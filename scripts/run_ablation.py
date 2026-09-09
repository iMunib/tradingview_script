"""Leave-one-out indicator ablation (Phase 4).

Frozen list (spec): RSI-14, MACD Histogram, Fisher-9, Dual %R, Buy/Sell Vol%,
CMF-20, WaveTrend Godmode, W200 Macro, FRED PERMIT.
WaveTrend is ABSENT from the master source: emitted as status=absent (not
ablatable; recommendation: do not add unvalidated indicators).

Each other indicator is neutralized by a documented source transform (constant
that removes its vote/gate contribution without touching anything else):
  rsi14     : rsi := 50.0            (kills RSI divergence votes; opens 42-60 zone)
  macd      : macdHist := 0.0        (kills MACD-hist divergence votes)
  fisher    : fish := 0.0            (kills hooks, fish exit, fish votes, fish>1.30 leg)
  dualpr    : prFast := -50.0; prSlow := -50.0 (kills %R reversal/OB/OS)
  volpct    : buyVolPct := 0.5; sellVolPct := 0.5 (volume gates fall back to OBV/MFI)
  cmf20     : cmf := 0.0             (kills CMF>0.05 absorption leg)
  w200      : useWeeklyFilter default true->false (macro gate pass-through)
  permit    : macroGate drops housing leg (macroGate = macroTrendBull)

Windows: Full history + W5 test (2025-2026, the powered OOS window).
degradation_pct here = sensitivity vs same-window baseline:
  (PF_baseline - PF_excluded)/PF_baseline*100 — NOT time degradation. Labeled.

Output: metrics/indicator_ablation_results.csv columns:
  indicator,status,asset,timeframe,window,PF,win_rate_pct,total_trades,
  max_drawdown_pct,degradation_pct
Baselines (status=included) quoted from all_assets_evaluation.json (Full) and
walkforward_windows.csv (W5 test) — no re-run.
"""
import asyncio
import csv
import json
import os
import re
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)
import runner
from scripts.evaluate_all_assets import persistent_pipeline, ensure_browser
from scripts.run_phase3 import variant as p3_variant, CELLS  # noqa

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)

MASTER = os.path.join(ROOT_DIR, "FINAL_OPTIMIZED_STRATEGY.pine")
TMP = os.path.join(ROOT_DIR, ".abl_tmp")
OUT_CSV = os.path.join(ROOT_DIR, "metrics", "indicator_ablation_results.csv")

OFF = {
    "RSI-14": ([(r"rsi = ta\.rsi\(close, rsiLength\)",
                  "rsi = ta.rsi(close, rsiLength)\nrsi := 50.0")],),
    "MACD-Histogram": ([(r"\[macdLine, signalLine, macdHist\] = ta\.macd\(close, 12, 26, 9\)",
                         "[macdLine, signalLine, macdHist] = ta.macd(close, 12, 26, 9)\nmacdHist := 0.0")],),
    "Fisher-9": ([(r"fish := 0\.5 \* math\.log\(\(1 \+ fVal\) / \(1 - fVal\)\) \+ 0\.5 \* nz\(fish\[1\]\)",
                   "fish := 0.5 * math.log((1 + fVal) / (1 - fVal)) + 0.5 * nz(fish[1])\nfish := 0.0")],),
    "Dual-%R": ([(r"prSlow = prSlowDen != 0 \? -100 \* \(prSlowHigh - close\) / prSlowDen : -50\.0",
                  "prSlow = prSlowDen != 0 ? -100 * (prSlowHigh - close) / prSlowDen : -50.0\nprFast := -50.0\nprSlow := -50.0")],),
    "BuySell-VolPct": ([(r"sellVolPct = \(buyVol \+ sellVol > 0\) \? sellVol / \(buyVol \+ sellVol\) : 0\.5",
                        "sellVolPct = (buyVol + sellVol > 0) ? sellVol / (buyVol + sellVol) : 0.5\nbuyVolPct := 0.5\nsellVolPct := 0.5")],),
    "CMF-20": ([(r"cmf = cmfDen != 0 \? cmfNum / cmfDen : 0\.0",
                 "cmf = cmfDen != 0 ? cmfNum / cmfDen : 0.0\ncmf := 0.0")],),
    "W200-Macro": ([(r'useWeeklyFilter   = input\.bool\(true, "Require Macro Regime EMA Filter"',
                     'useWeeklyFilter   = input.bool(false, "Require Macro Regime EMA Filter"')],),
    "PERMIT": ([(r"macroGate = macroTrendBull and \(isCrypto or na\(permits\) or permitsSlope >= -50\.0\)",
                 "macroGate = macroTrendBull")],),
}


def ablate(code, ind):
    for pat, rep in OFF[ind][0]:
        code2 = re.sub(pat, rep, code)
        assert code2 != code, f"transform failed for {ind}: {pat[:60]}"
        code = code2
    return code


def sens(base_pf, pf):
    if base_pf is None or pf is None or not base_pf:
        return ""
    return round((base_pf - pf) / base_pf * 100.0, 2)


