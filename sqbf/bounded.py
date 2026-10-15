"""Trusted subprocess supervisor. Secrets travel through pipes, never argv/files.

Windows jobs kill the owned process and all descendants on close. On Unix the
owned process group is killed. Both model I/O and the entire pilot are bounded.
"""
from __future__ import annotations

import base64
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

from .providers import ChatGPTPlanCredential, ChatGPTPlanModel, ModelResponse


class BudgetExceeded(RuntimeError):
    pass


class Budget:
    def __init__(self, seconds=300, calls=12):
        if not 0 < seconds <= 300 or not 1 <= calls <= 12:
            raise ValueError("Pilot budgets must be within 300 seconds and 12 calls")
        self.deadline = time.monotonic() + seconds
        self.limit = calls
        self.calls = 0

    def remaining(self):
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise BudgetExceeded("Hard pilot deadline exceeded")
        return remaining

    def claim(self):
        self.remaining()
        if self.calls >= self.limit:
            raise BudgetExceeded("Model call budget exhausted")
        self.calls += 1


class LabBudget(Budget):
    """Separate explicitly commissioned write pilot; CORE limits stay fixed."""
    def __init__(self, seconds, calls):
        if not 0 < seconds <= 1500 or not 2 <= calls <= 152:
            raise ValueError('LAB budgets exceed 25 minutes or 152 calls')
        self.deadline = time.monotonic() + seconds
        self.limit, self.calls = calls, 0


def _windows_job(process):
    class Basic(ctypes.Structure):
        _fields_ = [("process_time", ctypes.c_int64), ("job_time", ctypes.c_int64),
                    ("flags", wintypes.DWORD), ("min_ws", ctypes.c_size_t),
                    ("max_ws", ctypes.c_size_t), ("active", wintypes.DWORD),
                    ("affinity", ctypes.c_size_t), ("priority", wintypes.DWORD),
                    ("scheduling", wintypes.DWORD)]
    class Extended(ctypes.Structure):
        _fields_ = [("basic", Basic), ("io", ctypes.c_uint64 * 6),
                    ("process_memory", ctypes.c_size_t), ("job_memory", ctypes.c_size_t),
                    ("peak_process", ctypes.c_size_t), ("peak_job", ctypes.c_size_t)]
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    kernel.CreateJobObjectW.restype = wintypes.HANDLE
    kernel.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.TerminateJobObject.argtypes = [wintypes.HANDLE,wintypes.UINT]
    job = kernel.CreateJobObjectW(None, None)
    info = Extended()
    info.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    if (not job or not kernel.SetInformationJobObject(job, 9, ctypes.byref(info), ctypes.sizeof(info))
            or not kernel.AssignProcessToJobObject(job, int(process._handle))):
        if job:
            kernel.CloseHandle(job)
        process.kill()
        process.wait()
        raise RuntimeError("Cannot enforce Windows process-tree deadline")
    def close_job():
        # Explicit termination also covers handles duplicated by descendants;
        # closing our handle alone is not a sufficient observed tree-stop gate.
        kernel.TerminateJobObject(job,2)
        kernel.CloseHandle(job)
    return close_job


def _resume_owned_process(process):
    """Resume its initial thread only after assigning the suspended process.

    A venv launcher may create another interpreter immediately at startup.
    Suspending before job assignment avoids that descendant escaping the job.
    """
    class ThreadEntry(ctypes.Structure):
        _fields_=[("size",wintypes.DWORD),("usage",wintypes.DWORD),
                  ("thread_id",wintypes.DWORD),("owner_pid",wintypes.DWORD),
                  ("base_priority",wintypes.LONG),("delta",wintypes.LONG),("flags",wintypes.DWORD)]
    kernel=ctypes.WinDLL("kernel32",use_last_error=True)
    kernel.CreateToolhelp32Snapshot.argtypes=[wintypes.DWORD,wintypes.DWORD]
    kernel.CreateToolhelp32Snapshot.restype=wintypes.HANDLE
    kernel.Thread32First.argtypes=[wintypes.HANDLE,ctypes.POINTER(ThreadEntry)]
    kernel.Thread32Next.argtypes=[wintypes.HANDLE,ctypes.POINTER(ThreadEntry)]
    kernel.OpenThread.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
    kernel.OpenThread.restype=wintypes.HANDLE
    kernel.ResumeThread.argtypes=[wintypes.HANDLE]
    kernel.ResumeThread.restype=wintypes.DWORD
    kernel.CloseHandle.argtypes=[wintypes.HANDLE]
    snapshot=kernel.CreateToolhelp32Snapshot(4,0)
    entry=ThreadEntry()
    entry.size=ctypes.sizeof(entry)
    try:
        available=kernel.Thread32First(snapshot,ctypes.byref(entry))
        while available:
            if entry.owner_pid==process.pid:
                thread=kernel.OpenThread(2,False,entry.thread_id)
                if not thread:
                    break
                try:
                    if kernel.ResumeThread(thread)==1:
                        return
                finally:
                    kernel.CloseHandle(thread)
                break
            available=kernel.Thread32Next(snapshot,ctypes.byref(entry))
    finally:
        kernel.CloseHandle(snapshot)
    raise RuntimeError("Cannot resume the owned worker after job assignment")


