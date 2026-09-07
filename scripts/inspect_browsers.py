import subprocess
import json

ps_cmd = """
Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'chrome|msedge' } | ForEach-Object {
    [PSCustomObject]@{
        Id = $_.ProcessId
        Name = $_.Name
        CommandLine = $_.CommandLine
    }
} | ConvertTo-Json
"""

res = subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True, text=True)
try:
    data = json.loads(res.stdout)
    if isinstance(data, dict):
        data = [data]
    for p in data:
        cmd = p.get('CommandLine') or ''
        if any(k in cmd.lower() for k in ['remote-debugging', 'tradingview', 'user-data-dir', 'devtools']):
            print(f"[{p['Name']} - {p['Id']}] {cmd[:200]}...")
except Exception as e:
    print("Error:", e)
    print(res.stdout[:500])
