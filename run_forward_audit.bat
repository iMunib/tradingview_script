@echo off
REM 30-Day Forward Walk Audit — One-Click Runner
REM Connects to Chrome CDP on 127.0.0.1:9222 and scrapes Strategy Tester List of Trades
cd /d "%~dp0"
echo === Forward Walk Audit ===
echo Chrome must be running with --remote-debugging-port=9222 and TradingView chart open
echo.
if exist "venv\Scripts\python.exe" (
    "venv\Scripts\python.exe" "scripts\forward_monitor.py"
) else (
    python "scripts\forward_monitor.py"
)
echo.
echo Audit complete. See metrics\FORWARD_WALK_STATUS.md and metrics\forward_test_log.json
pause
