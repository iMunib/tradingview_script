import asyncio
import os
import sys
import json
import time

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)
import runner
import scripts.evaluate_all_assets as evaluator

async def run_matrix(pine_file, tasks=None):
    if tasks is None:
        tasks = [
            {"sym": "BATS:SPY", "tf": "1D", "sample": "IS"},
            {"sym": "BATS:SPY", "tf": "1D", "sample": "OOS"},
            {"sym": "BATS:QQQ", "tf": "1D", "sample": "IS"},
            {"sym": "BATS:QQQ", "tf": "1D", "sample": "OOS"},
            {"sym": "BITSTAMP:BTCUSD", "tf": "1D", "sample": "IS"},
            {"sym": "BITSTAMP:BTCUSD", "tf": "1D", "sample": "OOS"},
            {"sym": "BATS:SPY", "tf": "1W", "sample": "IS"},
            {"sym": "BATS:SPY", "tf": "1W", "sample": "OOS"},
            {"sym": "BATS:QQQ", "tf": "1W", "sample": "IS"},
            {"sym": "BATS:QQQ", "tf": "1W", "sample": "OOS"},
            {"sym": "BITSTAMP:BTCUSD", "tf": "1W", "sample": "IS"},
            {"sym": "BITSTAMP:BTCUSD", "tf": "1W", "sample": "OOS"},
        ]
    
    ws_url = runner.get_ws_url()
    client = runner.CDPClient(ws_url)
    await client.connect()
    await client.find_tradingview_target()
    
    results = {}
    with open(pine_file, "r", encoding="utf-8") as f:
        base_code = f.read()
        
    for t in tasks:
        sym = t["sym"]
        tf = t["tf"]
        s = t["sample"]
        key = f"{sym}_{tf}_{s}"
        
        # Prepare pine code for this sample window
        code = base_code
        if s == "IS":
            code = code.replace("bool inTradeWindow = true", "bool inTradeWindow = (time >= inSampleStart and time <= inSampleEnd)")
            # also handle if already replaced
            if "GENERATE-IS-START" in code:
                import re
                code = re.sub(r'// GENERATE-IS-START[\s\S]*?// GENERATE-IS-END', 
                              '// GENERATE-IS-START\nbool inTradeWindow = (time >= inSampleStart and time <= inSampleEnd)\n// GENERATE-IS-END', code)
        elif s == "OOS":
            if "GENERATE-IS-START" in code:
                import re
                code = re.sub(r'// GENERATE-IS-START[\s\S]*?// GENERATE-IS-END', 
                              '// GENERATE-IS-START\nbool inTradeWindow = (time >= outSampleStart and time <= outSampleEnd)\n// GENERATE-IS-END', code)
            else:
                code = code.replace("bool inTradeWindow = true", "bool inTradeWindow = (time >= outSampleStart and time <= outSampleEnd)")
        elif s == "Full":
            if "GENERATE-IS-START" in code:
                import re
                code = re.sub(r'// GENERATE-IS-START[\s\S]*?// GENERATE-IS-END', 
                              '// GENERATE-IS-START\nbool inTradeWindow = true\n// GENERATE-IS-END', code)
        
        tmp_pine = os.path.join(ROOT_DIR, ".diag_tmp", f"tmp_{s}.pine")
        os.makedirs(os.path.dirname(tmp_pine), exist_ok=True)
        with open(tmp_pine, "w", encoding="utf-8") as f:
            f.write(code)
            
        print(f"\n>>> Running {key} ...")
        res = await evaluator.persistent_pipeline(client, tmp_pine, sym, tf, wait_sec=5)
        if res:
            results[key] = {
                "symbol": sym, "interval": tf, "sample": s,
                "pf": res.get("profit_factor"),
                "trades": res.get("total_closed_trades"),
                "win_rate": res.get("win_rate_pct"),
                "net_pct": res.get("net_profit_pct"),
                "dd_pct": res.get("max_drawdown_pct")
            }
            print(f"[{key}] PF: {res.get('profit_factor')} | N: {res.get('total_closed_trades')} | WR: {res.get('win_rate_pct')}% | Net: {res.get('net_profit_pct')}% | DD: {res.get('max_drawdown_pct')}%")
        await asyncio.sleep(1.0)
        
    await client.close()
    
    print("\n═══════════════════════ MATRIX SUMMARY ═══════════════════════")
    for k, v in results.items():
        print(f"{k:25} | PF: {str(v['pf']):6} | N: {str(v['trades']):4} | WR: {str(v['win_rate'])+'%':7} | Net: {str(v['net_pct'])+'%':8} | DD: {str(v['dd_pct'])+'%':7}")
    return results

if __name__ == "__main__":
    pine = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT_DIR, "test_strategy.pine")
    asyncio.run(run_matrix(pine))
