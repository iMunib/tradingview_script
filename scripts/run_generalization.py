"""Out-of-basket generalization sweep (H5): 5 untuned liquid tickers x Full/IS/OOS on 1D.

Tickers: BATS:DIA, BATS:IWM, NASDAQ:AAPL, NASDAQ:MSFT, BITSTAMP:ETHUSD.
Uses the CURRENT master + IS/OOS variants (no ticker-specific tuning — the point).
AAPL/MSFT fall through to fallbackReversal; DIA/IWM likewise; ETHUSD hits the
crypto branch. Output: metrics/generalization.json (+ appends to backtest_history).
"""
import asyncio
import json
import os
import sys
import time

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)
import runner
from scripts.evaluate_all_assets import persistent_pipeline, ensure_browser

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)

FULL_PINE = os.path.join(ROOT_DIR, "FINAL_OPTIMIZED_STRATEGY.pine")
IS_PINE = os.path.join(ROOT_DIR, "strategy_is.pine")
OOS_PINE = os.path.join(ROOT_DIR, "strategy_oos.pine")
OUT_JSON = os.path.join(ROOT_DIR, "metrics", "generalization.json")

TICKERS = [
    ("DIA_1D", "BATS:DIA"), ("IWM_1D", "BATS:IWM"), ("AAPL_1D", "NASDAQ:AAPL"),
    ("MSFT_1D", "NASDAQ:MSFT"), ("ETHUSD_1D", "BITSTAMP:ETHUSD"),
]
PERIODS = [("Full", FULL_PINE, "Full Chart History"),
           ("IS", IS_PINE, "In-Sample (2018-2024)"),
           ("OOS", OOS_PINE, "Out-of-Sample (2025-2026)")]


def slim(out, sym, sample):
    return {"symbol": sym, "interval": "1D", "sample": sample,
            "net_profit_pct": out.get("net_profit_pct"),
            "profit_factor": out.get("profit_factor"),
            "max_drawdown_pct": out.get("max_drawdown_pct"),
            "win_rate_pct": out.get("win_rate_pct"),
            "winning_trades": out.get("winning_trades"),
            "total_closed_trades": out.get("total_closed_trades")}


async def main():
    only = None
    for i, a in enumerate(sys.argv[1:]):
        if a == "--only" and i + 1 < len(sys.argv[1:]):
            only = sys.argv[1:][i + 1]
    ensure_browser()
    client = runner.CDPClient(runner.get_ws_url())
    await client.connect()
    await client.find_tradingview_target()
    data = {}
    try:
        for tag, sym in TICKERS:
            for period, pine, sample in PERIODS:
                key = f"{tag}_{period}"
                if only and key != only:
                    continue
                print(f">>> {key} {sym} 1D [{sample}] ...", flush=True)
                out = await persistent_pipeline(client, pine, sym, "1D", wait_sec=6)
                if out.get("status") == "compile_error":
                    print(f"    COMPILE ERROR {out.get('errors')}", flush=True)
                    continue
                data[key] = slim(out, sym, sample)
                print(f"    N={out.get('total_closed_trades')} PF={out.get('profit_factor')} "
                      f"DD={out.get('max_drawdown_pct')} WR={out.get('win_rate_pct')}", flush=True)
                await asyncio.sleep(1.0)
    finally:
        await client.close()
    # degradation per ticker Full-IS/OOS convention: (IS->OOS)
    for tag, sym in TICKERS:
        a, b = data.get(f"{tag}_IS"), data.get(f"{tag}_OOS")
        if a and b and a.get("profit_factor") and b.get("profit_factor"):
            data[f"{tag}_degradation_pct"] = round(
                (a["profit_factor"] - b["profit_factor"]) / a["profit_factor"] * 100.0, 2)
    json.dump(data, open(OUT_JSON, "w", encoding="utf-8"), indent=2)
    print(f"Wrote {len(data)} keys to {OUT_JSON}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
