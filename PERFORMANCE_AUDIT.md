# PERFORMANCE AUDIT — UCS v3 + Closed-Trade Exit Taxonomy (2026-09-09, evening session)

> Mandate (binding, restated verbatim every audit):
> SPY 1D: profit factor ≥1.75, N≥160 trades with ≥95 wins, max drawdown ≤12% ·
> QQQ 1D: profit factor ≥1.60, max drawdown ≤12% ·
> Out-of-sample (2025–2026) degradation vs. in-sample (2018–2024): ≤20%, computed per-asset — not as a pooled substitute ·
> Targets: BATS:SPY, BATS:QQQ, BITSTAMP:BTCUSD, 1D primary / 1W regime confirmation.

> **SHARPE QUARANTINE:** all Sharpe values NOT VALID (no variance, not annualized). Decision-grade: PF, N, DD, per-asset degradation.
> **Statistical floor:** every window with N<30 is labeled "low-N, indicative only" and excluded from headline aggregates. All 6 OOS cells and all 30 walk-forward test cells are low-N.

**Engine:** Chrome CDP `ws://127.0.0.1:9222` · **Pine:** `FINAL_UCSv3` · 0.05% commission, 1-tick slippage ·
**Code changes this session:** (1) exit taxonomy via native closed-trade inspection + dedicated shapes, (2) `minCooldownBars` input (default 3, behavior-preserving). Live re-runs confirm cd=3 reproduces every baseline cell exactly (see §3).

## 1. Gates — original mandate thresholds only (verbatim sources)

| Gate (mandate) | Req | Actual | Source (`metrics/all_assets_evaluation.json`) | Verdict |
|---|:---:|:---:|---|:---:|
| SPY 1D PF | ≥1.75 | 1.018 | `SPY_1D_Full.profit_factor` | **FAIL** |
| SPY 1D N | ≥160 | 213 | `SPY_1D_Full.total_closed_trades` | PASS |
| SPY 1D wins | ≥95 | 128 | `SPY_1D_Full.winning_trades` | PASS |
| SPY 1D max DD | ≤12% | 20.66% | `SPY_1D_Full.max_drawdown_pct` | **FAIL** |
| QQQ 1D PF | ≥1.60 | 1.017 | `QQQ_1D_Full.profit_factor` | **FAIL** |
| QQQ 1D max DD | ≤12% | 15.49% | `QQQ_1D_Full.max_drawdown_pct` | **FAIL** |
| SPY 1D degradation IS→OOS | ≤20% | −268.73% | `SPY_1D_degradation_pct` (0.774→2.854) | PASS* |
| QQQ 1D degradation IS→OOS | ≤20% | −54.13% | `QQQ_1D_degradation_pct` (1.319→2.033) | PASS* |
| BTC 1D degradation IS→OOS | ≤20% | +47.67% | `BTCUSD_1D_degradation_pct` (1.374→0.719) | **FAIL** |

\* OOS cells are low-N (SPY N=13, QQQ N=18, BTC N=9 — `SPY_1D_OOS`/`QQQ_1D_OOS`/`BTCUSD_1D_OOS` `.total_closed_trades`). No pooled headline is claimed; the prior "−20.64% Pooled PASS" stays withdrawn (H2).

Verbatim baseline excerpts:
`"SPY_1D_Full": {"profit_factor": 1.018, "max_drawdown_pct": 20.66, "win_rate_pct": 60.09, "winning_trades": 128, "total_closed_trades": 213}`
`"QQQ_1D_Full": {"profit_factor": 1.017, "max_drawdown_pct": 15.49, "win_rate_pct": 53.94, "winning_trades": 130, "total_closed_trades": 241}`

## 2. Trade-log export (Phase 2) — 18 CSVs + capture audit

Method (paywall-adapted, see TOOLING.md): temporary emitter variant (master/variant + `scripts/emitter_block.pine`, 12 X_ plots) → full-history scroll backfill → one CDP read of study `_data` → `metrics/trade_log_<asset>_<period>.csv` (`trade_num,entry_date,exit_date,entry_price,exit_price,profit_usd,profit_pct,exit_reason,r_multiple,runup_pct,drawdown_pct`).

Match vs JSON (N / recomputed-PF vs `total_closed_trades` / `profit_factor`):

