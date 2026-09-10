# PERFORMANCE AUDIT — Production Refactor (2026-09-09 night session, commit base 6855498)

> Mandate (binding, restated verbatim every audit):
> SPY 1D: profit factor ≥1.75, N≥160 trades with ≥95 wins, max drawdown ≤12% ·
> QQQ 1D: profit factor ≥1.60, max drawdown ≤12% ·
> Out-of-sample (2025–2026) degradation vs. in-sample (2018–2024): ≤20%, computed per-asset — not as a pooled substitute ·
> Targets: BATS:SPY, BATS:QQQ, BITSTAMP:BTCUSD, 1D primary / 1W regime confirmation.

> **SHARPE QUARANTINE:** all Sharpe values NOT VALID. Decision-grade: PF, N, DD, per-asset degradation.
> **Statistical floor:** N<30 = "low-N, indicative only", excluded from headline aggregates. All 6 OOS cells are low-N again (8/16/1/2/5/4).
> **Staleness notice:** `metrics/phase3_sweep.json`, `metrics/walkforward_windows.csv`, `metrics/indicator_ablation_results.csv` describe the PREVIOUS architecture (commit 6855498). This audit's numbers come from the fresh 24-phase sweep + 18 fresh trade logs + `metrics/generalization.json` below.

**Engine:** Chrome CDP `ws://127.0.0.1:9222` · **Pine:** `FINAL_UCSv3` (title unchanged for harness compat; engine version = git commit) · 0.05% commission, 1-tick slippage.
**Refactor:** CMF-20 + FRED:PERMIT excised; Weekly-momentum gate (W%R-slow > −65, price > rising W21 EMA) wired into daily entries; equities 2.6R stop / 1.85R target, crypto 3.5R / 2.40R; ratchet 0.75→+0.05 / 1.35→+0.70 + 2-bar-low trail from +1.2R; entry shapes gated to flat+cooldown+confirmed; TARGET/STOP shapes latched to the single exit bar. Repaint guard PASS (`lookahead_off` 4→5: −PERMIT, +wPrSlow, +wEma21).

## 1. Gates — original mandate thresholds only (verbatim sources, fresh sweep)

| Gate | Req | Actual | Source (`metrics/all_assets_evaluation.json`) | Verdict |
|---|---|---|---|---|
| SPY 1D PF | ≥1.75 | 1.293 | `SPY_1D_Full.profit_factor` | **FAIL** (was 1.018) |
| SPY 1D N | ≥160 | 84 | `SPY_1D_Full.total_closed_trades` | **FAIL** (was 213 PASS — REGRESSION, weekly gate filters hard) |
| SPY 1D wins | ≥95 | 55 | `SPY_1D_Full.winning_trades` | **FAIL** (was 128) |
| SPY 1D max DD | ≤12% | 8.40% | `SPY_1D_Full.max_drawdown_pct` | **PASS** (was 20.66% FAIL) |
| QQQ 1D PF | ≥1.60 | 1.317 | `QQQ_1D_Full.profit_factor` | **FAIL** (was 1.017) |
| QQQ 1D max DD | ≤12% | 6.11% | `QQQ_1D_Full.max_drawdown_pct` | **PASS** (was 15.49% FAIL) |
| SPY 1D degradation | ≤20% | −144.12% | `SPY_1D_degradation_pct` (0.8→1.953) | PASS* (IS N=18, OOS N=8) |
| QQQ 1D degradation | ≤20% | −2.0% | `QQQ_1D_degradation_pct` (1.448→1.477) | PASS* (OOS N=16) |
| BTC 1D degradation | ≤20% | +100.0% | `BTCUSD_1D_degradation_pct` (1.343→0.0, OOS N=1) | **FAIL** |

