import asyncio
import os
import sys
import json
import time
import re

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)
import runner
import scripts.evaluate_all_assets as evaluator

async def run_single(symbol="BITSTAMP:BTCUSD", interval="1W", pine_file=None, sample="Out-of-Sample (2025-2026)"):
    if pine_file is None:
        pine_file = os.path.join(ROOT_DIR, "strategy_oos.pine")
    
    # Partition if sample window specified
    actual_pine = pine_file
    if sample in ["IS", "In-Sample (2018-2024)", "OOS", "Out-of-Sample (2025-2026)", "Full", "Full (2018-2026)"]:
        with open(pine_file, "r", encoding="utf-8") as f:
            code = f.read()
        if sample in ["IS", "In-Sample (2018-2024)"]:
            code = re.sub(r'// GENERATE-IS-START[\s\S]*?// GENERATE-IS-END',
                          '// GENERATE-IS-START\nbool inTradeWindow = (time >= inSampleStart and time <= inSampleEnd)\n// GENERATE-IS-END', code)
        elif sample in ["OOS", "Out-of-Sample (2025-2026)"]:
            code = re.sub(r'// GENERATE-IS-START[\s\S]*?// GENERATE-IS-END',
                          '// GENERATE-IS-START\nbool inTradeWindow = (time >= outSampleStart and time <= outSampleEnd)\n// GENERATE-IS-END', code)
        elif sample in ["Full", "Full (2018-2026)"]:
            code = re.sub(r'// GENERATE-IS-START[\s\S]*?// GENERATE-IS-END',
                          '// GENERATE-IS-START\nbool inTradeWindow = (time >= inSampleStart and time <= outSampleEnd)\n// GENERATE-IS-END', code)
        tmp_dir = os.path.join(ROOT_DIR, ".diag_tmp")
        os.makedirs(tmp_dir, exist_ok=True)
        actual_pine = os.path.join(tmp_dir, "quick_test_tmp.pine")
        with open(actual_pine, "w", encoding="utf-8") as f:
            f.write(code)

    ws_url = runner.get_ws_url()
    client = runner.CDPClient(ws_url)
    await client.connect()
    await client.find_tradingview_target()
    
    print(f"Testing {symbol} {interval} [{sample}] with {os.path.basename(pine_file)}...")
    t0 = time.time()
    res = await evaluator.persistent_pipeline(client, actual_pine, symbol, interval, wait_sec=5)
    t1 = time.time()
    
    print(f"Elapsed: {t1 - t0:.1f}s")
    if res:
        print(f"PF: {res.get('profit_factor')} | Trades: {res.get('total_closed_trades')} | WinRate: {res.get('win_rate_pct')}% | Net: {res.get('net_profit_pct')}% | DD: {res.get('max_drawdown_pct')}%")
    else:
        print("Failed to get metrics")
    await client.close()
    return res

if __name__ == "__main__":
    sym = sys.argv[1] if len(sys.argv) > 1 else "BITSTAMP:BTCUSD"
    tf = sys.argv[2] if len(sys.argv) > 2 else "1W"
    pine = sys.argv[3] if len(sys.argv) > 3 else os.path.join(ROOT_DIR, "strategy_oos.pine")
    sample = sys.argv[4] if len(sys.argv) > 4 else "Out-of-Sample (2025-2026)"
    asyncio.run(run_single(sym, tf, pine, sample))
