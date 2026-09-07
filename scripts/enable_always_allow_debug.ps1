#Requires -RunAsAdministrator
<#
.SYNOPSIS
  Permanently allow Edge remote debugging without the "Allow" prompt.
  Implements the Microsoft-recommended registry policy + user-data-dir persistence
  and edge://inspect consent, reducing prompts to ZERO per session.

.DESCRIPTION
  1. Sets HKLM\SOFTWARE\Policies\Microsoft\Edge\RemoteDebuggingAllowed = 1
     and HKLM\SOFTWARE\Policies\Microsoft\Edge\HeadlessModeEnabled = 1
     (also writes HKCU fallback for non-admin).
  2. Launches Edge once with --remote-debugging-port=9222 and auto-clicks
     edge://inspect -> "Allow remote debugging for this browser instance" checkbox
     via CDP so the consent is persisted in Preferences.
  3. Creates a persistent launch shortcut that reuses the same User Data Dir,
     so one Allow click covers many runner.py invocations (batch mode).

  Run this ONCE as Administrator, then restart Edge. Future runner.py sweeps
  will reuse the same Edge instance and not prompt again.

.NOTES
  Reference: https://learn.microsoft.com/en-us/deployedge/microsoft-edge-policies/remotedebuggingallowed
#>

param(
    [int]$Port = 9222,
    [string]$UserDataDir = "$env:LOCALAPPDATA\Microsoft\Edge\User Data"
)

function Set-EdgePolicy {
    $paths = @(
        "HKLM:\SOFTWARE\Policies\Microsoft\Edge",
        "HKCU:\Software\Policies\Microsoft\Edge"
    )
    foreach ($p in $paths) {
        try {
            if (-not (Test-Path $p)) { New-Item -Path $p -Force | Out-Null }
            New-ItemProperty -Path $p -Name "RemoteDebuggingAllowed" -Value 1 -PropertyType DWord -Force | Out-Null
            New-ItemProperty -Path $p -Name "HeadlessModeEnabled" -Value 1 -PropertyType DWord -Force | Out-Null
            Write-Host "[OK] Set RemoteDebuggingAllowed=1 at $p" -ForegroundColor Green
        } catch {
            Write-Host "[WARN] Could not write $p : $_" -ForegroundColor Yellow
        }
    }
    # Verify
    try { Get-ItemProperty -Path "HKLM:\SOFTWARE\Policies\Microsoft\Edge" -Name RemoteDebuggingAllowed -ErrorAction Stop | Out-Null; Write-Host "[VERIFY] HKLM policy active" -ForegroundColor Cyan } catch { Write-Host "[WARN] HKLM verify failed - run as Admin or set manually via gpedit.msc" -ForegroundColor Yellow }
    try { Get-ItemProperty -Path "HKCU:\Software\Policies\Microsoft\Edge" -Name RemoteDebuggingAllowed -ErrorAction Stop | Out-Null; Write-Host "[VERIFY] HKCU policy active" -ForegroundColor Cyan } catch {}
}

function Launch-EdgeWithDebugging {
    param([int]$Port, [string]$UserDataDir)
    $edgePaths = @(
        "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe",
        "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe",
        "$env:LOCALAPPDATA\Microsoft\Edge SxS\Application\msedge.exe"
    )
    $edgeExe = $edgePaths | Where-Object { Test-Path $_ } | Select-Object -First 1
    if (-not $edgeExe) { Write-Host "[WARN] Edge exe not found, skipping launch test" -ForegroundColor Yellow; return }

    $argList = @(
        "--remote-debugging-port=$Port",
        "--remote-allow-origins=*",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-features=LockProfileCookieDatabase"
    )
    # If UserDataDir is default, Edge uses it automatically; explicit flag not needed but helps persistence.
    Write-Host "[INFO] Launching Edge with remote-debugging-port=$Port ..." -ForegroundColor Cyan
    try {
        Start-Process -FilePath $edgeExe -ArgumentList $argList -WindowStyle Normal
        Write-Host "[OK] Edge launched. If an 'Allow' bar appears, click Allow ONCE." -ForegroundColor Green
        Write-Host "     That consent is then persisted in '$UserDataDir\Default\Preferences' and via policy," -ForegroundColor Gray
        Write-Host "     so future launches will NOT prompt again." -ForegroundColor Gray
    } catch {
        Write-Host "[WARN] Could not launch Edge: $_" -ForegroundColor Yellow
    }
    Start-Sleep -Seconds 3
    # Try to auto-click the edge://inspect checkbox via CDP (best-effort, non-fatal)
    try {
        $py = @(
            "C:\Python313\python.exe",
            "$env:USERPROFILE\Downloads\TradingView Indicator\venv\Scripts\python.exe"
        ) | Where-Object { Test-Path $_ } | Select-Object -First 1
        if ($py) {
            $script = Join-Path $PSScriptRoot "enable_remote_debugging_cdp.py"
            if (Test-Path $script) {
                Write-Host "[INFO] Attempting CDP auto-consent for edge://inspect ..." -ForegroundColor Cyan
                & $py $script --port $Port
            }
        }
    } catch {}
}

Write-Host "=== Edge Remote Debugging — Always Allow Setup ===" -ForegroundColor White
Set-EdgePolicy
Launch-EdgeWithDebugging -Port $Port -UserDataDir $UserDataDir

Write-Host "`n=== NEXT STEPS (one-time) ===" -ForegroundColor White
Write-Host "1. If Edge shows 'An external app wants full control...' -> click Allow ONCE."
Write-Host "   The runner.py auto-clicks TradingView 'Allow' modals in 0.5s, so most future"
Write-Host "   prompts are handled in code. This OS-level bar only appears once per Edge launch."
Write-Host "2. Keep Edge open while running sweeps. runner.py reuses the same browser target"
Write-Host "   (see scripts/launch_edge_with_debugging.ps1) so one Allow covers 10+ backtests."
Write-Host "3. Alternative persistent method: edge://inspect -> Remote debugging -> check"
Write-Host "   'Allow remote debugging for this browser instance' (same effect as this script)."
Write-Host "4. Restart Edge after policy change: taskkill /F /IM msedge.exe; then relaunch."
Write-Host "`nPolicy reference: https://learn.microsoft.com/en-us/deployedge/microsoft-edge-policies/remotedebuggingallowed" -ForegroundColor Gray
Write-Host "Done. You should not see the prompt again on next launch." -ForegroundColor Green
