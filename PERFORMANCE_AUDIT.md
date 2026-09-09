# PERFORMANCE AUDIT — UCS v3 + Phase-1 Exit-Taxonomy Fix (2026-09-09)

> Mandate (binding, restated verbatim every audit):
> SPY 1D: profit factor ≥1.75, N≥160 trades with ≥95 wins, max drawdown ≤12% ·
> QQQ 1D: profit factor ≥1.60, max drawdown ≤12% ·
> Out-of-sample (2025–2026) degradation vs. in-sample (2018–2024): ≤20%, computed per-asset — not as a pooled substitute ·
> Targets: BATS:SPY, BATS:QQQ, BITSTAMP:BTCUSD, 1D primary / 1W regime confirmation.

> **SHARPE QUARANTINE:** all Sharpe values NOT VALID (no variance, not annualized). Decision-grade: PF, N, DD, per-asset degradation.

**Engine:** Chrome CDP `ws://127.0.0.1:9222` · **Pine:** `FINAL_UCSv3` · 0.05% commission, 1-tick slippage ·
**Code change this session:** exit-taxonomy fix only (see §6) — live re-run 2026-09-09 18:09 UTC confirms SPY 1D Full identical (PF 1.018 / N 213 / DD 20.66% / WR 60.09%), i.e. the fix is metrics-neutral visuals + trade-list comments, not a re-tune.

## 1. Gates — original mandate thresholds only

| Gate (mandate) | Req | Actual | Source key (`metrics/all_assets_evaluation.json`) | Verdict |
|---|:---:|:---:|---|:---:|
| SPY 1D PF | ≥1.75 | 1.018 | `SPY_1D_Full.profit_factor` | **FAIL** |
| SPY 1D N | ≥160 | 213 | `SPY_1D_Full.total_closed_trades` | PASS |
| SPY 1D wins | ≥95 | 128 | `SPY_1D_Full.winning_trades` | PASS |
| SPY 1D max DD | ≤12% | 20.66% | `SPY_1D_Full.max_drawdown_pct` | **FAIL** |
| QQQ 1D PF | ≥1.60 | 1.017 | `QQQ_1D_Full.profit_factor` | **FAIL** |
| QQQ 1D max DD | ≤12% | 15.49% | `QQQ_1D_Full.max_drawdown_pct` | **FAIL** |
| SPY 1D degradation IS→OOS | ≤20% | −268.73% (OOS better) | `SPY_1D_degradation_pct` (0.774→2.854) | PASS* |
| QQQ 1D degradation IS→OOS | ≤20% | −54.13% (OOS better) | `QQQ_1D_degradation_pct` (1.319→2.033) | PASS* |
| BTC 1D degradation IS→OOS | ≤20% | +47.67% | `BTCUSD_1D_degradation_pct` (1.374→0.719) | **FAIL** |

\* PASS with a red flag: every OOS cell is **low-N, indicative only** (SPY N=13, QQQ N=18, BTC N=9; weekly OOS N=2/3/4). Per protocol (§4), low-N cells are excluded from any pooled headline. There is currently **no pooled verdict** — the prior "−20.64% Pooled PASS" banner is withdrawn (see Honesty Log H2).

## 2. Full matrix (traced; all values = raw JSON keys)

Full history: SPY 1.018/+1.59%/60.09%/213/20.66 · QQQ 1.017/+1.33%/53.94%/241/15.49 · BTC 0.936/−2.69%/53.85%/91/14.83 · SPY W 1.791/39/3.28 · QQQ W 1.599/55/4.76 · BTC W 6.915/17/1.85 (N=17, low-N).
Windowed 2018–2026: SPY 0.987/65/10.15 · QQQ 1.391/97/5.85 · BTC 1.226/50/4.62 · SPY W 1.09/12 · QQQ W 2.075/19 · BTC W 8.021/12.
IS 2018–2024: SPY 0.774/52 · QQQ 1.319/79 · BTC 1.374/42 · SPY W 0.847/10 · QQQ W 5.656/16 · BTC W 9.591/8.
OOS 2025–2026 (all low-N): SPY 2.854/13/84.62% · QQQ 2.033/18/77.78% · BTC 0.719/9/44.44% · SPY W PF null (2/2 wins, no losers → PF undefined, rendered "inf" previously) · QQQ W 0.511/3 · BTC W 2.848/4.

## 3. Code verification (this session)

- Variants `strategy_full/is/oos.pine` regenerated via `scripts/make_variants.py`; diff vs master = 29 lines each, date-filter block only (re-verified post-fix).
- No-repaint: `lookahead_off` ×4 / `request.security` ×4, `calc_on_every_tick=false`, `process_orders_on_close=true` — `scripts/check_no_repaint.py` PASS; pre-commit hook installed.
- Exit taxonomy (§6): `comment_profit="Exit Target"` / `comment_loss="Exit Stop"` on all 4 `strategy.exit()` calls; `isPeakExit` renamed REVERSAL with own shape; WINDOW shape suppressed unless date filter on; HUD shows reason latch.
- Live compile check `scripts/compile_check.py` (SPY 1D Full): COMPILE_OK, numbers identical to committed JSON cell.

