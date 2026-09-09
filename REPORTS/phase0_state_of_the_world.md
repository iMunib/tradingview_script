# Phase 0 — State of the World (2026-09-09)

> Mandate restated verbatim (binding; restated in every future audit; do not let drift):
> - SPY 1D: profit factor ≥1.75, N≥160 trades with ≥95 wins, max drawdown ≤12%
> - QQQ 1D: profit factor ≥1.60, max drawdown ≤12%
> - Out-of-sample (2025–2026) degradation vs. in-sample (2018–2024): ≤20%, computed per-asset — not as a pooled substitute
> - Target instruments: BATS:SPY, BATS:QQQ, BITSTAMP:BTCUSD, 1D primary / 1W regime confirmation

## 0. Git state (evidence, not summary)

- `git log --oneline -20` top: `26f2b88 feat(quant): deliver UCS v3 ... -20.64% OOS outperformance` (2026-09-09 17:50 -0400). Parent chain: `0cfe809`, `f3d2d1c`, `0283d5a`, `f2ce0a7`.
- `HEAD (26f2b88)` is **1 ahead of `origin/main` (`0cfe809`)**. `git fetch origin` confirms no new remote commits; local commit unpushed.
- `git diff origin/main --stat`: 26 files, +15206/−1283. Bulk is `metrics/backtest_history.json` (+5400), `metrics/baseline_history_backup_20260907.json` (+6077), `metrics/all_assets_evaluation.json` (+411 changed), `FINAL_OPTIMIZED_STRATEGY.pine` (431 changed), `scripts/evaluate_all_assets.py` (634 changed), plus new diagnostic scripts (`diagnose_tasks_bc.py` +426, `test_matrix.py` +94, etc.).
- **Uncommitted (dirty working tree):** `M strategy_is.pine`, `M strategy_oos.pine`. Untracked: `.diag_tmp/`, `.openclaw/`, `baseline_pure.pine` (233 lines), `logs/` (15 eval logs), `strategy_full.pine` (341 lines), `test_strategy.pine` (268 lines).
- Critical inconsistency: the **committed** `strategy_is.pine`/`strategy_oos.pine` at `26f2b88` are the **old baseline** (`strategy("FINAL OPTIMIZED — Single RSI 14 ...", shorttitle="FINAL_BASELINE")`, 227 lines), while the working-tree versions are UCS v3 (341 lines, `FINAL_UCSv3`). `strategy_full.pine` was **never committed** (untracked). So the committed repo state is internally inconsistent: master = UCS v3, variants = stale baseline. The working-tree (uncommitted) variants are the correct UCS v3 derivatives (see §1). `metrics/all_assets_evaluation.json` (committed at 26f2b88) can only have come from runtime-regenerated variants (`generate_partitioned_files()` inside `evaluate_all_assets.py` rewrites the three files at sweep start), not from the committed stale files — this is plausible but means the committed JSON is not reproducible from the committed `.pine` files without re-running the generator.
- What `26f2b88` actually contains vs. what docs claim: docs claim "24-phase 17:44–17:49 UTC single-WS sweep". JSON contains exactly 24 asset×sample cells (6 Full + 6 Windowed + 6 IS + 6 OOS) + 6 degradation keys + `pooled_oos_summary` — count matches. But **no timestamp is stored per cell** (recs have symbol/interval/sample/net/PF/DD/WR/wins/N/sharpe only), so the 17:44–17:49 window is **unverifiable from the JSON**. `metrics/backtest_history.json` holds **741 rows** from many iterative runs (logs/ has 15 eval logs dated 2026-09-09), so "24-phase" describes one sweep among many same-day experiments, not a single clean run. Commit message headline ("-20.64% OOS outperformance") repeats the pooled metric that §3 shows is a mandate substitute (see §5).

## 1. Pine-file diffs (pairwise, verified — assumption CONFIRMED with a caveat)