def invoke_worker(mode: str, payload: dict, timeout: float):
    if timeout <= 0:
        raise BudgetExceeded("No time remains for the worker")
    # Windows venv redirectors can launch interpreters with job breakaway.
    # Start the actual interpreter instead, retaining the current environment's
    # import paths (including the project venv packages) through PYTHONPATH.
    executable=getattr(sys,"_base_executable",sys.executable) if os.name=="nt" else sys.executable
    environment=os.environ.copy()
    environment["PYTHONPATH"]=os.pathsep.join(str(path) for path in sys.path)
    process = subprocess.Popen(
        [executable, "-m", "sqbf.bounded", mode],
        cwd=str(Path(__file__).resolve().parents[1]),
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding="utf-8", start_new_session=os.name != "nt",
        creationflags=(0x00000004 | 0x08000000) if os.name=="nt" else 0,
        env=environment,
    )
    close_tree = None
    try:
        # Worker waits for stdin before doing work. Assign it to the job before
        # releasing the payload, so browser/model descendants inherit the job.
        close_tree = _windows_job(process) if os.name == "nt" else lambda: os.killpg(process.pid, signal.SIGKILL)
        if os.name=="nt":
            _resume_owned_process(process)
        try:
            stdout, _ = process.communicate(json.dumps(payload), timeout=timeout)
        except subprocess.TimeoutExpired:
            close_tree()
            close_tree = None
            process.wait(timeout=5)
            raise BudgetExceeded("Owned worker exceeded its hard wall-clock deadline") from None
        if process.returncode:
            raise RuntimeError("Owned worker failed; stopped without retry")
        result = json.loads(stdout)
        if not isinstance(result, dict):
            raise RuntimeError("Invalid worker response")
        return result
    finally:
        if close_tree:
            try:
                close_tree()
            except ProcessLookupError:
                pass
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)


def model_spec(model):
    if not isinstance(model, ChatGPTPlanModel):
        raise ValueError("Only the authorized ChatGPT plan provider is permitted")
    return {"model": model.model, "access_token": model.credential.access_token,
            "scopes": sorted(model.credential.granted_scopes), "schema": model.response_schema,
            "max_response_chars": model.max_response_chars}


def restore_model(spec):
    return ChatGPTPlanModel(spec["model"], ChatGPTPlanCredential(spec["access_token"], frozenset(spec["scopes"])),
                            spec["schema"], timeout=30, max_response_chars=spec["max_response_chars"])


def ask_bounded(model, prompt, screenshots, budget):
    budget.claim()
    images = screenshots if isinstance(screenshots, list) else [screenshots]
    result = invoke_worker("model", {"provider": model_spec(model), "prompt": prompt,
                          "images": [base64.b64encode(png).decode() for png in images]},
                          min(30, budget.remaining()))
    budget.remaining()
    return ModelResponse(result["data"], result["usage"])


def main():
    try:
        payload = json.load(sys.stdin)
        mode = sys.argv[1]
        if mode == "model":
            model = restore_model(payload["provider"])
            result = model.ask(payload["prompt"], [base64.b64decode(png) for png in payload["images"]])
            output = {"data": result.data, "usage": result.usage}
        elif mode == "vision-test":
            from .plan_login import vision_test
            model=restore_model(payload["provider"])
            output=vision_test(model.credential,model.model)
        elif mode == "pilot":
            from .smoke_runner import browser_pilot
            output = browser_pilot(payload)
        elif mode == "lab-pilot":
            from .write_profile import load_write_profile
            module=load_write_profile(payload['scenario']['write_policy']['contract'],'lab_runner')
            output = module.browser_pilot(payload)
        elif mode == 'pdf-check':
            from importlib import import_module
            output=import_module('projects.ble-elva.tools.pdf_check').inspect_pdf(payload['path'],payload['required_text'])
        elif mode == 'regular-suite':
            from .write_profile import load_suite_profile
            output=load_suite_profile(payload['suite']['adapter_contract']).browser_suite(payload)
        elif mode == "test-hang":
            time.sleep(60)  # Explicit local regression mode, no credentials/UI.
            output = {}
        elif mode == "test-tree":
            child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
            Path(payload["pid_file"]).write_text(str(child.pid))
            time.sleep(60)
            output = {}
        else:
            raise ValueError("Unknown worker mode")
        print(json.dumps(output))
        return 0
    except Exception:
        # Never forward provider exceptions, raw payloads, stderr, or tokens.
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