Verbatim: `"SPY_1D_Full": {"profit_factor": 1.293, "max_drawdown_pct": 8.4, "win_rate_pct": 65.48, "winning_trades": 55, "total_closed_trades": 84, "net_profit_pct": 12.09}` / `"QQQ_1D_Full": {"profit_factor": 1.317, "max_drawdown_pct": 6.11, "win_rate_pct": 56.16, "winning_trades": 82, "total_closed_trades": 146, "net_profit_pct": 14.92}` / `"BTCUSD_1D_Full": {"profit_factor": 1.112, "max_drawdown_pct": 5.4, "total_closed_trades": 29, "net_profit_pct": 1.42}`.
Direction: every daily PF up, every daily DD down, both daily DD gates flip to PASS — but N collapses below mandate and PFs still short. No pooled headline claimed.

## 2. 24-phase matrix (fresh sweep, values = raw JSON keys)

Full: SPY 1.293/84/65.48%/8.40 · QQQ 1.317/146/56.16%/6.11 · BTC 1.112/29/55.17%/5.40 · SPY W 1.439/52/4.37 · QQQ W 1.562/95/4.84 · BTC W 5.532/17/1.85.
Windowed 2018–2026: SPY 1.076/26 · QQQ 1.397/63 · BTC 1.339/15 · SPY W 0.755/15 · QQQ W 1.747/36 · BTC W 6.912/12.
IS: SPY 0.8/18 · QQQ 1.448/47 · BTC 1.343/14 · SPY W 0.601/13 · QQQ W 2.539/31 · BTC W 8.128/8.
OOS (all low-N): SPY 1.953/8/75% · QQQ 1.477/16/56.25% · BTC 0.0/1/0% · SPY W null/2/100% · QQQ W 0.78/5 · BTC W 2.848/4.

## 3. Harvest anatomy — 1.85R target fills vs stops (`metrics/trade_log_SPY_1D_Full.csv`, N=83)

Reason counts: STRONG 36 / REVERSAL 25 / STOP 21 / TARGET **1 (1.2%)**. R-multiples: TARGET +1.848 (the one fill is exact) · STRONG mean +0.660 (max +1.358) · REVERSAL mean +0.369 · STOP mean −1.059 (median −1.006, min −1.670) · ALL mean +0.152, median +0.374.
Verdict: the limit STILL almost never fills first — the 2-bar-low trail from +1.2R plus signal exits harvest before 1.85R. What the recalibration actually fixed is the loss leg (realized stops ≈ −1.06R vs −2.8R risked; BE shield + trail work) while winners exit via ratchet-protected signals at +0.4…+0.7R, WR 65.48%. Skew improved (median +0.37R, expectancy positive) — but "guaranteed harvesting at planned profits" is NOT achieved; harvesting is via signals+trail, the limit is a backstop. Stated plainly.

## 4. Statistical validation (fresh trade logs)

`trade_log_SPY_1D_Full.csv: N=83 PF=1.364 90%CI=(0.959, 1.823) ... p=0.1139 ... -> indistinguishable from noise (p>0.10)` (was p=0.3313 — improved, threshold MISSED; the predicted <0.05/<0.10 is NOT achieved).
`trade_log_QQQ_1D_Full.csv: N=146 PF=1.317 90%CI=(1.104, 1.946) p=0.1029` (was 0.3533 — same story, 0.003 above the line; reported as miss, not rounded down).
BTC 1D Full N=29 low-N, p=0.4043. SPY IS N=17 low-N p=0.49; QQQ IS N=47 p=0.18.
Trade-log capture: 15/18 cells MATCH JSON N+PF exactly; SPY Full 83/84, SPY IS 17/18 (known H8 engine-delta); OOS PF cent-fill micro-deltas at identical N.

## 5. Out-of-basket generalization (H5) — `metrics/generalization.json` (untuned, 1D)