- Line counts: `FINAL_OPTIMIZED_STRATEGY.pine` 348, `strategy_full.pine`/`strategy_is.pine`/`strategy_oos.pine` 341 each (working tree), `baseline_pure.pine` 233, `test_strategy.pine` 268.
- `diff master vs {full,is,oos}` (working tree): **exactly 29 diff lines each, confined to the date-filter block** — `useDateFilter` (`input.bool(false)` → hardcoded `true`) and `dateMode` default string, plus the `// GENERATE-IS-START … // GENERATE-IS-END` body:
  - full: `bool inTradeWindow = (time >= inSampleStart and time <= outSampleEnd)`
  - is: `bool inTradeWindow = (time >= inSampleStart and time <= inSampleEnd)`
  - oos: `bool inTradeWindow = (time >= outSampleStart and time <= outSampleEnd)`
  - vs. master: `bool inTradeWindow = true` + `if useDateFilter` / `dateMode` branching (lines 33–34, 46–55).
- So the prompt's assumption is **CONFIRMED for the working tree**: the three variants differ only in date filtering. **Caveat:** it is FALSE for the committed tree (variants stale, see §0). Generator `scripts/make_variants.py` (67 lines, regex on `useDateFilter`/`dateMode` + marker replacement) and the duplicate `generate_partitioned_files()` inside `scripts/evaluate_all_assets.py:178-211` both implement this correctly.
- Dead variants: `baseline_pure.pine` = old Single-RSI baseline; `test_strategy.pine` = "High-Volume Dual Swing Engine" experiment. Neither is referenced by the evaluator; both untracked. They must be retired or documented (Phase 4 TOOLING).

## 2. Number tracing: README / PERFORMANCE_AUDIT vs. `metrics/all_assets_evaluation.json`

All table cells below were checked key-by-key against the JSON. **All 24 primary cells trace exactly** (PF/N/DD/WR/net% match the named keys):

| Doc table | JSON keys | Trace |
|---|---|---|
| README §Full Chart History (6 rows) | `SPY_1D_Full`, `QQQ_1D_Full`, `BTCUSD_1D_Full`, `SPY_1W_Full`, `QQQ_1W_Full`, `BTCUSD_1W_Full` | exact (e.g. SPY PF 1.018, N 213, DD 20.66, WR 60.09) |
| README §Windowed 2018–2026 | `*_Full_2018_2026` (6 keys) | exact (SPY 0.987/65/10.15/64.62 … BTC W 8.021/12/1.63) |
| README §IS 2018–2024 | `*_IS` (6 keys) | exact (SPY 0.774/52/59.62 … BTC W 9.591/8/62.50) |
| README §OOS 2025–2026 | `*_OOS` (6 keys) | exact incl. `SPY_1W_OOS` PF `null` rendered as "inf" (N=2, 100% WR, no losers) |
| README §Degradation + Pooled | `*_degradation_pct` (6) + `pooled_oos_summary` (trade_weighted 1.825/2.308/−26.47; true pooled 1.308/1.578/−20.64) | exact (SPY W stored −1080.64, README truncates to −1080) |
| PERFORMANCE_AUDIT §§2–4 + Gates | same keys | exact; raw-text quotes (SPY OOS `+6,180.50USD+6.18% PF 2.854 84.62% 11/13 DD 3.46%`, QQQ OOS `+4,136.96…`, BTC W Full `+18,304.39…`) match `net_profit_raw`/`profit_factor`/`win_rate_pct`/`winning_trades`/`total_closed_trades`/`max_drawdown_pct` |

Degradation formula verified: `(PF_IS − PF_OOS)/PF_IS×100` reproduces stored values (SPY −268.73, QQQ −54.13, BTC 47.67).

### Unverifiable claims (no raw source value found — reported, not quietly fixed)

