import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from sqbf.bounded import Budget, BudgetExceeded, ask_bounded, invoke_worker
from sqbf.models import Scenario
from sqbf.no_write_oracle import TABLES, compare, snapshot
from sqbf.providers import ChatGPTPlanCredential, ChatGPTPlanModel, CHATGPT_PLAN_SCOPE
from sqbf.read_only import allow_operation, request_allowed, ReadOnlyViolation, EVENT_GUARD, check_action
from sqbf.reporting import Evidence,index_run
from sqbf.smoke_runner import ACTION_SCHEMA, REVIEW_SCHEMA, run_smoke


class CoreSmokeTests(unittest.TestCase):
    def model(self):
        return ChatGPTPlanModel("gpt-6-luna",ChatGPTPlanCredential("secret-canary",frozenset({CHATGPT_PLAN_SCOPE})),ACTION_SCHEMA)

    def test_hard_model_timeout_and_no_retry(self):
        started=time.monotonic()
        with self.assertRaises(BudgetExceeded):
            invoke_worker("test-hang",{"secret":"secret-canary"},0.5)
        self.assertLess(time.monotonic()-started,4)
        budget=Budget(seconds=1,calls=1)
        with patch("sqbf.bounded.invoke_worker",side_effect=BudgetExceeded("timeout")) as worker:
            with self.assertRaises(BudgetExceeded): ask_bounded(self.model(),"task",b"png",budget)
            self.assertEqual(worker.call_count,1)
            with self.assertRaises(BudgetExceeded): ask_bounded(self.model(),"task",b"png",budget)
            self.assertEqual(worker.call_count,1)

    def test_process_tree_is_killed_at_deadline(self):
        import ctypes
        with tempfile.TemporaryDirectory() as directory:
            pidfile=Path(directory)/"pid"
            with self.assertRaises(BudgetExceeded):
                invoke_worker("test-tree",{"pid_file":str(pidfile)},1)
            self.assertTrue(pidfile.exists())
            pid=int(pidfile.read_text())
            if os.name == "nt":
                kernel=ctypes.WinDLL("kernel32",use_last_error=True)
                kernel.OpenProcess.restype=ctypes.c_void_p
                handle=kernel.OpenProcess(0x101000,False,pid)
                if handle:
                    # Job termination is asynchronous; wait for the descendant
                    # signal rather than equating a transient exit-code race
                    # immediately after parent termination with a live child.
                    kernel.WaitForSingleObject(ctypes.c_void_p(handle),2000)
                    code=ctypes.c_ulong()
                    kernel.GetExitCodeProcess(ctypes.c_void_p(handle),ctypes.byref(code))
                    kernel.CloseHandle(ctypes.c_void_p(handle))
                    self.assertNotEqual(code.value,259)
            else:
                self.assertFalse(Path(f"/proc/{pid}").exists())

    def test_global_call_and_time_limits_fail_before_dispatch(self):
        with patch("sqbf.bounded.time.monotonic",return_value=0): budget=Budget(seconds=1,calls=2)
        with patch("sqbf.bounded.time.monotonic",return_value=2),patch("sqbf.bounded.invoke_worker") as worker:
            with self.assertRaises(BudgetExceeded): ask_bounded(self.model(),"task",b"png",budget)
            worker.assert_not_called()
        with self.assertRaises(ValueError): Budget(seconds=301)
        with self.assertRaises(ValueError): Budget(calls=13)

    def test_write_targets_and_unapproved_text_keys_are_blocked(self):
        policy={"query":"STS 0–45"}
        allow_operation({"action":"click"},"products-navigation",False,policy)
        allow_operation({"action":"type","text":"STS 0–45"},None,True,policy)
        allow_operation({"action":"key","key":"Backspace"},None,True,policy)
        for action,target,focus in [({"action":"click"},"new-product",False),
               ({"action":"type","text":"injected"},None,True),
               ({"action":"type","text":"STS 0–45"},None,False),
               ({"action":"key","key":"Tab"},None,True)]:
            with self.assertRaises(ReadOnlyViolation): allow_operation(action,target,focus,policy)

    def test_http_origin_route_and_write_method_limits(self):
        origin="http://127.0.0.1:5080"
        self.assertTrue(request_allowed(origin+"/products","GET",origin))
        self.assertTrue(request_allowed(origin+"/_blazor/negotiate","POST",origin))
        for url,method in [(origin+"/products/new","GET"),(origin+"/api/products","POST"),
                           ("http://127.0.0.1:5059/products","GET"),(origin+"/products","DELETE")]:
            self.assertFalse(request_allowed(url,method,origin))

    def test_oracle_requires_stable_identity_hashes_and_all_visible_steps(self):
        before={"docker":{"id":"one"},"tables":{"products":{"count":0,"hash":"hash"}}}
        observations=[{"query_visible":True,"empty_visible":True},
                      {"products_page":True,"filter_cleared":True,"empty_visible":True}]
        self.assertEqual(compare(before,before,observations,True)["status"],"PASS")
        changed={"docker":{"id":"two"},"tables":before["tables"]}
        self.assertEqual(compare(before,changed,observations,True)["status"],"FAIL")
        changed={"docker":before["docker"],"tables":{"products":{"count":0,"hash":"different"}}}
        self.assertEqual(compare(before,changed,observations,True)["status"],"FAIL")
        self.assertEqual(compare(before,before,observations[:-1],True)["status"],"FAIL")
        self.assertEqual(compare(before,before,observations,False)["status"],"FAIL")

    def test_oracle_uses_only_read_queries_and_select_only_existing_role(self):
        fixture={"database":{"container":"isolated","oracle_role":"sqbf_oracle_ro","name":"fixture"}}
        identity={"database":"fixture","username":"sqbf_oracle_ro","read_only":"on",
                  **{k:False for k in ["superuser","createdb","createrole","bypassrls","create_schema","create_object"]}}
        rows=[identity,{"can_write":False}]+[{"table":table,"count":0,"hash":"hash"} for table in TABLES]
        import types
        with patch("sqbf.no_write_oracle.verify_docker_identity",return_value={"id":"one"}), \
                patch("subprocess.run",return_value=types.SimpleNamespace(stdout="\n".join(json.dumps(row) for row in rows))) as command:
            snapshot(fixture,run=command)
            sql=command.call_args.kwargs["input"]
            self.assertIn("READ ONLY",sql)
            self.assertIn("sqbf_oracle_ro",command.call_args.args[0])
            self.assertFalse(any(verb in sql for verb in ["INSERT INTO","UPDATE ","DELETE FROM","TRUNCATE ","GRANT ","CREATE "]))
            rows[1]["can_write"]=True
            command.return_value.stdout="\n".join(json.dumps(row) for row in rows)
            with self.assertRaises(RuntimeError): snapshot(fixture,run=command)

    def test_all_outputs_and_registry_with_mocked_pilot(self):
        scenario=Scenario.load("projects/ble-elva/scenarios/core-smoke-01.json")
        observations=[{"query_visible":True,"empty_visible":True},
                      {"products_page":True,"filter_cleared":True,"empty_visible":True}]
        result={"executor_status":"DONE","actions":5,"model_calls":7,"observations":observations,
                "review":{"verdict":"PASS","reason":"visible","findings":[],
                          "scores":{"findability":4,"clarity":4,"task_progress":5,"error_recovery":3}},
                "usage":[],"events":[],"images":[],"wall_seconds":1}
        def simulate_worker(mode,payload,timeout):
            import hashlib
            images=[]
            for i in range(2):
                name=f'{i:03d}-mock.png'
                png=b'mock screenshot'
                (Path(payload['folder'])/name).write_bytes(png)
                images.append({'name':name,'label':'mock','sha256':hashlib.sha256(png).hexdigest()})
            result['images']=images
            return result
        with tempfile.TemporaryDirectory() as directory,patch("sqbf.smoke_runner.snapshot",return_value={"unchanged":True}), \
                patch("sqbf.smoke_runner.invoke_worker",side_effect=simulate_worker) as worker:
            folder=run_smoke(scenario,self.model(),self.model(),Path(directory),"local-session",False,
                  "projects/ble-elva/fixtures/enzberg-product-core-v0.2.json")
            for name in ["run.json","report.md","scores.json","findings.json","oracle-before.json","oracle-after.json","oracle.json"]:
                self.assertTrue((folder/name).exists(),name)
            manifest=json.loads((folder/"run.json").read_text())
            self.assertEqual(manifest["completion_status"],"GO")
            self.assertNotIn("secret-canary",(folder/"run.json").read_text())
            self.assertIn("CORE-SMOKE-01",(Path(directory)/"index.jsonl").read_text())
            self.assertLessEqual(worker.call_args.args[2],280)

    def test_real_browser_blocks_write_button_even_if_clicked_directly(self):
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser=p.chromium.launch()
            context=browser.new_context()
            page=context.new_page()
            page.set_content('<button onclick="window.writes=1">Neues Produkt</button><input placeholder="Produkt, Code, Werk oder Kunde">')
            page.evaluate(EVENT_GUARD)
            page.get_by_text("Neues Produkt").click()
            self.assertIsNone(page.evaluate("window.writes"))
            field=page.locator('input')
            field.click()
            field.press_sequentially("STS 0–45")
            self.assertEqual(field.input_value(),"STS 0–45")
            browser.close()

    def test_browser_loop_action_budget_and_invalid_action_stop_with_mocks(self):
        import types
        from unittest.mock import MagicMock
        from sqbf.bounded import model_spec
        from sqbf.providers import ModelResponse
        from sqbf.smoke_runner import browser_pilot
        from dataclasses import asdict
        for invalid in [False,True]:
            scenario=Scenario.load("projects/ble-elva/scenarios/core-smoke-01.json")
            scenario.max_actions=2
            page=MagicMock()
            page.url=scenario.url
            page.screenshot.return_value=b"synthetic-screenshot"
            page.evaluate.return_value={"target":"product-search","focused":True}
            browser=MagicMock()
            browser.new_context.return_value.new_page.return_value=page
            playwright=MagicMock()
            playwright.__enter__.return_value.chromium.launch.return_value=browser
            def ask(model,prompt,images,budget):
                budget.claim()
                if prompt.startswith("Independently"):
                    return ModelResponse({"verdict":"INCONCLUSIVE","reason":"mock","findings":[],
                        "scores":{"findability":1,"clarity":1,"task_progress":1,"error_recovery":1}}, {})
                action={"action":"type","text":"unapproved"} if invalid else {"action":"click","x":20,"y":20}
                return ModelResponse(action,{})
            with tempfile.TemporaryDirectory() as directory, \
                    patch("playwright.sync_api.sync_playwright",return_value=playwright), \
                    patch("sqbf.smoke_runner.ask_bounded",side_effect=ask) as calls, \
                    patch("sqbf.smoke_runner.observation",return_value={"query_visible":False,"empty_visible":True}):
                payload={"scenario":asdict(scenario),"executor":model_spec(self.model()),"reviewer":model_spec(self.model()),
                         "seconds":5,"folder":directory,"storage_state":"test-session","headed":False}
                if invalid:
                    result=browser_pilot(payload)
                    self.assertEqual(result["executor_status"],"BLOCKED_READ_ONLY")
                    page.keyboard.type.assert_not_called()
                    self.assertEqual(calls.call_count,1)
                else:
                    result=browser_pilot(payload)
                    self.assertEqual(result["actions"],2)
                    self.assertEqual(page.mouse.click.call_count,2)
                    self.assertEqual(result["executor_status"],"BLOCKED_ACTION_BUDGET")

    def test_registry_filters(self):
        from sqbf.cli import main
        import io
        rows=[{"scenario_id":"CORE-SMOKE-01","software_version":"build","date":"2026-10-13",
               "persona":"Laborleitung","executor":"gpt-6-luna","reviewer":"strong", "result":"GO",
               "scores":{"clarity":4}}, {"scenario_id":"other","result":"NO-GO"}]
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory)/"index.jsonl").write_text("\n".join(json.dumps(row) for row in rows))
            output=io.StringIO()
            with patch("sys.stdout",output):
                main(["list-runs","--output",directory,"--test-id","CORE-SMOKE-01","--role","luna","--min-score","3"])
            self.assertEqual(len(json.loads(output.getvalue())),1)


if __name__ == "__main__": unittest.main()