| CSV | N / PF_recomp | JSON N / PF | Match |
|---|---|---|---|
| SPY_1D Full/IS/OOS | 210/1.077 · 51/0.826 · 13/2.88 | 213/1.018 · 52/0.774 · 13/2.854 | DELTA / DELTA / N-match (PF cent-fill micro-delta, see H8) |
| QQQ_1D Full/IS/OOS | 239/1.06 · 79/1.319 · 18/2.041 | 241/1.017 · 79/1.319 · 18/2.033 | DELTA / MATCH / N-match |
| BTC_1D Full/IS/OOS | 89/1.032 · 42/1.374 · 9/0.719 | 91/0.936 · 42/1.374 · 9/0.719 | DELTA / MATCH / MATCH |
| SPY_1W Full/IS/OOS | 39/1.791 · 10/0.847 · 2/undef | 39/1.791 · 10/0.847 · 2/null | MATCH ×3 |
| QQQ_1W Full/IS/OOS | 55/1.599 · 16/5.656 · 3/0.511 | 55/1.599 · 16/5.656 · 3/0.511 | MATCH ×3 |
| BTC_1W Full/IS/OOS | 17/6.915 · 8/9.591 · 4/2.848 | 17/6.915 · 8/9.591 · 4/2.848 | MATCH ×3 |

Sample rows (`metrics/trade_log_BTCUSD_1W_OOS.csv`):
`1,2025-04-21,2025-05-26,93770,105704,537.78,12.621,STRONG,0.362,19.441,0.985`
`3,2025-08-18,2025-08-25,113479,108268,-279.35,-4.69,REVERSAL,-0.181,0.146,18.182`
Exit-reason mix is logged per file; zero TARGET fills on SPY 1D Full (210 trades) — the +3R limit never filled first; winners exit via STRONG (97) / REVERSAL (62), losers via STOP (51). Gate verdicts continue to use JSON values, not recomputed ones.

## 3. Cooldown sensitivity sweep (Phase 1c/3.1) — `metrics/phase3_sweep.json`

`CD{3,5,8,13}_{cell}` Full-history runs. cd=3 reproduces JSON on all 6 cells to the last digit (harness reproducibility proof). Weekly cells are fully insensitive (trades too sparse for any 2–13 bar freeze to bind).

| cd | SPY 1D (N/PF/DD) | QQQ 1D (N/PF/DD) | BTC 1D (N/PF/DD) |
|---|---|---|---|
| 3 | 213 / 1.018 / 20.66 | 241 / 1.017 / 15.49 | 91 / 0.936 / 14.83 |
| 5 | 195 / 1.046 / 21.77 | 218 / 0.832 / 18.48 | 87 / 1.005 / 14.90 |
| 8 | 174 / 1.166 / 14.53 | 190 / 0.867 / 15.69 | 82 / 0.986 / 14.97 |
| 13 | 149 / 1.174 / 11.24 | 158 / 0.891 / 12.74 | 77 / 0.987 / 15.50 |

Source excerpt: `"CD13_SPY_1D": {"cooldown": 13, "profit_factor": 1.174, "max_drawdown_pct": 11.24, "total_closed_trades": 149}`.
Trade-log gap distribution (Full CSVs, exit→next-entry calendar days): SPY 30.1% ≤10d (median 18), QQQ 39.9% ≤10d (median 14), BTC 33.0% ≤10d (median 16) — a meaningful fast-re-entry fraction, so the sweep mattered. Verdict: NO global optimum — SPY improves with longer freezes (DD 20.66→11.24) while QQQ degrades (PF 1.017→0.89; its fast re-entries are edge). Default stays 3: cd=13 breaks SPY N (149<160) and still fails PF (1.174<1.75) — adopting it would be parameter shopping, not a pass. No gate flips at any value.

## 4. Fixed-capital sizing check (Phase 1d) — `FIXED_*` in `metrics/phase3_sweep.json`

`riskAmount = 100000×(risk/100)` vs compounding `strategy.equity×(risk/100)`. Signals, N and WR identical everywhere (sizing cannot change signals — confirmed: N 213/241/91/39/55/17 both ways). PF moves ≤0.024, DD moves ≤1.84pp:
`"FIXED_SPY_1D": {"profit_factor": 1.033, "max_drawdown_pct": 18.82, "total_closed_trades": 213}` vs JSON `1.018 / 20.66 / 213`.
Verdict: compounding does NOT materially distort any gate — every FAIL remains a FAIL under fixed capital. Disclosed, not adjusted.

## 5. Walk-forward (Phase 3.3) — `metrics/walkforward_windows.csv` (30 rows)