1. README §Degradation: "Trajectory: 48.94 → 42.96 → 38.17 → 2.55 → −20.64" — the four prefix values appear in **no key** of `all_assets_evaluation.json`. Possibly prior sweeps in `backtest_history.json` (741 rows, unchecked); untraced as stated.
2. README §3 Ablation table attributions — "QQQ OOS 1.854/77.78%", "BTC W 6.915/17; early entries vs RSI lag", "SPY windowed WR 64.62%; STRONG BUY tier", "OOS daily double while Fed gate dormant", "SPY N 360→213", "SPY Full WR 60.09% (best Full WR yet)". The *levels* (6.915, 64.62%, 60.09%) trace to JSON cells, but the **causal attributions** (which indicator caused them) have no source: **`metrics/indicator_ablation_results.csv` does not exist**; no leave-one-out run was ever recorded.
3. PERFORMANCE_AUDIT §5: "SPY 360→213", "BTC N 229→91", "DD 49.62→14.83" — the 360/229/49.62 baselines are in no JSON key (presumably pre-UCSv3 sweeps; untraced).
4. Sweep provenance: "17:44–17:49 UTC … single WS" — no per-cell timestamp; unverifiable from JSON (§0).
5. Gates thresholds: "SPY N 180–230", "SPY PF≥1.70", "BTC N 60–100 / DD≤14", "QQQ OOS≥1.60 + WR 65–75", "BTC W ≥10/≥3" — none of these ranges appear in the mandate; the SPY PF gate (1.70) is 0.05 below the mandate (1.75). These are invented gates, not traced thresholds.
6. `SPY_1W_degradation_pct = −1080.64` is computed against an **arbitrary capped PF=10.0** for the `null`-PF (N=2, no-loss) OOS cell (`evaluate_all_assets.py:587-591,601-609`). The cap value 10.0 appears nowhere in the docs; the −1080% figure is an artifact of that cap, not a measurement.
7. `true_pooled ΣGP/ΣGL` (1.308→1.578): GP/GL are **algebraically reconstructed** from `net_profit_pct` + PF (`evaluate_all_assets.py:572-599`), not summed from trade logs. No `metrics/trade_log_*.csv` exists, so the reconstruction is unverifiable against actual trade P&L.

## 3. Mandate verdict on current numbers (original thresholds only)

| Gate (mandate) | Actual (JSON key) | Verdict |
|---|---|---|
| SPY 1D PF ≥1.75 | 1.018 (`SPY_1D_Full`) | **FAIL** (−0.732) |
| SPY 1D N ≥160 | 213 (`SPY_1D_Full`) | PASS |
| SPY 1D wins ≥95 | 128 (`SPY_1D_Full`) | PASS |
| SPY 1D DD ≤12% | 20.66% (`SPY_1D_Full`) | **FAIL** (+8.66pp) |
| QQQ 1D PF ≥1.60 | 1.017 (`QQQ_1D_Full`) | **FAIL** |
| QQQ 1D DD ≤12% | 15.49% (`QQQ_1D_Full`) | **FAIL** |
| Per-asset degradation ≤20%: SPY 1D | −268.73% | PASS (OOS better; but OOS N=13, low-N — see §5) |
| Per-asset degradation ≤20%: QQQ 1D | −54.13% | PASS (OOS N=18, low-N) |
| Per-asset degradation ≤20%: BTC 1D | +47.67% | **FAIL** |
| Weekly (regime confirmation, mandate silent on thresholds) | SPY W PF 1.791/N39, QQQ W 1.599/N55, BTC W 6.915/N17 — all OOS cells N≤4 | indicative only |

**Headline:** on the binding per-asset mandate the strategy **FAILS 4 of 6 Full-history gates and 1 of 3 degradation gates**. The docs' "Pooled PASS (−20.64%)" banner is a substituted metric that appears nowhere in the mandate and reverses the verdict over failing cells — the second manufactured-pass pattern named in the session brief. It must not be repeated.

## 4. Strengths inventory (confirmed — must not regress)

