"""
Autonomous Optimization & Walk-Forward Validation Engine
Iterates through parameter sweeps, executes backtests via runner.py,
and records quantitative comparisons across assets and in/out-of-sample periods.
"""

import os
import sys
import json
import time
import subprocess
import itertools

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STRATEGY_TEMPLATE = os.path.join(ROOT_DIR, "strategy.pine")
TEMP_PINE = os.path.join(ROOT_DIR, "strategy_variant.pine")
PYTHON_EXE = os.path.join(ROOT_DIR, "venv", "Scripts", "python.exe")
RUNNER_PY = os.path.join(ROOT_DIR, "runner.py")
OPTIM_RESULTS = os.path.join(ROOT_DIR, "metrics", "optimization_results.json")

def generate_variant(rsi_len=14, atr_mult=2.5, obv_len=20, date_filter=False, date_mode="All"):
    with open(STRATEGY_TEMPLATE, "r", encoding="utf-8") as f:
        code = f.read()

    import re
    # Replace inputs with explicit literal assignments to completely bypass TradingView input caching
    code = re.sub(r'rsiLength\s*=\s*input\.int\(.*', f'rsiLength = {rsi_len}', code)
    code = re.sub(r'atrStopMult\s*=\s*input\.float\(.*', f'atrStopMult = {atr_mult}', code)
    code = re.sub(r'obvEmaLength\s*=\s*input\.int\(.*', f'obvEmaLength = {obv_len}', code)

    if date_mode == "In-Sample (2018-2024)":
        window_logic = "inTradeWindow = (time >= inSampleStart and time <= inSampleEnd)\nuseDateFilter = true"
    elif date_mode == "Out-of-Sample (2025-2026)":
        window_logic = "inTradeWindow = (time >= outSampleStart and time <= outSampleEnd)\nuseDateFilter = true"
    else:
        window_logic = "inTradeWindow = true\nuseDateFilter = false"

    code = re.sub(r'group_dates\s*=\s*[\s\S]*?(?=// ─── DATE WINDOW CALCULATION)', '', code)
    code = re.sub(r'inTradeWindow\s*=\s*true[\s\S]*?(?=// ─── 1\. MACRO)', f'{window_logic}\n\n', code)

    with open(TEMP_PINE, "w", encoding="utf-8") as f:
        f.write(code)
    return TEMP_PINE

def run_backtest(symbol, interval, pine_file=TEMP_PINE, wait_sec=6):
    cmd = [
        PYTHON_EXE, RUNNER_PY,
        "--pine", os.path.basename(pine_file),
        "--symbol", symbol,
        "--interval", interval,
        "--wait", str(wait_sec)
    ]
    res = subprocess.run(cmd, cwd=ROOT_DIR, capture_output=True, text=True, encoding="utf-8")
    try:
        # Last JSON object printed
        lines = res.stdout.strip().split("\n")
        json_str = ""
        brace_count = 0
        recording = False
        for line in reversed(lines):
            if "}" in line:
                recording = True
            if recording:
                json_str = line + "\n" + json_str
            if "{" in line and recording:
                break
        data = json.loads(json_str)
        return data
    except Exception as e:
        print(f"Error parsing runner output: {e}\nSTDOUT: {res.stdout}\nSTDERR: {res.stderr}")
        return None

def main():
    # Grid of candidate parameter configurations
    configs = [
        # (rsi_len, atr_mult, obv_len)
        (14, 2.5, 20), # Baseline
        (10, 2.0, 20),
        (14, 2.0, 10),
        (21, 2.5, 50),
        (14, 3.0, 20),
        (10, 2.5, 10),
        (21, 2.0, 20),
    ]

    symbols = ["SPY", "QQQ", "BTCUSD"]
    all_results = []

    print(f"Starting parameter sweeps across {len(configs)} configurations and {len(symbols)} symbols...")

    for rsi_len, atr_mult, obv_len in configs:
        cfg_name = f"RSI_{rsi_len}_ATR_{atr_mult}_OBV_{obv_len}"
        print(f"\n==========================================")
        print(f"Testing Config: {cfg_name}")
        print(f"==========================================")

        for sym in symbols:
            # 1. Full period (1D)
            generate_variant(rsi_len, atr_mult, obv_len, date_filter=False, date_mode="All")
            full_res = run_backtest(sym, "1D")
            print(f"[{sym} 1D Full] PF: {full_res.get('profit_factor') if full_res else 'N/A'}, MaxDD: {full_res.get('max_drawdown_pct') if full_res else 'N/A'}%, Trades: {full_res.get('total_closed_trades') if full_res else 'N/A'}")

            # 2. In-Sample (2018-2024)
            generate_variant(rsi_len, atr_mult, obv_len, date_filter=True, date_mode="In-Sample (2018-2024)")
            is_res = run_backtest(sym, "1D")
            print(f"[{sym} 1D In-Sample] PF: {is_res.get('profit_factor') if is_res else 'N/A'}, MaxDD: {is_res.get('max_drawdown_pct') if is_res else 'N/A'}%, Trades: {is_res.get('total_closed_trades') if is_res else 'N/A'}")

            # 3. Out-of-Sample (2025-2026)
            generate_variant(rsi_len, atr_mult, obv_len, date_filter=True, date_mode="Out-of-Sample (2025-2026)")
            oos_res = run_backtest(sym, "1D")
            print(f"[{sym} 1D Out-Sample] PF: {oos_res.get('profit_factor') if oos_res else 'N/A'}, MaxDD: {oos_res.get('max_drawdown_pct') if oos_res else 'N/A'}%, Trades: {oos_res.get('total_closed_trades') if oos_res else 'N/A'}")

            record = {
                "config": {"rsi_length": rsi_len, "atr_multiplier": atr_mult, "obv_ema_length": obv_len},
                "symbol": sym,
                "interval": "1D",
                "full_sample": full_res,
                "in_sample": is_res,
                "out_of_sample": oos_res
            }
            all_results.append(record)

            with open(OPTIM_RESULTS, "w", encoding="utf-8") as f:
                json.dump(all_results, f, indent=2)

    print("\nOptimization completed! Results written to:", OPTIM_RESULTS)

if __name__ == "__main__":
    main()
