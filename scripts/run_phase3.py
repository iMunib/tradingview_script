"""Phase-3 sweep driver: cooldown sensitivity, fixed-capital sizing, walk-forward.

Suites (overview metrics only — no trade-log scroll needed):
  cooldown : minCooldownBars in {3,5,8,13} x 6 cells, Full history (master base)
  sizing   : riskAmount = 100000*(risk/100) [fixed] vs equity-compounding, Full x 6
  walkfwd  : 5 spec windows (train/test) x 6 cells x 2 = 60 runs

Spec windows (Phase 3.3):
  W1 train 2016-2020 / test 2021 | W2 2017-2021/2022 | W3 2018-2022/2023
  W4 2019-2023/2024 | W5 2020-2024/2025-2026

Outputs (never overwrites all_assets_evaluation.json):
  metrics/phase3_sweep.json        (cooldown + sizing runs)
  metrics/walkforward_windows.csv  (one row per window per asset)

Usage: python scripts/run_phase3.py --suite cooldown|sizing|walkfwd [--only SPY_1D]
"""
import asyncio
import csv
import json
import os
import re
import sys
import time

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)
import runner
from scripts.evaluate_all_assets import persistent_pipeline, ensure_browser

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)

MASTER = os.path.join(ROOT_DIR, "FINAL_OPTIMIZED_STRATEGY.pine")
TMP = os.path.join(ROOT_DIR, ".phase3_tmp")
SWEEP_JSON = os.path.join(ROOT_DIR, "metrics", "phase3_sweep.json")
WF_CSV = os.path.join(ROOT_DIR, "metrics", "walkforward_windows.csv")

CELLS = [
    ("SPY_1D", "BATS:SPY", "1D"), ("QQQ_1D", "BATS:QQQ", "1D"),
    ("BTCUSD_1D", "BITSTAMP:BTCUSD", "1D"), ("SPY_1W", "BATS:SPY", "1W"),
    ("QQQ_1W", "BATS:QQQ", "1W"), ("BTCUSD_1W", "BITSTAMP:BTCUSD", "1W"),
]
WINDOWS = [
    ("W1", "2016-01-01", "2020-12-31", "2021-01-01", "2021-12-31"),
    ("W2", "2017-01-01", "2021-12-31", "2022-01-01", "2022-12-31"),
    ("W3", "2018-01-01", "2022-12-31", "2023-01-01", "2023-12-31"),
    ("W4", "2019-01-01", "2023-12-31", "2024-01-01", "2024-12-31"),
    ("W5", "2020-01-01", "2024-12-31", "2025-01-01", "2026-12-31"),
]


def ts(date):
    y, m, d = date.split("-")
    return f"timestamp({int(y)}, {int(m)}, {int(d)}, 0, 0)"


def variant(code, tag, cooldown=None, fixed_capital=False, win=None):
    if cooldown is not None:
        code = re.sub(r'minCooldownBars\s*=\s*input\.int\(3,',
                      f'minCooldownBars    = input.int({cooldown},', code)
    if fixed_capital:
        code = re.sub(r'riskAmount = strategy\.equity \* \(riskPerTrade / 100\.0\)',
                      'riskAmount = 100000 * (riskPerTrade / 100.0)', code)
    if win is not None:
        s, e = win
        code = re.sub(r'useDateFilter\s*=\s*input\.bool\(false[^\n]*\)',
                      'useDateFilter       = true', code)
        body = (f"// GENERATE-IS-START\nbool inTradeWindow = "
                f"(time >= {ts(s)} and time <= {ts(e)})\n// GENERATE-IS-END")
        code = re.sub(r'// GENERATE-IS-START[\s\S]*?// GENERATE-IS-END', body, code)
    os.makedirs(TMP, exist_ok=True)
    path = os.path.join(TMP, f"p3_{tag}.pine")
    with open(path, "w", encoding="utf-8") as f:
        f.write(code)
    return path


def slim(out):
    return {k: out.get(k) for k in
            ("net_profit_pct", "profit_factor", "max_drawdown_pct",
             "win_rate_pct", "winning_trades", "total_closed_trades")}


def deg(a, b):
    if a is None or b is None or not a:
        return None
    return round((a - b) / a * 100.0, 2)