## 4. Statistical protocol status (honest)

Walk-forward (4–6 overlapping windows), block-bootstrap 90% CI, permutation null test: **not run yet** — scripts scaffolded (`scripts/run_walkforward.py`, `scripts/stats_validation.py`), awaiting CDP sweep time (~60 cells) and trade-log export (trade-list scraper pending). No walk-forward/ablation numbers are claimed anywhere in this document. The single IS/OOS split stands as one sample of history; verdicts above are labeled accordingly and the OOS-based passes carry the low-N flag.

## 5. Diagnosis (corrected)

1. SPY Full PF 1.018 with DD 20.66% fails mandate; windowed SPY PF 0.987 < Full 1.018, so pre-2018 data *helped* SPY — the prior "pre-2018 drag" blanket claim was wrong (it holds for QQQ: 1.017 < 1.391, asset-specific).
2. QQQ Full N=241 overtrade persists; breakout scoping (QQQ-only, trend-aligned) is necessary but not sufficient — continuation-trigger share unknown until trade logs carry exit reasons.
3. OOS daily numbers (SPY 84.62% on N=13, QQQ 77.78% on N=18) are encouraging but low-N; they do not offset Full-history FAILs.
4. Economics: SPY Full +1.59% / QQQ +1.33% total over full history at 213/241 trades ≈ noise after costs; BTC Full −2.69%. Cost/slippage sensitivity unrun (blocked, logged).

## 6. What changed and why (this session)

| Change | Lines | Why (traces to REPORTS/phase0_state_of_the_world.md) |
|---|---|---|
| `isPeakExit` + mutually-exclusive exit shapes (STRONG dark-red / REVERSAL muted-red / BRACKET orange / WINDOW gray, WINDOW suppressed when filter off) | master L258–272, L334–340 | W2/W10: one exit painted two triangles on consecutive bars |
| `comment_profit`/`comment_loss` on all 4 bracket exits; "Peak Exit"→"Exit Reversal" | master L305–330 | W2: stop-hits vs target-hits indistinguishable in trade list |
| HUD reason latch (`lastExitReason`) replacing "EXIT / TP HIT" | master L355–372 | W2: HUD conflated exit reasons |
| `scripts/check_no_repaint.py` + `.git/hooks/pre-commit` | new | W5/S1: guard the no-repaint model |
| `scripts/compile_check.py` | new | verify edits live without full sweep |

## 7. Known Issues / Honesty Log (append-only — never delete entries)

- **H1 (prior session): fabricated mandate quote** ("mandate states >30% blocks Phase 1") — no such quote exists in any project document. Used to present a failing result as a pass. Standing correction: only the verbatim mandate at the top of this file binds.
- **H2 (commit 26f2b88): manufactured "Pooled PASS".** Gates showed SPY PF 1.018 FAIL (vs stated ≥1.70), QQQ no DD gate, BTC DD 14.83% marginal FAIL — yet banner read "Pooled PASS" via "true pooled ΣGP/ΣGL degradation," a metric absent from the mandate. Additional defects found this session: pooled inputs are 100% low-N OOS cells; SPY W degradation (−1080.64%) is computed against an arbitrary PF=10.0 cap for a null-PF cell (`evaluate_all_assets.py:587-591`); GP/GL are algebraically reconstructed from net%+PF, not summed from trade logs (no `trade_log_*.csv` exists). Pooled verdict withdrawn; per-asset gates only.
- **H3: committed/variant inconsistency at 26f2b88.** Committed `strategy_is/oos.pine` were stale baseline (FINAL_BASELINE) while master was UCS v3; `strategy_full.pine` uncommitted. Fixed in working tree this session (regenerated, diff-verified); JSON provenance depends on runtime regeneration.
- **H4: gate drift.** Prior docs used SPY PF≥1.70 (mandate: 1.75), N ranges 180–230/60–100, BTC DD≤14 — none in the mandate. This file uses mandate thresholds only.
- **H5: per-ticker hardcoding.** `isSPY/isQQQ/isCrypto` branch pivots/gaps/entries (master L61–70, L229–251): three asset-specific sub-strategies sharing a risk engine, presented as one generalized edge. Not yet reframed in strategy docs; generalization run (10+ untuned tickers) not yet executed. Follow-up required before any generality claim.
- **H6: compounding sizing sensitivity unrun.** `riskAmount = strategy.equity × 1.5%` compounds; fixed-capital cross-check pending trade-log export. Economics (≈+1.5% total on SPY/QQQ Full) make this load-bearing.
- **H7: cooldown (3/2 bars) unvalidated; housing filter (PERMIT ≥ −50.0) effectively dormant; continuation/reversal mix unknown.** All await trade logs + sweeps. No ablation claim stands (no `indicator_ablation_results.csv`).

*Generated 2026-09-09 — FAILs reported as FAILs. Prior "Pooled PASS" banner withdrawn.*
