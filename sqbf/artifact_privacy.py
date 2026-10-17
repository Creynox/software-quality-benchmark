"""Enforce current-user-only artifact directories before any evidence write."""
import os
from pathlib import Path
import stat
import subprocess


class ArtifactPrivacyError(RuntimeError):
    pass


def _windows_directory(path, protect, inherit=True):
    script = r'''
$ErrorActionPreference='Stop'
$p=[Console]::In.ReadToEnd()
$sid=[System.Security.Principal.WindowsIdentity]::GetCurrent().User
if (__PROTECT__) {
 & icacls.exe $p /inheritance:r /grant:r (('*'+$sid.Value)+'__RIGHTS__') | Out-Null
 if ($LASTEXITCODE -ne 0) { throw 'ACL enforcement failed' }
}
$acl=Get-Acl -LiteralPath $p
if (-not $acl.AreAccessRulesProtected) { throw 'Inherited permissions' }
$found=$false
foreach ($r in $acl.Access) {
 if ($r.AccessControlType -eq 'Allow') {
  if ($r.IdentityReference.Translate([System.Security.Principal.SecurityIdentifier]).Value -ne $sid.Value) { throw 'Unexpected reader' }
  $found=$true
 }
}
if (-not $found) { throw 'Owner access missing' }
'''.replace("__PROTECT__", "$true" if protect else "$false").replace("__RIGHTS__", ":(OI)(CI)F" if inherit else ":F")
    subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
                   input=str(path.resolve()), capture_output=True, text=True, check=True, timeout=10,
                   env={k:v for k,v in os.environ.items() if k.lower() != "psmodulepath"})


def check_private_directory(path, protect=False):
    path = Path(path)
    try:
        info = path.lstat()
        if path.is_symlink() or not stat.S_ISDIR(info.st_mode) or getattr(info,"st_file_attributes",0) & 0x400:
            raise ValueError()
        if os.name == "nt":
            _windows_directory(path, protect)
        else:
            if protect:
                path.chmod(0o700)
            if path.stat().st_uid != os.getuid() or path.stat().st_mode & 0o077:
                raise ValueError()
    except Exception:
        raise ArtifactPrivacyError("ARTIFACT_PRIVACY_FAILED: no artifact write permitted") from None


def create_private_file(path):
    """Exclusive empty reservation, protected before writing registry contents."""
    path = Path(path)
    with path.open("x"):
        pass
    try:
        if os.name == "nt":
            _windows_directory(path,True,inherit=False)
        else:
            path.chmod(0o600)
    except Exception:
        path.unlink()
        raise ArtifactPrivacyError("ARTIFACT_PRIVACY_FAILED: no file contents written") from None
