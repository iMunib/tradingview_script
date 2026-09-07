<#
.SYNOPSIS
  DEPRECATED — Edge purged. This wrapper now kills Edge and launches Chrome.
  Use .\launch_chrome_with_debugging.ps1 directly for zero-prompt Chrome.
  Kept for backward compatibility — now enforces Chrome hardcode.
#>
param(
    [int]$Port = 9222,
    [string]$Url = "https://www.tradingview.com/chart/",
    [switch]$KillExisting
)
Write-Host "[DEPRECATED] launch_edge_with_debugging.ps1 is now a Chrome wrapper — Edge purged per mandate" -ForegroundColor Yellow
# Kill any Edge camping on 9222
try {
    $conns = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue | Where-Object { $_.State -eq "Listen" }
    foreach ($c in $conns) {
        $proc = Get-Process -Id $c.OwningProcess -ErrorAction SilentlyContinue
        if ($proc -and $proc.ProcessName -like "*msedge*") {
            Write-Host "[PURGE] Killing Edge PID $($proc.Id) on port $Port" -ForegroundColor Yellow
            Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
            Start-Sleep -Seconds 1
        }
    }
} catch {}
# Delegate to Chrome launcher (hardcoded)
$chromeLauncher = Join-Path $PSScriptRoot "launch_chrome_with_debugging.ps1"
if (Test-Path $chromeLauncher) {
    & $chromeLauncher -Port $Port -Url $Url
} else {
    Write-Error "Chrome launcher not found at $chromeLauncher — Edge fallback is purged"
    exit 1
}