- **S1. No-repaint execution model.** `process_orders_on_close=true, calc_on_every_tick=false` (line 6); all 4 `request.security()` calls (lines 125, 127, 128, 132) use `lookahead=barmerge.lookahead_off` with `[1]` offsets (`ta.ema(close,200)[1]`, `close[1]`, `ta.sma(permits,12)[1]`). Count: `lookahead_off` ×4, `request.security` ×4. Pre-commit guard required (Phase 1e).
- **S2. Entry-side tiering.** `isStrongBuy`/`isBuy` (lines 255–256) are mutually exclusive (`isBuy = longEntry and not isStrongBuy`), gated off one rising edge (`longEntry = longSetup and not longSetup[1]`, line 252). No double-fire. Extend this pattern to exits (Phase 1b), don't replace it.
- **S3. Staged R-multiple ratchet.** Lines 293–306: 0.90R→+0.05R lock, 1.60R→+0.80R, 2.40R→+1.65R, each re-issuing `strategy.exit("Bracket Exit", … stop=…, limit=…)`. Legitimate partial-lock structure; keep while fixing taxonomy/sizing.
- **S4. Hysteresis cooldown concept.** `lastExitBar`/`cooldownPassed` (lines 246–249): 3-bar daily / 2-bar weekly post-exit freeze inside `longSetup` (line 251) + HUD COOLDOWN state (lines 343–345). Right mechanism for churn; parameter (3/2) unvalidated — Phase 1c must sweep, not discard.

## 5. Weaknesses inventory (each maps to a Phase 1 fix or a new finding)

- **W1 (→1a). Per-ticker hardcoded branching — CONFIRMED.** `isSPY`/`isQQQ`/`isCrypto` (61–63) drive `pLeft/pRight/gapMin/gapMax` (67–70), `spyReversal`/`qqqBreakout`/`qqqReversal`/`btcReversal`/`fallbackReversal` (229–236) and `reversalSetup` (238). This is three asset-specific sub-strategies sharing a risk engine, currently presented as one generalized edge. Docs must either reframe or prove generalization on 10+ untuned tickers.
- **W2 (→1b). Exit taxonomy collapsed — CONFIRMED.** Four mechanisms (bracket stop, bracket limit, `isStrongExit` L257, Peak `confluenceBearFresh or fishExitBear` L309–310) render as two shapes; `isStandardExit` (L258) is a next-bar post-hoc flag (`position[1]>0 and position==0`), so `exitPlot` (L320) unions a same-bar trigger with a next-bar echo — one exit can paint **two triangles on consecutive bars**, the reported "overlap" symptom. All four `strategy.exit()` calls (L291/298/302/306) share the name `"Bracket Exit"` with **no `comment_profit`/`comment_loss`**, so stop-hits vs target-hits are indistinguishable in the trade list. HUD `EXIT / TP HIT` (L341) conflates them. `Window End` close (L311–312) injects a backtest-artifact exit into IS/OOS edge trades.
- **W3 (→1c). Cooldown unvalidated — CONFIRMED.** 3/2-bar freeze has no supporting distribution; **no trade log exists** (`metrics/trade_log_*.csv` absent), so bars-between-entries cannot be computed today. Phase 2 log export is a prerequisite, then sweep 3/5/8/13.
- **W4 (→1d). Compounding sizing undisclosed — CONFIRMED.** `riskAmount = strategy.equity × riskPerTrade/100` (L270) compounds across multi-year runs; no fixed-fractional-of-initial-capital cross-check has been run or disclosed. With SPY Full net only +1.59% over full history (~213 trades), sizing assumptions dominate the economics.
- **W5 (→1e). No repaint guard in tooling — CONFIRMED absent.** S1 holds in code but no pre-commit check exists; `evaluate_all_assets.py`/`make_variants.py` do not assert it.
- **W6 (NEW). All OOS cells are low-N; pooled headline is 100% low-N.** OOS N = 13/18/9/2/3/4 (all <30); weekly IS mostly <30; BTC W Full N=17 <30 yet gated PASS. Per Phase 2 rule every OOS cell must be labeled "low-N, indicative only" and excluded from pooled headlines. The "Elite Daily Double" (SPY 84.62% on N=13, QQQ 77.78% on N=18) is statistically fragile.
- **W7 (NEW). `null`-PF cap fabricates SPY W degradation.** `SPY_1W_OOS` PF is `null` (2/2 winners); script substitutes 10.0 then reports −1080.64% degradation and folds the capped 10.0 into the trade-weighted pooled PF (2.308). Arbitrary constant, undisclosed in docs.
- **W8 (NEW). Housing filter is effectively dormant.** `macroGate = … and (isCrypto or na(permits) or permitsSlope >= −50.0)` (L135): PERMIT-level units (~10³) vs threshold −50 makes the gate pass-always except in crashes; crypto bypasses it entirely (`isCrypto or …`). Yet README credits PERMIT with "6–9mo lead / OOS daily double". Contribution unproven; ablation must test removal.
- **W9 (NEW). Full-vs-Windowed contradicts the "pre-2018 drag" story.** SPY Full PF 1.018 > Windowed 0.987 — including pre-2018 data *helped* SPY PF. Docs (§5.2) claim the opposite. QQQ Full 1.017 < Windowed 1.391 does show drag, so the effect is asset-specific and the blanket explanation is wrong.
- **W10 (NEW). `isStrongExit` plot lacks `barstate.isconfirmed` while its trigger has it** (L257 vs L307/L320); `isStandardExit` fires a bar late by construction. Visualization lags reality by one bar on every bracket/peak exit — misleading on live charts even though the order engine (calc_on_every_tick=false) does not repaint.
- **W11 (NEW). Continuation vs reversal mix unknown.** `continuationTrigger` (42–60 RSI pullback, L240–243) vs `reversalSetup` (L238) proportions, and Strong/Peak/Bracket/Window exit shares, are unreported — the trade log must carry exit-reason taxonomy or no ablation/cooldown claim is attributable.
- **W12 (NEW). Economics.** SPY Full +1.59% / QQQ +1.33% total (not annualized) over full chart history with 213/241 trades at 0.05% commission + 1-tick slippage: gross edge ≈ noise. BTC Full −2.69% (PF 0.936). No cost-sensitivity or slippage-sweep disclosed.