async def main():
    only = None
    for i, a in enumerate(sys.argv[1:]):
        if a == "--only" and i + 1 < len(sys.argv[1:]):
            only = sys.argv[1:][i + 1]
    ensure_browser()
    base_code = open(MASTER, encoding="utf-8").read()
    for ind in OFF:
        ablate(base_code, ind)  # fail fast: verify every transform applies
    print("all 8 transforms verified against master", flush=True)
    j = json.load(open(os.path.join(ROOT_DIR, "metrics", "all_assets_evaluation.json"), encoding="utf-8"))
    wf = {(r["window"], r["asset"], r["interval"]): r for r in
          csv.DictReader(open(os.path.join(ROOT_DIR, "metrics", "walkforward_windows.csv"), encoding="utf-8"))}
    basekey = {"BATS:SPY_1D": "SPY_1D_Full"}
    jk = {"SPY_1D": "SPY_1D_Full", "QQQ_1D": "QQQ_1D_Full", "BTCUSD_1D": "BTCUSD_1D_Full",
          "SPY_1W": "SPY_1W_Full", "QQQ_1W": "QQQ_1W_Full", "BTCUSD_1W": "BTCUSD_1W_Full"}
    rows = []
    # baseline rows
    for prefix, sym, tf in CELLS:
        b = j[jk[prefix]]
        rows.append({"indicator": "ALL", "status": "included", "asset": sym,
                     "timeframe": tf, "window": "Full",
                     "PF": b["profit_factor"], "win_rate_pct": b["win_rate_pct"],
                     "total_trades": b["total_closed_trades"],
                     "max_drawdown_pct": b["max_drawdown_pct"], "degradation_pct": ""})
        w5 = wf[("W5", sym, tf)]
        rows.append({"indicator": "ALL", "status": "included", "asset": sym,
                     "timeframe": tf, "window": "W5-test",
                     "PF": w5["test_PF"], "win_rate_pct": "",
                     "total_trades": w5["test_N"],
                     "max_drawdown_pct": w5["test_DD"], "degradation_pct": ""})
    client = runner.CDPClient(runner.get_ws_url())
    await client.connect()
    await client.find_tradingview_target()
    try:
        for ind in OFF:
            for prefix, sym, tf in CELLS:
                if only and prefix != only:
                    continue
                for win, warg in (("Full", None), ("W5-test", ("2025-01-01", "2026-12-31"))):
                    code = ablate(base_code, ind)
                    os.makedirs(TMP, exist_ok=True)
                    tag = f"abl_{ind}_{prefix}_{win}".replace("%", "pct").replace("-", "_")
                    path = os.path.join(TMP, tag + ".pine")
                    if warg:
                        code = re.sub(r'useDateFilter\s*=\s*input\.bool\(false[^\n]*\)',
                                      'useDateFilter       = true', code)
                        import datetime as _dt  # local import, no behavior change
                        body = ("// GENERATE-IS-START\nbool inTradeWindow = "
                                "(time >= timestamp(2025, 1, 1, 0, 0) and time <= timestamp(2026, 12, 31, 0, 0))\n"
                                "// GENERATE-IS-END")
                        code = re.sub(r'// GENERATE-IS-START[\s\S]*?// GENERATE-IS-END', body, code)
                    open(path, "w", encoding="utf-8").write(code)
                    print(f">>> {ind} EXCLUDED {prefix} {win} ...", flush=True)
                    out = await persistent_pipeline(client, path, sym, tf, wait_sec=6)
                    base_pf = (j[jk[prefix]]["profit_factor"] if win == "Full"
                               else (float(wf[("W5", sym, tf)]["test_PF"])
                                     if wf[("W5", sym, tf)]["test_PF"] not in ("", None) else None))
                    rows.append({"indicator": ind, "status": "excluded", "asset": sym,
                                 "timeframe": tf, "window": win,
                                 "PF": out.get("profit_factor"), "win_rate_pct": out.get("win_rate_pct"),
                                 "total_trades": out.get("total_closed_trades"),
                                 "max_drawdown_pct": out.get("max_drawdown_pct"),
                                 "degradation_pct": sens(base_pf, out.get("profit_factor"))})
                    print(f"    PF={out.get('profit_factor')} N={out.get('total_closed_trades')} "
                          f"sens={rows[-1]['degradation_pct']}", flush=True)
                    await asyncio.sleep(1.0)
    finally:
        await client.close()
    # WaveTrend absent rows
    for prefix, sym, tf in CELLS:
        for win in ("Full", "W5-test"):
            rows.append({"indicator": "WaveTrend-Godmode", "status": "absent-not-in-master",
                         "asset": sym, "timeframe": tf, "window": win,
                         "PF": "", "win_rate_pct": "", "total_trades": "",
                         "max_drawdown_pct": "", "degradation_pct": ""})
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["indicator", "status", "asset", "timeframe",
                                          "window", "PF", "win_rate_pct", "total_trades",
                                          "max_drawdown_pct", "degradation_pct"])
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {len(rows)} rows to {OUT_CSV}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
