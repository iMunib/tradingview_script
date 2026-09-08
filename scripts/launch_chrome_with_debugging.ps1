#Requires -Version 5.1
param(
    [int]$Port = 9222,
    [string]$Url = "https://www.tradingview.com/chart/",
    [string]$UserDataDir = "C:\Users\RehmanPC\ChromeDevProfile"
)
$ErrorActionPreference = "Stop"
$ChromeCandidates = @(
    "C:\Program Files\Google\Chrome\Application\chrome.exe",
    "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "C:\Users\RehmanPC\AppData\Local\Google\Chrome\Application\chrome.exe"
)
function Find-Chrome {
    foreach ($p in $ChromeCandidates) {
        if (Test-Path $p) { return $p }
    }
    return $null
}
function Kill-ZombiePortOwner {
    param([int]$Port)
    try {
        $conns = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue | Where-Object { $_.State -eq "Listen" }
        foreach ($c in $conns) {
            $pid = $c.OwningProcess
            try {
                $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
                if (-not $proc) { continue }
                $name = $proc.ProcessName
                $path = $proc.Path
                if ($name -like "*chrome*" -or $path -like "*chrome*") {
                    Write-Host "[PURGE] Port $Port owned by Chrome PID $pid ($name) - keeping" -ForegroundColor Green
                    return $false
                }
                Write-Host "[PURGE] Killing zombie $name (PID $pid) on port $Port - Edge purged" -ForegroundColor Yellow
                Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
                Start-Sleep -Seconds 1
                return $true
            } catch {
                Write-Host "[WARN] Could not inspect PID $pid : $_" -ForegroundColor Yellow
            }
        }
    } catch {
        Write-Host "[WARN] Kill-Zombie failed: $_" -ForegroundColor Yellow
    }
    return $false
}
function Test-PortOpen {
    param([int]$Port)
    try {
        $c = Test-NetConnection -ComputerName 127.0.0.1 -Port $Port -WarningAction SilentlyContinue -ErrorAction SilentlyContinue
        return $c.TcpTestSucceeded
    } catch { return $false }
}
Write-Host "=== Chrome Zero-Prompt Launcher (Edge Purged) ===" -ForegroundColor Cyan
if (Test-PortOpen -Port $Port) {
    Write-Host "[CHECK] Port $Port is occupied - checking owner..." -ForegroundColor Yellow
    $killed = Kill-ZombiePortOwner -Port $Port
    if ($killed) {
        Start-Sleep -Seconds 1
        if (Test-PortOpen -Port $Port) {
            Write-Host "[ERROR] Port $Port still occupied after purge" -ForegroundColor Red
            Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue | Format-Table LocalAddress, LocalPort, OwningProcess, State
        } else {
            Write-Host "[PURGE] Port $Port cleared" -ForegroundColor Green
        }
    } else {
        Write-Host "[OK] Port $Port owned by Chrome - reusing (zero new Allow)" -ForegroundColor Green
        Write-Host "[PERSIST] Reusing existing Chrome session" -ForegroundColor Green
        exit 0
    }
}
$chrome = Find-Chrome
if (-not $chrome) {
    Write-Host "[ERROR] Google Chrome not found at standard locations:" -ForegroundColor Red
    $ChromeCandidates | ForEach-Object { Write-Host "  $_" -ForegroundColor Red }
    Write-Host "Install Chrome or set UserDataDir. Edge fallback is purged per mandate." -ForegroundColor Red
    exit 1
}
Write-Host "[DISCOVERY] Chrome found at $chrome" -ForegroundColor Green
if (-not (Test-Path $UserDataDir)) {
    New-Item -ItemType Directory -Path $UserDataDir -Force | Out-Null
    Write-Host "[INIT] Created ChromeDevProfile at $UserDataDir" -ForegroundColor Cyan
}
$chromeArgs = @(
    "--remote-debugging-port=$Port",
    "--user-data-dir=`"$UserDataDir`"",
    "--no-first-run",
    "--no-default-browser-check",
    "--remote-allow-origins=*",
    $Url
)
Write-Host "[LAUNCH] $chrome $($chromeArgs -join ' ')" -ForegroundColor Cyan
try {
    Start-Process -FilePath $chrome -ArgumentList $chromeArgs -WindowStyle Normal
} catch {
    Write-Host "[ERROR] Chrome launch failed: $_" -ForegroundColor Red
    exit 1
}
for ($i=0; $i -lt 20; $i++) {
    if (Test-PortOpen -Port $Port) {
        Write-Host "[SUCCESS] Chrome listening on 127.0.0.1:$Port - zero infobar, single WS for sweep" -ForegroundColor Green
        Write-Host "[INFO] Keep this Chrome window open for entire evaluate sweep (12 assets, one Allow)" -ForegroundColor Cyan
        exit 0
    }
    Start-Sleep -Seconds 1
}
Write-Host "[ERROR] Chrome did not open port $Port within 20s" -ForegroundColor Red
exit 1