## 6. Fixed candidate indicator list (frozen before any ablation — Phase 3 anti-stopping-rule lock)

Existing (10): RSI-14 · MACD-histogram (12,26,9) · Fisher Transform 9-period · Dual %R (21/112) · MFI-14 · OBV/EMA-20 · CMF-20 · buy/sell volume percent · Weekly 200 EMA (+M21/M12 monthly fallbacks) · FRED housing permits (PERMIT slope).
Candidates (4): ADX/DMI trend-strength gate · ATR-percentile volatility regime filter · VWAP deviation · realized-volatility regime switch.
Rule: ablate exactly this list, leave-one-out through the Phase 2 walk-forward protocol, one row per indicator×asset×window in `metrics/indicator_ablation_results.csv` (columns: indicator,included,asset,window,PF,WR_pct,N,MaxDD_pct,degradation_pct). No mid-sweep additions. Bonferroni/BH correction for any "significant" claim, else label exploratory.

## 7. Tooling actually invoked this session (Phase 4 TOOLING seed)

- Active: `git log/diff/fetch/status`, file reads, `scripts/make_variants.py` (read only), `scripts/evaluate_all_assets.py` (read only), `metrics/all_assets_evaluation.json` (read), local Python for arithmetic/diffs. No browser/CDP run yet; no Pine edit yet.
- Retired/pending: `baseline_pure.pine`, `test_strategy.pine` (dead variants — retire); `.diag_tmp/`, `.openclaw/`, `__pycache__/` (noise).

## 8. What Phase 1+ must do (traceability)

1a reframe-or-prove-generalization (W1) · 1b exit taxonomy + comment_profit/loss + Window-shape suppression + HUD reasons (W2/W10) · 1c cooldown distribution + 3/5/8/13 sweep once trade logs exist (W3/W11) · 1d fixed-capital sizing cross-check (W4/W12) · 1e lookahead_off pre-commit guard (W5/S1) · Honesty Log + per-asset gates + low-N labels + capped-PF disclosure (W6/W7) · PERMIT ablation (W8) · correct pre-2018-drag claim (W9).
