"""Statistical validation on trade-log CSVs (Phase 2 steps 2-4).

Inputs: metrics/trade_log_<asset>_<period>.csv with columns:
  entry_date,exit_date,entry_price,exit_price,qty,pnl,exit_reason,r_multiple
  (exit_reason in {Strong Exit, Exit Reversal, Exit Target, Exit Stop, Window End})

For each file:
  1. Block-bootstrap (contiguous blocks of 10 trades, 2000 resamples,
     seed 7): 90% CI for profit factor. Reports interval, not a point estimate.
  2. Permutation null: 2000 random sign-flips of trade P&L (destroys any
     directional edge, preserves marginals); one-sided p-value for observed PF.
     p > 0.10 -> edge statistically indistinguishable from noise (reported plainly).
  3. maxDD proxy from cumulative-P&L equity curve with 90% bootstrap CI.

Rules honored: files with N<30 are labeled 'low-N, indicative only'.
Exits tagged 'Window End' are reported separately (backtest artifact).

Usage: python scripts/stats_validation.py metrics/trade_log_SPY_1D_Full.csv [...]
Exits 3 + message if a file is missing (never fabricates).
"""
import csv
import glob
import math
import os
import random
import sys

BLOCK = 10
RESAMPLES = 2000
SEED = 7


def load(path):
    with open(path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    need = {"entry_date", "exit_date", "entry_price", "exit_price",
            "exit_reason"}
    missing = need - set(rows[0].keys() if rows else [])
    if missing:
        raise ValueError(f"{path}: missing columns {sorted(missing)}")
    # P&L column: 'pnl' canonical; 'profit_usd' (export_trade_logs.py) aliased
    pnl_key = "pnl" if "pnl" in rows[0] else (
        "profit_usd" if "profit_usd" in rows[0] else None)
    if pnl_key is None:
        raise ValueError(f"{path}: missing P&L column (need 'pnl' or 'profit_usd')")
    pnls = [float(r[pnl_key]) for r in rows]
    return rows, pnls


def profit_factor(pnls):
    gp = sum(p for p in pnls if p > 0)
    gl = -sum(p for p in pnls if p < 0)
    if gl == 0:
        return None  # no losers: PF undefined
    return gp / gl


def max_dd_proxy(pnls):
    eq, peak, mdd = 0.0, 0.0, 0.0
    for p in pnls:
        eq += p
        peak = max(peak, eq)
        mdd = max(mdd, peak - eq)
    return mdd


def block_resample(pnls, rng):
    n = len(pnls)
    out = []
    while len(out) < n:
        i = rng.randrange(0, max(1, n - BLOCK + 1))
        out.extend(pnls[i:i + BLOCK])
    return out[:n]


def ci(vals, q=0.90):
    s = sorted(v for v in vals if v is not None)
    if not s:
        return (None, None)
    lo_i = int(len(s) * (1 - q) / 2)
    hi_i = min(len(s) - 1, int(len(s) * (1 + q) / 2))
    return (round(s[lo_i], 3), round(s[hi_i], 3))


def analyze(path):
    rows, pnls = load(path)
    n = len(pnls)
    rng = random.Random(SEED)
    pf = profit_factor(pnls)
    pf_boot = [profit_factor(block_resample(pnls, rng)) for _ in range(RESAMPLES)]
    pf_ci = ci(pf_boot)
    mdd = max_dd_proxy(pnls)
    mdd_ci = ci([max_dd_proxy(block_resample(pnls, rng)) for _ in range(RESAMPLES)])
    # permutation null: random sign flips
    exceeding = 0
    trials = 0
    if pf is not None:
        for _ in range(RESAMPLES):
            null = [p * rng.choice((-1.0, 1.0)) for p in pnls]
            npf = profit_factor(null)
            if npf is not None:
                trials += 1
                if npf >= pf:
                    exceeding += 1
    p_value = round((exceeding + 1) / (trials + 1), 4) if trials else None
    verdict = ("low-N, indicative only" if n < 30 else
               "indistinguishable from noise (p>0.10)" if (p_value or 0) > 0.10 else
               "edge outside null (p<=0.10)")
    window_exits = sum(1 for r in rows if r["exit_reason"] == "Window End")
    return {"file": os.path.basename(path), "N": n,
            "PF": round(pf, 3) if pf is not None else "undefined (no losers)",
            "PF_90CI": pf_ci, "maxDD_proxy": round(mdd, 2), "maxDD_90CI": mdd_ci,
            "perm_p": p_value, "window_artifact_exits": window_exits, "verdict": verdict}


def main():
    pats = sys.argv[1:] or [os.path.join("metrics", "trade_log_*.csv")]
    files = [f for p in pats for f in (glob.glob(p) if "*" in p else [p])]
    files = [f for f in files if os.path.exists(f)]
    if not files:
        print("stats_validation: no trade_log CSVs found matching "
              + str(pats) + " — run the trade-list export first (see TOOLING.md).")
        return 3
    for path in sorted(files):
        try:
            r = analyze(path)
        except Exception as e:
            print(f"{path}: ERROR {e}")
            continue
        print(f"{r['file']}: N={r['N']} PF={r['PF']} 90%CI={r['PF_90CI']} "
              f"maxDD~{r['maxDD_proxy']} CI={r['maxDD_90CI']} p={r['perm_p']} "
              f"window_exits={r['window_artifact_exits']} -> {r['verdict']}")


if __name__ == "__main__":
    sys.exit(main() or 0)
