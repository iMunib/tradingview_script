# Autonomous Quantitative Swing System — UCS v3 for TradingView

> **SHARPE QUARANTINE:** all Sharpe values NOT VALID (no variance, not annualized). Decision-grade: PF, N, DD, per-asset degradation.
> **Status:** Full-history mandate gates FAIL (see PERFORMANCE_AUDIT.md §1) — daily edge statistically indistinguishable from noise (§6); no pooled substitute claimed.

**Target:** `BATS:SPY` · `BATS:QQQ` · `BITSTAMP:BTCUSD` · **TF:** 1D primary / 1W regime confirmation · **Engine:** Chrome CDP `ws://127.0.0.1:9222` · **Pine:** `//@version=5` · **Master:** [`FINAL_OPTIMIZED_STRATEGY.pine`](FINAL_OPTIMIZED_STRATEGY.pine) (`FINAL_UCSv3`).

## 1. Architecture (verified this session)

- Hysteresis: `lastExitBar`, `cooldownPassed = bar−lastExit ≥ (weekly?2:minCooldownBars)` (`minCooldownBars` input, default 3, range 1–15). Sweep result: asset-specific — SPY DD improves with longer freezes, QQQ PF degrades; default 3 retained with evidence (audit §3). HUD shows COOLDOWN.
- Entry tiering: `isStrongBuy = entry and (votes≥2 or (%R and BuyVol%>60))`; `isBuy = entry and not isStrongBuy` — mutually exclusive off one rising edge. Note: shapes plot signals even when no fill occurs in-position/in-cooldown (331 signals vs ~211 fills on SPY Full — cosmetic over-plot, audit H9).
- Exit taxonomy (native closed-trade inspection — `strategy.closedtrades.exit_comment()` on the exit bar/+1):
  | Label | Trigger | Visual | Trade-list trace |
  |---|---|---|---|
  | STRONG EXIT | `isStrongExit` (bear 2/3 + fish>1.30, or overbought + SellVol%>60%) | dark red triangle, large | `comment="Strong Exit"` |
  | EXIT — TARGET | `exit_comment` contains "Exit Target" | teal diamond | `comment_profit="Exit Target"` |
  | EXIT — STOP | `exit_comment` contains "Exit Stop" | orange square | `comment_loss="Exit Stop"` |
  | EXIT — REVERSAL | `isReversalExit` (fresh bear confluence / Fisher hook) | muted-red triangle | `comment="Exit Reversal"` |
  | WINDOW END | date-filter forced close | gray circle, **suppressed unless filter on** | `comment="Window End"` (artifact, not edge) |
- Verified end-to-end (SPY 1D Full, chart-model shape counts vs CSV reasons): STRONG 97=97, REVERSAL 62=62, STOP shape 102=51×2 bars (documented 2-bar emission), TARGET 0, WINDOW 0.
- HUD STATUS latches the exact reason (`TARGET HIT` / `STOPPED OUT` / `STRONG EXIT` / `REVERSAL` / `LAST EXIT: …`).
- Scoping (honest framing): SPY no breakout; `qqqBreakout` only QQQ+trend; BTC absorption. Per-ticker branches (`isSPY/isQQQ/isCrypto`, master L61–70, L229–251) = three asset-specific sub-strategies sharing one risk engine until a 10+ untuned-ticker run proves otherwise.
- No-repaint: `calc_on_every_tick=false`, `process_orders_on_close=true`, 4/4 `request.security()` with `lookahead_off` — enforced by `scripts/check_no_repaint.py` + pre-commit hook (PASS 4→4 this session).

## 2. Results (traced; OOS + all walk-forward tests low-N, indicative only)