async def run_suite(client, base_code, suite, only):
    results = {}
    if suite == "cooldown":
        for cd in (3, 5, 8, 13):
            for prefix, sym, tf in CELLS:
                if only and prefix != only:
                    continue
                tag = f"CD{cd}_{prefix}"
                p = variant(base_code, tag, cooldown=cd)
                print(f">>> {tag} {sym} {tf} ...", flush=True)
                out = await persistent_pipeline(client, p, sym, tf, wait_sec=6)
                results[tag] = {"cooldown": cd, "cell": prefix, **slim(out)}
                print(f"    N={out.get('total_closed_trades')} PF={out.get('profit_factor')} "
                      f"DD={out.get('max_drawdown_pct')}", flush=True)
                await asyncio.sleep(1.0)
    elif suite == "sizing":
        for prefix, sym, tf in CELLS:
            if only and prefix != only:
                continue
            tag = f"FIXED_{prefix}"
            p = variant(base_code, tag, fixed_capital=True)
            print(f">>> {tag} {sym} {tf} ...", flush=True)
            out = await persistent_pipeline(client, p, sym, tf, wait_sec=6)
            results[tag] = {"cell": prefix, **slim(out)}
            print(f"    N={out.get('total_closed_trades')} PF={out.get('profit_factor')} "
                  f"DD={out.get('max_drawdown_pct')}", flush=True)
            await asyncio.sleep(1.0)
    elif suite == "walkfwd":
        rows = []
        for w, tr_s, tr_e, te_s, te_e in WINDOWS:
            for prefix, sym, tf in CELLS:
                if only and prefix != only:
                    continue
                ptr = variant(base_code, f"{w}_tr_{prefix}", win=(tr_s, tr_e))
                pte = variant(base_code, f"{w}_te_{prefix}", win=(te_s, te_e))
                print(f">>> {w} {prefix} train ...", flush=True)
                tr = await persistent_pipeline(client, ptr, sym, tf, wait_sec=6)
                print(f">>> {w} {prefix} test ...", flush=True)
                te = await persistent_pipeline(client, pte, sym, tf, wait_sec=6)
                tn = te.get("total_closed_trades") or 0
                rows.append({
                    "window": w, "asset": sym, "interval": tf,
                    "train_start": tr_s, "train_end": tr_e,
                    "test_start": te_s, "test_end": te_e,
                    "train_PF": tr.get("profit_factor"), "train_N": tr.get("total_closed_trades"),
                    "train_DD": tr.get("max_drawdown_pct"),
                    "test_PF": te.get("profit_factor"), "test_N": tn,
                    "test_DD": te.get("max_drawdown_pct"),
                    "degradation_pct": deg(tr.get("profit_factor"), te.get("profit_factor")),
                    "low_n_flag": "low-N, indicative only" if tn < 30 else "",
                })
                print(f"    train PF={tr.get('profit_factor')} N={tr.get('total_closed_trades')} | "
                      f"test PF={te.get('profit_factor')} N={tn} deg={rows[-1]['degradation_pct']}",
                      flush=True)
                await asyncio.sleep(1.0)
        with open(WF_CSV, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        print(f"Wrote {len(rows)} rows to {WF_CSV}", flush=True)
        results["_walkforward_rows"] = len(rows)
    return results


async def main():
    suite = "cooldown"
    only = None
    args = sys.argv[1:]
    for i, a in enumerate(args):
        if a == "--suite" and i + 1 < len(args):
            suite = args[i + 1]
        if a == "--only" and i + 1 < len(args):
            only = args[i + 1]
    assert suite in ("cooldown", "sizing", "walkfwd"), suite
    ensure_browser()
    with open(MASTER, encoding="utf-8") as f:
        base_code = f.read()
    assert "minCooldownBars" in base_code, "master lacks minCooldownBars input!"
    client = runner.CDPClient(runner.get_ws_url())
    await client.connect()
    await client.find_tradingview_target()
    t0 = time.time()
    try:
        res = await run_suite(client, base_code, suite, only)
    finally:
        await client.close()
    if suite in ("cooldown", "sizing"):
        prev = {}
        if os.path.exists(SWEEP_JSON):
            prev = json.load(open(SWEEP_JSON, encoding="utf-8"))
        prev.update(res)
        json.dump(prev, open(SWEEP_JSON, "w", encoding="utf-8"), indent=2)
        print(f"Merged {len(res)} runs into {SWEEP_JSON} ({time.time()-t0:.0f}s)", flush=True)
    print("SUITE DONE:", suite)


if __name__ == "__main__":
    asyncio.run(main())
