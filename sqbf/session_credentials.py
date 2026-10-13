"""Explicit Windows-user-bound benchmark credentials, never logged or exported."""
import json
import os
from pathlib import Path
import subprocess


def load_credentials(path, expected_username):
    if os.name != "nt" or not expected_username:
        raise ValueError("DPAPI login requires Windows and an explicit expected username")
    # File contents and decrypted password stay in a captured child pipe/memory.
    script = r'''
$ErrorActionPreference='Stop'
$p=[Console]::In.ReadToEnd()
$sid=[System.Security.Principal.WindowsIdentity]::GetCurrent().User
$acl=Get-Acl -LiteralPath $p
if (-not $acl.AreAccessRulesProtected) { throw 'Unprotected credential ACL' }
foreach ($rule in $acl.Access) {
 if ($rule.AccessControlType -eq 'Allow' -and $rule.IdentityReference.Translate([System.Security.Principal.SecurityIdentifier]).Value -ne $sid.Value) { throw 'Unexpected credential reader' }
}
$c=Get-Content -LiteralPath $p -Raw | ConvertFrom-Json
$s=ConvertTo-SecureString $c.password_dpapi
$b=[Runtime.InteropServices.Marshal]::SecureStringToBSTR($s)
try { @{username=$c.username;password=[Runtime.InteropServices.Marshal]::PtrToStringBSTR($b)} | ConvertTo-Json -Compress }
finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($b) }
'''
    try:
        result = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
                                input=str(Path(path).resolve()), capture_output=True, text=True,
                                timeout=15, check=True,
                                env={key: value for key, value in os.environ.items() if key.lower() != "psmodulepath"})
        data = json.loads(result.stdout)
        if data.get("username") != expected_username or not isinstance(data.get("password"), str) or not data["password"]:
            raise ValueError()
        return data
    except Exception:
        raise ValueError("Local DPAPI benchmark credentials unavailable or identity mismatch") from None