Full: SPY PF 1.018/N 213/DD 20.66% · QQQ 1.017/241/15.49% · BTC 0.936/91/14.83% · SPY W 1.791/39 · QQQ 1.599/55 · BTC W 6.915/17.
IS→OOS degradation: SPY −268.73% · QQQ −54.13% · BTC **+47.67% (FAIL)** (OOS N=13/18/9).
Statistics: daily PF 90% CIs all include 1.0 (perm p 0.24–0.47, noise-consistent); weekly marginal (SPY W p=0.082, QQQ W p=0.092). Walk-forward: 30/30 test cells low-N — annual windows cannot power this frequency.
Ablation (exploratory): REMOVE CMF-20 (sens ~0) and PERMIT (0.0 crypto / weak equities); KEEP Dual-%R; W200 structural; Fisher/RSI/VolPct/MACD need split-ablation follow-ups (transforms conflated).
Full tables + verbatim excerpts: [`PERFORMANCE_AUDIT.md`](PERFORMANCE_AUDIT.md). Recon: [`REPORTS/phase0_state_of_the_world.md`](REPORTS/phase0_state_of_the_world.md). Data: `metrics/trade_log_*.csv` (18), `metrics/walkforward_windows.csv` (30), `metrics/indicator_ablation_results.csv` (120), `metrics/phase3_sweep.json`.

## 3. What changed and why (this session vs 5b1339e)

| Change | Numbers effect | Why |
|---|---|---|
| Closed-trade exit taxonomy (`exit_comment` inspection, 5 shapes, HUD latch) | **None** — cd=3 reproduces all 6 Full cells exactly | Bracket STOP vs TARGET were indistinguishable; generic triangles |
| `minCooldownBars` input (default 3) | None at default | Enables evidence-based cooldown choice (§3 result: asset-specific, keep 3) |
| Trade-log exporter (Pine emitter + chart-model read) | New data: 18 CSVs, 97–99% capture (H8 bounds the gap) | Unblocks all statistics; native export paywalled (TOOLING.md) |
| Walk-forward / bootstrap / ablation suites | New data: 30 + 96 + stats rows | Mandated protocol; results mostly negative — reported as such |
| Withdrew nothing further; prior pooled PASS stays withdrawn | Headlines unchanged (honest FAILs) | No new passing claim exists to make |

## 4. Variant table (diff-verified 2026-09-09 evening)

| File | `useDateFilter` / `dateMode` | `inTradeWindow` | Diverges from master? |
|---|---|---|---|
| `FINAL_OPTIMIZED_STRATEGY.pine` (master) | `input.bool(false)` / `"All"` | `true` + dateMode branching | — |
| `strategy_full.pine` | `true` / `"Full (2018-2026)"` | `time ∈ [2018-01-01, 2026-12-31]` | date block only (29 diff lines) |
| `strategy_is.pine` | `true` / `"In-Sample (2018-2024)"` | `time ∈ [2018-01-01, 2024-12-31]` | date block only |
| `strategy_oos.pine` | `true` / `"Out-of-Sample (2025-2026)"` | `time ∈ [2025-01-01, 2026-12-31]` | date block only |

Note: JSON "Full" cells (`SPY_1D_Full` etc.) were swept with the MASTER (unconstrained full history, incl. pre-2018); `strategy_full.pine` is the windowed 2018–2026 variant (`SPY_1D_Full_2018_2026` cells). Regenerate: `python scripts\make_variants.py` (also auto-run at each `evaluate_all_assets.py` sweep start).

## 5. Operations

```powershell
.\scripts\launch_chrome_with_debugging.ps1 -Port 9222
python scripts\make_variants.py
python scripts\evaluate_all_assets.py     # full 24-cell sweep (~6 min, single WS)
python scripts\compile_check.py           # fast compile+metrics check of the master
python scripts\check_no_repaint.py        # repaint guard (also pre-commit)
python scripts\export_trade_logs.py [--only TAG_Full]  # 18 trade-log CSVs (~30 min)
python scripts\run_phase3.py --suite cooldown|sizing|walkfwd
python scripts\run_ablation.py
python scripts\stats_validation.py metrics\trade_log_*.csv
```

Tooling inventory (incl. paywall findings + retired probes): [`TOOLING.md`](TOOLING.md).
