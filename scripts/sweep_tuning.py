"""
Systematic Parametric Sweeper for Intrabar Patched Quant Swing Strategy
Evaluates:
- atrStopMult: [2.4, 2.8, 3.2]
- tpMultiple: [2.5, 3.0, 3.5]
- pivotLeft/Right: [3, 5, 8]
"""

import os
import sys
import re
import json
import asyncio
import subprocess

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_PINE = os.path.join(ROOT_DIR, "FINAL_OPTIMIZED_STRATEGY.pine")
TEMP_PINE = os.path.join(ROOT_DIR, "strategy_sweep.pine")
PYTHON_EXE = os.path.join(ROOT_DIR, "venv", "Scripts", "python.exe")
RUNNER_PY = os.path.join(ROOT_DIR, "runner.py")
SWEEP_RESULTS = os.path.join(ROOT_DIR, "metrics", "sweep_results.json")

def make_sweep_variant(atr_mult=2.8, tp_mult=3.0, pivot_lr=5, date_mode="All"):
    with open(BASE_PINE, "r", encoding="utf-8") as f:
        code = f.read()

    # Literal replacement to guarantee TradingView uses exact values
    code = re.sub(r'atrStopMult\s*=\s*input\.float\(.*', f'atrStopMult = {atr_mult}', code)
    code = re.sub(r'tpMultiple\s*=\s*input\.float\(.*', f'tpMultiple = {tp_mult}', code)
    code = re.sub(r'pivotLeft\s*=\s*input\.int\(.*', f'pivotLeft = {pivot_lr}', code)
    code = re.sub(r'pivotRight\s*=\s*input\.int\(.*', f'pivotRight = {pivot_lr}', code)

    if date_mode == "In-Sample (2018-2024)":
        code = re.sub(r'bool inTradeWindow = true[\s\S]*?(?=// ═══════════════════════════════════════════════════════════════════════════════\n// 3\. ZERO-LOOKAHEAD)',
                      'bool inTradeWindow = (time >= inSampleStart and time <= inSampleEnd)\nbool useDateFilter = true\n', code)
    elif date_mode == "Out-of-Sample (2025-2026)":
        code = re.sub(r'bool inTradeWindow = true[\s\S]*?(?=// ═══════════════════════════════════════════════════════════════════════════════\n// 3\. ZERO-LOOKAHEAD)',
                      'bool inTradeWindow = (time >= outSampleStart and time <= outSampleEnd)\nbool useDateFilter = true\n', code)

    with open(TEMP_PINE, "w", encoding="utf-8") as f:
        f.write(code)
    return TEMP_PINE

def run_test(symbol="BATS:SPY", interval="1D", pine_path=TEMP_PINE):
    cmd = [
        PYTHON_EXE, RUNNER_PY,
        "--pine", os.path.basename(pine_path),
        "--symbol", symbol,
        "--interval", interval,
        "--wait", "6"
    ]
    res = subprocess.run(cmd, cwd=ROOT_DIR, capture_output=True, text=True, encoding="utf-8")
    lines = res.stdout.strip().split("\n")
    json_str = ""
    recording = False
    for line in reversed(lines):
        if "}" in line:
            recording = True
        if recording:
            json_str = line + "\n" + json_str
        if "{" in line and recording:
            break
    try:
        return json.loads(json_str)
    except Exception as e:
        print("Failed to parse json:", e, "\nSTDOUT:", res.stdout, "\nSTDERR:", res.stderr)
        return None

if __name__ == "__main__":
    test_grid = [
        # Sweep ATR Stop Multipliers
        (2.4, 3.0, 5),
        (2.8, 3.0, 5),
        (3.2, 3.0, 5),
        # Sweep Take Profit Multiples
        (2.8, 2.5, 5),
        (2.8, 3.5, 5),
        # Sweep Pivot Confirmations
        (2.8, 3.0, 3),
        (2.8, 3.0, 8),
    ]

    results = []
    print(f"Sweeping {len(test_grid)} configurations on SPY 1D...")
    for atr, tp, piv in test_grid:
        print(f"\n--- Testing atrStopMult={atr}, tpMultiple={tp}, pivotLR={piv} ---")
        pfile = make_sweep_variant(atr_mult=atr, tp_mult=tp, pivot_lr=piv)
        data = run_test("BATS:SPY", "1D", pfile)
        if data:
            rec = {
                "atrStopMult": atr,
                "tpMultiple": tp,
                "pivotLR": piv,
                "net_profit_pct": data.get("net_profit_pct"),
                "profit_factor": data.get("profit_factor"),
                "max_drawdown_pct": data.get("max_drawdown_pct"),
                "win_rate_pct": data.get("win_rate_pct"),
                "total_closed_trades": data.get("total_closed_trades"),
                "sharpe_ratio": data.get("sharpe_ratio")
            }
            results.append(rec)
            print("Result:", json.dumps(rec, indent=2))

    with open(SWEEP_RESULTS, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved {len(results)} sweep results to {SWEEP_RESULTS}")
