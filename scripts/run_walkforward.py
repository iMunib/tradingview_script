"""Walk-forward runner (Phase 2): 5 overlapping train/test windows.

For a rule-based strategy nothing is refit — each window REPORTS test-period
PF/DD/degradation-vs-train plus the train-period cell, one row per window per
asset in metrics/walkforward_windows.csv. Reuses persistent_pipeline from
evaluate_all_assets (single WS session). No pooled headline is computed here;
verdicts stay per-asset per the mandate.

Windows (test year + train span):
  W1 test 2022 / train 2016-2021, W2 test 2023 / train 2017-2022,
  W3 test 2024 / train 2018-2023, W4 test 2025 / train 2019-2024,
  W5 test 2026YTD / train 2020-2025.

Usage: python scripts/run_walkforward.py [--test-only]
Cells: 6 asset/TF x 5 windows x (test [+ train]) = 30 (or 60). ~5 min per 24 cells.
Output columns: window,asset,interval,train_start,train_end,test_start,test_end,
  train_PF,train_N,train_DD,test_PF,test_N,test_DD,degradation_pct,low_n_flag
"""
import asyncio
import csv
import os
import re
import sys
import time

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)
import runner
from scripts.evaluate_all_assets import persistent_pipeline, ensure_browser

BASE_PINE = os.path.join(ROOT_DIR, "FINAL_OPTIMIZED_STRATEGY.pine")
WF_DIR = os.path.join(ROOT_DIR, ".wf_tmp")
OUT_CSV = os.path.join(ROOT_DIR, "metrics", "walkforward_windows.csv")

WINDOWS = [
    ("W1", "2016-01-01", "2021-12-31", "2022-01-01", "2022-12-31"),
    ("W2", "2017-01-01", "2022-12-31", "2023-01-01", "2023-12-31"),
    ("W3", "2018-01-01", "2023-12-31", "2024-01-01", "2024-12-31"),
    ("W4", "2019-01-01", "2024-12-31", "2025-01-01", "2025-12-31"),
    ("W5", "2020-01-01", "2025-12-31", "2026-01-01", "2026-12-31"),
]
ASSETS = [("BATS:SPY", "1D"), ("BATS:QQQ", "1D"), ("BITSTAMP:BTCUSD", "1D"),
          ("BATS:SPY", "1W"), ("BATS:QQQ", "1W"), ("BITSTAMP:BTCUSD", "1W")]


def ts(date):
    y, m, d = date.split("-")
    return f"timestamp({int(y)}, {int(m)}, {int(d)}, 0, 0)"


def make_variant(start, end, tag):
    with open(BASE_PINE, encoding="utf-8") as f:
        code = f.read()
    code = re.sub(r'useDateFilter\s*=\s*input\.bool\(false[^\n]*\)',
                  'useDateFilter       = true', code)
    body = (f"// GENERATE-IS-START\nbool inTradeWindow = "
            f"(time >= {ts(start)} and time <= {ts(end)})\n// GENERATE-IS-END")
    code = re.sub(r'// GENERATE-IS-START[\s\S]*?// GENERATE-IS-END', body, code)
    os.makedirs(WF_DIR, exist_ok=True)
    path = os.path.join(WF_DIR, f"wf_{tag}.pine")
    with open(path, "w", encoding="utf-8") as f:
        f.write(code)
    return path


def deg(pf_tr, pf_te):
    if pf_tr is None or pf_te is None or not pf_tr:
        return None
    return round((pf_tr - pf_te) / pf_tr * 100.0, 2)


async def main():
    test_only = "--test-only" in sys.argv
    ensure_browser()
    ws_url = runner.get_ws_url()
    client = runner.CDPClient(ws_url)
    await client.connect()
    await client.find_tradingview_target()
    rows = []
    for w, tr_s, tr_e, te_s, te_e in WINDOWS:
        test_pine = make_variant(te_s, te_e, f"{w}_test")
        train_pine = None if test_only else make_variant(tr_s, tr_e, f"{w}_train")
        for sym, tf in ASSETS:
            te = await persistent_pipeline(client, test_pine, sym, tf)
            tr = {"profit_factor": None, "total_closed_trades": None,
                  "max_drawdown_pct": None} if test_only else \
                await persistent_pipeline(client, train_pine, sym, tf)
            n = te.get("total_closed_trades") or 0
            rows.append({
                "window": w, "asset": sym, "interval": tf,
                "train_start": tr_s, "train_end": tr_e,
                "test_start": te_s, "test_end": te_e,
                "train_PF": tr.get("profit_factor"), "train_N": tr.get("total_closed_trades"),
                "train_DD": tr.get("max_drawdown_pct"),
                "test_PF": te.get("profit_factor"), "test_N": n,
                "test_DD": te.get("max_drawdown_pct"),
                "degradation_pct": deg(tr.get("profit_factor"), te.get("profit_factor")),
                "low_n_flag": "low-N, indicative only" if n < 30 else "",
            })
            time.sleep(1.0)
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {len(rows)} rows to {OUT_CSV}")
    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