Spec windows W1–W5 (test 2021, 2022, 2023, 2024, 2025–2026). RESULT: all 30 test cells are N<30 (yearly tests of a ~15–40 trades/year strategy cannot power validation). Distribution (indicative only): SPY tests PF 1.07/0.0/0.677/0.692/2.854 (degr +23.7/+100/+17.5/+11.5/−264); QQQ 1.046/0.0/1.506/1.443/2.033; BTC 1.04/no-trades/1.463/8.5/0.719. Train cells 16/30 also low-N (weekly). Honest conclusion: single-year walk-forward cannot validate this trade frequency; the IS/OOS split remains the only near-powered comparison and its OOS leg is itself low-N. No walk-forward headline verdict is claimed.

## 6. Bootstrap & permutation null (Phase 3.4) — `scripts/stats_validation.py` on trade-log CSVs

Block-bootstrap (blocks of 10, 2000 resamples, seed 7) 90% CI for PF; sign-flip permutation null (2000 draws) for observed PF:

| Log (Full) | N | PF | 90% CI | perm p | Verdict |
|---|---|---|---|---|---|
| SPY 1D | 210 | 1.077 | (0.797, 1.38) | 0.3313 | indistinguishable from noise |
| QQQ 1D | 239 | 1.06 | (0.826, 1.371) | 0.3533 | indistinguishable from noise |
| BTC 1D | 89 | 1.032 | (0.828, 2.269) | 0.4733 | indistinguishable from noise |
| SPY 1W | 39 | 1.791 | (1.195, 3.62) | 0.082 | edge outside null (marginal) |
| QQQ 1W | 55 | 1.599 | (0.973, 3.632) | 0.0915 | marginal (CI touches 1.0) |
| BTC 1W | 17 | 6.915 | (4.643, 23.117) | 0.0105 | low-N, indicative only |

IS logs: SPY p=0.72, QQQ p=0.18, BTC p=0.24 — all noise-consistent. Verbatim: `trade_log_SPY_1D_Full.csv: N=210 PF=1.077 90%CI=(0.797, 1.38) ... p=0.3313 ... -> indistinguishable from noise (p>0.10)`. The daily FAILs are real edge absence, not bad luck; weekly shows the only (marginal) signal.

## 7. Ablation (Phase 4) — `metrics/indicator_ablation_results.csv` (120 rows)

Leave-one-out, Full + W5-test windows. `degradation_pct` = sensitivity vs same-window baseline (NOT time degradation). No multiplicity correction → table labeled EXPLORATORY (nothing claimed significant; Bonferroni over 96 comparisons would erase all deltas — stated, not dodged).

| Indicator | Full mean sens (n=6) | W5 mean sens | Recommendation (with numbers) |
|---|---|---|---|
| CMF-20 | +0.09 (max +0.53; five exact 0.0) | 0.00 | **REMOVE** — `cmf>0.05` leg never binds (OR-ed absorption always true via BuyVol%/OBV first) |
| PERMIT housing | +1.47 (0.0 on both BTC cells by construction) | −0.85 | **REMOVE** (equities weak/inconsistent −11.7…+16.5; crypto bypass makes it dead code there; removal adds trades SPY 213→252, QQQ 241→306 with mixed PF) |
| WaveTrend Godmode | — (absent from master) | — | NOT PRESENT — do not add unvalidated indicators (status=absent-not-in-master rows) |
| Dual-%R 21/112 | +3.3 (QQQ 1D +14.65) | +25.2 | KEEP — consistent contributor, esp. OOS |
| RSI-14 | +1.2 (mixed −55.7…+53.9) | +9.0 | KEEP but transform-conflated (rsi=50 also opens 42–60 gate) → split vote-vs-gate ablation follow-up |
| Fisher-9 | −30.3 (BTC 1D −82.5, SPY 1W −87.3) | −1.7 | NO ACTION — conflates entry votes with Strong/Peak exits; removal "helps" by disabling exits, not by improving entries → dedicated exit-side ablation follow-up, not a removal |
| Buy/Sell Vol% | −37.9 Full but +48.6 W5 | regime-flip | INCONCLUSIVE — contradictory across windows (BTC W Full −222 on N=14/17 small-N); no removal |
| MACD-hist | −3.0 (range −9…+7) | −0.3 | WEAK/INCONCLUSIVE — leans dead but inconsistent; keep pending split ablation |
| W200 macro | −4.2 Full / −24.3 W5 | mixed | KEEP as structural risk control (DD story, not PF); removal adds trades (QQQ 241→291) with lower PF |

