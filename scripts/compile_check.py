"""Compile-check a Pine file on the live TradingView chart (no metrics writes).

Reuses runner.CDPClient and scripts.evaluate_all_assets.persistent_pipeline,
which short-circuits with {'status': 'compile_error', 'errors': [...]} when
Monaco reports severity-8 markers. Prints COMPILE_OK or the error list.

Usage: python scripts/compile_check.py [pine_file] [symbol] [interval]
"""
import asyncio
import json
import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)
import runner
from scripts.evaluate_all_assets import persistent_pipeline


async def main():
    pine = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT_DIR, "FINAL_OPTIMIZED_STRATEGY.pine")
    symbol = sys.argv[2] if len(sys.argv) > 2 else "BATS:SPY"
    interval = sys.argv[3] if len(sys.argv) > 3 else "1D"
    ws_url = runner.get_ws_url()
    client = runner.CDPClient(ws_url)
    await client.connect()
    await client.find_tradingview_target()
    out = await persistent_pipeline(client, pine, symbol, interval, wait_sec=8)
    if out.get("status") == "compile_error":
        print("COMPILE_ERRORS:")
        for e in out["errors"]:
            print(f"  line {e.get('line')}:{e.get('col')} - {e.get('message')}")
        sys.exit(2)
    # Hardening: Monaco-marker lookup can miss; the Strategy Tester report pane
    # also surfaces Pine runtime/compile errors as "Caution! ..." text.
    raw = out.get("raw_report_text") or ""
    err_sigs = ["Caution!", "cannot call", "Syntax error", "Script error",
                "Mismatched input", "no viable alternative"]
    hits = [s for s in err_sigs if s in raw]
    if hits or "requires trade data" in raw:
        print("COMPILE_OR_NODATA (report pane): signatures=" + str(hits))
        print("--- report head ---")
        print(raw[:1200])
        sys.exit(3)
    print("COMPILE_OK")
    print(json.dumps({k: v for k, v in out.items() if k != "raw_report_text"}, indent=2))
    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