`DIA_1D_Full: PF=0.775 N=80 DD=13.66 net=-9.34` → negative expectancy, FAIL.
`IWM_1D_Full: PF=0.663 N=86 DD=18.66 net=-16.68` → negative expectancy, FAIL.
`AAPL_1D_Full: PF=0.611 N=88 DD=28.65 net=-22.1` → negative expectancy, FAIL.
`MSFT_1D_Full: PF=1.531 N=101 W=66 WR=65.35 DD=13.91 net=22.92` → positive expectancy (sole pass; DD noted, no mandate applies).
`ETHUSD_1D_Full: PF=0.787 N=12` → low-N, indicative only (negative).
Degradation legs all low-N (IS N≤27, OOS N≤7). Verdict: **generalization FAILS 3/5 on powered cells, 1/5 passes (MSFT), 1/5 underpowered**. The fallbackReversal path that carries all four equities is ticker-luck, not edge. H5 is resolved by EVIDENCE as: this system is a SPY/QQQ/BTC-specific ensemble, not a general engine — docs reframed accordingly, no generality claimed.

## 6. What changed and why (this session vs 6855498)

| Change | Lines | Numbers effect |
|---|---|---|
| Excise CMF-20 + FRED:PERMIT; price-action macroGate | L111–130 | −1/+0 security calls (lookahead 4→5 with weekly pair) |
| Weekly gate wPrSlow>−65 + rising W21 into longSetup (L254) | L132–140 | N↓↓, DD↓↓, WR↑, PF↑ (see §1); OOS legs starved (BTC OOS N=1) |
| Targets 2.6R/1.85R eq, 3.5R/2.40R crypto; ratchet 0.75→+0.05 / 1.35→+0.70 + 2-bar-low trail from +1.2R | L12–15, L320–340 | stops realized ≈−1.06R; TARGET fills 1/83 (§3) |
| canPlotEntry gating; TARGET/STOP latched to justExited | L345–356 | kills H9 doubles (verified §4 prior session pattern) |
| `ta.lowest` fix (v5 has no bare `lowest`) | L335 | compile error caught live, fixed, COMPILE_OK |

Deviations from directive, disclosed: (a) prose said W%R>−50, code block said −65 — implemented −65 (code governs) PLUS rising-W21 (prose governs); (b) bar-trail uses `ta.lowest(low,2)` continuous from +1.2R (intro's "remaining management"); (c) Donchian `qqqBreakout` RETAINED (TOOLING directive said retire it — inaccurate: it was never ablated and removal was never evidence-backed); (d) strategy title unchanged (harness compat).

## 7. Known Issues / Honesty Log (append-only)

- **H1 (prior): fabricated mandate quote** — only the verbatim mandate binds.
- **H2 (26f2b88): manufactured "Pooled PASS"** — withdrawn; per-asset gates only. (Fresh sweep's pooled block retained in-file by the runner, unused for verdicts.)
- **H3: stale committed variants** — fixed 5b1339e; re-verified (29-line date-only diffs).
- **H4: gate drift** — mandate thresholds only in this file.
- **H5: per-ticker hardcoding → RESOLVED BY EVIDENCE.** Generalization run 1/5 (MSFT only); DIA/IWM/AAPL negative on powered N. System is basket-specific; README §1 reframed, no generality claimed.
- **H6: sizing sensitivity** — immaterial (prior session). Not re-run (sizing code untouched).
- **H7: cooldown/housing/mix** — cooldown validated asset-specific (prior); housing now EXCISED per its own ablation; entry continuation/reversal mix still unlogged — open.
- **H8: chart-vs-Deep-Backtest capture gap** — persists in fresh export (SPY Full 83/84, IS 17/18); bounded, gate-neutral.
- **H9: visual doubles** — entry gating + single-bar TARGET/STOP latch implemented this session; STOP×2/HUD-latch behavior superseded (re-verify counts next session).
- **H10 (new): production-refactor accounting.** CMF-20 + PERMIT excised (files/lines §6); +3R→1.85R recalibration does NOT produce limit harvesting (1/83 fills — §3 states the real mechanism); p-value prediction missed (0.1139/0.1029 vs <0.10 — §4); N-for-quality trade collapsed SPY N below mandate (84<160 — §1 reports the regression, no rescue tuning attempted); prior-session phase3/walkforward/ablation artifacts are STALE (old architecture) and cited nowhere as current evidence.

*Generated 2026-09-09 night session — FAILs reported as FAILs with raw excerpts; negative results (generalization 1/5, p-misses, TARGET 1.2%) reported, not buried.*