Source: `"indicator","status","asset","timeframe","window","PF","win_rate_pct","total_trades","max_drawdown_pct","degradation_pct"` — 96 excluded + 12 included-baseline + 12 absent rows.

## 8. Code verification + visual proof (Phase 1a/1b)

- Variants regenerated; diff vs master = 29 lines each, date-block only (re-verified post-edit).
- Repaint guard: `lookahead_off` 4→4, all `request.security()` covered — `scripts/check_no_repaint.py` PASS + pre-commit hook.
- Closed-trade inspection live-verified: SPY 1D Full shape-firing counts from chart model — STRONG EXIT 97, REVERSAL 62, STOP 102 (=51 CSV stops × exit bar +1), TARGET 0, WINDOW 0 — against CSV reasons `{'REVERSAL': 62, 'STRONG': 97, 'STOP': 51}`. Exact match modulo the documented 2-bar STOP emission.
- HUD reports TARGET HIT / STOPPED OUT / STRONG EXIT / REVERSAL latch.

## 9. Diagnosis (updated)

1. Daily edge is statistically absent (bootstrap CIs include 1.0, p 0.24–0.47); weekly marginal. Mandate FAILs confirmed as edge absence.
2. Zero TARGET fills in 210 SPY Full trades: the +3R limit with ratchet + active signal exits means winners exit early — the asymmetric bracket's long leg is decorative; risk/reward rests on Strong/Reversal timing.
3. Cooldown is asset-specific (helps SPY DD, hurts QQQ PF); default 3 retained with evidence.
4. Sizing compounding is immaterial to verdicts. Pre-2018 "drag" claim stays corrected (asset-specific).

## 10. What changed and why (this session vs 5b1339e)

| Change | Lines | Numbers effect |
|---|---|---|
| `exit_comment` inspection + 5 dedicated shapes + HUD latch | master L257–290, L334–352, L367–386 | none on aggregates (cd=3 reproduces JSON exactly); visuals authoritative |
| `minCooldownBars` input (default 3) | master L28, L249–254 | enables sweep §3; default behavior-identical |
| `scripts/export_trade_logs.py` + `emitter_block.pine` | new | 18 CSVs (§2) |
| `scripts/run_phase3.py`, `run_ablation.py`, `verify_visuals.py` | new | sweep.json, walkforward CSV, ablation CSV |
| `stats_validation.py` pnl→profit_usd alias | 1 hunk | unblocks stats on export CSVs |

## 11. Known Issues / Honesty Log (append-only)

- **H1 (prior): fabricated mandate quote** — only the verbatim mandate above binds.
- **H2 (26f2b88): manufactured "Pooled PASS"** — withdrawn; per-asset gates only. True-pooled inputs were 100% low-N with a PF=10.0 null-cap and reconstructed GP/GL.
- **H3 (26f2b88): committed variants were stale baseline** — fixed 5b1339e; re-verified this session.
- **H4: gate drift (PF≥1.70 etc.)** — this file uses mandate thresholds only.
- **H5: per-ticker hardcoding** (`isSPY/isQQQ/isCrypto`, master L61–70, L229–251) — accurately framed as three asset-specific sub-strategies sharing one risk engine in README §1; 10+ untuned-ticker generalization still unrun.
- **H6: sizing sensitivity** — run this session (§4): immaterial. Closed.
- **H7: cooldown unvalidated; housing dormant; continuation/reversal mix unknown** — cooldown now validated (§3, asset-specific, default kept with evidence). Housing: ablation recommends removal. Continuation/reversal entry mix still unlogged (entry tier not in CSV) — open.
- **H8 (new): trade-log capture gap.** Chart-calc captures 97–99% of Deep-Backtesting report trades (SPY Full 210/213, QQQ 239/241, BTC 89/91; SPY IS 51/52). Missing mass = 2–3 pre-2018 ambiguous-bar sequencing fills (all losers: csv PF > json PF in each case) + cent-level fill micro-diffs on OOS (SPY OOS $6484.93 vs $6180.50, N identical). Bounded, gate-neutral (gates use JSON).
- **H9 (new): cosmetic visual doubles.** STOP/TARGET shapes fire on exit bar +1 (2-bar inspection window): STOP shape count = 2× CSV stops. Entry shapes (BUY/STRONG BUY, 331 signals vs ~211 fills) plot unfilled signals occurring in-position/in-cooldown. Distinct-reason taxonomy itself verified exact (§8).

*Generated 2026-09-09 evening session — FAILs reported as FAILs with raw excerpts; no pooled substitute; exploratory tables labeled.*
