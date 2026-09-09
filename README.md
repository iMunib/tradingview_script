# Autonomous Quantitative Swing System — UCS v3 for TradingView

> **SHARPE QUARANTINE:** all Sharpe values NOT VALID (no variance, not annualized). Decision-grade: PF, N, DD, per-asset degradation.

**Target:** `BATS:SPY` · `BATS:QQQ` · `BITSTAMP:BTCUSD` · **TF:** 1D primary / 1W regime confirmation · **Engine:** Chrome CDP `ws://127.0.0.1:9222` · **Pine:** `//@version=5` · **Master:** [`FINAL_OPTIMIZED_STRATEGY.pine`](FINAL_OPTIMIZED_STRATEGY.pine) (`FINAL_UCSv3`) · **Status:** Full-history mandate gates FAIL (see PERFORMANCE_AUDIT.md §1) — no pooled substitute claimed.

> UCS v3 — hysteresis + tiering + scoped breakout. 3-bar daily / 2-bar weekly post-exit cooldown; STRONG BUY (2/3 triad or %R+BuyVol%>60%) vs BUY; exits fully taxonomized (§1); SPY ex-breakout; QQQ breakout only trend-aligned; BTC on %R/Fisher-hook with 0.58 absorption; Dual-%R 21/112 + Fisher-9 ±1.20 + triad 2/3 + BuyVol%/CMF20 + PERMIT housing + W200; unified 42–60 RSI pullback; 2.8/3.0R + 3.5/3.45R with 0.90→+0.05/1.60→+0.80/2.40→+1.65 ratchet.

## 1. Architecture (verified this session)

- Hysteresis: `lastExitBar`, `cooldownPassed = bar−lastExit ≥ (weekly?2:3)`; entries blocked post-exit; HUD shows COOLDOWN. Parameter value unvalidated — sweep pending trade logs.
- Entry tiering: `isStrongBuy = entry and (votes≥2 or (%R and BuyVol%>60))`; `isBuy = entry and not isStrongBuy` — mutually exclusive off one rising edge.
- Exit taxonomy (mutually exclusive, priority-ordered):
  | Label | Trigger | Visual | Trade-list trace |
  |---|---|---|---|
  | STRONG EXIT | `isStrongExit` (bear 2/3 + fish>1.30, or overbought + SellVol%>60%) | dark red, large | `comment="Strong Exit"` |
  | EXIT REVERSAL | `isPeakExit` (fresh bear confluence or Fisher exit hook) | muted red `#CD5C5C` | `comment="Exit Reversal"` |
  | EXIT STOP / TARGET | bracket fill (emulator stop/limit hit) | orange, small | `comment_loss="Exit Stop"` / `comment_profit="Exit Target"` on all 4 `strategy.exit()` calls |
  | EXIT WINDOW | date-filter forced close | gray diamond, **suppressed unless date filter on** | `comment="Window End"` (backtest artifact, not edge) |
- HUD STATUS shows the actual reason latch (`lastExitReason`), including `LAST EXIT: …` when flat — never a generic "EXIT / TP HIT". Limitation disclosed: which bracket leg filled is known only from the trade-list comment, not intrabar in the HUD.
- Scoping (honest framing — see §4): SPY no breakout; `qqqBreakout` only QQQ+trend; BTC `btcVolAbsorption`. Per-ticker branches (`isSPY/isQQQ/isCrypto`, master L61–70, L229–251) make this three asset-specific sub-strategies sharing one risk/exit engine until a 10+ untuned-ticker generalization run proves otherwise.
- No-repaint: `calc_on_every_tick=false`, `process_orders_on_close=true`, 4/4 `request.security()` with `lookahead_off` — enforced by `scripts/check_no_repaint.py` + pre-commit hook.

## 2. Results (traced to `metrics/all_assets_evaluation.json`; OOS cells low-N, indicative only)

Full history: SPY PF 1.018 / N 213 / DD 20.66% · QQQ 1.017 / 241 / 15.49% · BTC 0.936 / 91 / 14.83% · SPY W 1.791/39 · QQQ W 1.599/55 · BTC W 6.915/17.
Windowed 2018–2026: SPY 0.987/65 · QQQ 1.391/97 · BTC 1.226/50 · SPY W 1.09/12 · QQQ W 2.075/19 · BTC W 8.021/12.
IS 2018–2024: SPY 0.774/52 · QQQ 1.319/79 · BTC 1.374/42 · SPY W 0.847/10 · QQQ W 5.656/16 · BTC W 9.591/8.
OOS 2025–2026 (ALL low-N): SPY 2.854/13 · QQQ 2.033/18 · BTC 0.719/9 · SPY W PF undefined (2/2 wins) · QQQ W 0.511/3 · BTC W 2.848/4.
Per-asset degradation: SPY −268.73% · QQQ −54.13% · BTC **+47.67% (FAIL)**. No pooled headline — withdrawn, see audit H2.
Full tables + gates: [`PERFORMANCE_AUDIT.md`](PERFORMANCE_AUDIT.md). State-of-world recon: [`REPORTS/phase0_state_of_the_world.md`](REPORTS/phase0_state_of_the_world.md).

## 3. What changed and why (this session vs 26f2b88)

| Change | Effect on numbers | Why |
|---|---|---|
| Exit taxonomy + `comment_profit/loss` + HUD reason latch | **None** — live re-run SPY 1D Full identical (1.018/213/20.66%) | Exits were visually indistinguishable; stop vs target hits untraceable |
| "Peak Exit" → "Exit Reversal" + own shape; WINDOW suppressed when filter off | None | Killed double-triangle artifact (same-bar trigger + next-bar echo) |
| `scripts/check_no_repaint.py` + pre-commit hook | None | Lock the no-repaint model |
| Withdrew "Pooled −20.64% PASS"; per-asset gates only | Headline FAIL (honest) | Pooled metric not in mandate; inputs 100% low-N; null-PF cap artifact |

## 4. Variant table (diff-verified 2026-09-09)

| File | `useDateFilter` / `dateMode` | `inTradeWindow` | Diverges from master? |
|---|---|---|---|
| `FINAL_OPTIMIZED_STRATEGY.pine` (master) | `input.bool(false)` / `"All"` | `true` + dateMode branching | — |
| `strategy_full.pine` | `true` / `"Full (2018-2026)"` | `time ∈ [2018-01-01, 2026-12-31]` | date block only (29 diff lines) |
| `strategy_is.pine` | `true` / `"In-Sample (2018-2024)"` | `time ∈ [2018-01-01, 2024-12-31]` | date block only |
| `strategy_oos.pine` | `true` / `"Out-of-Sample (2025-2026)"` | `time ∈ [2025-01-01, 2026-12-31]` | date block only |

Regenerate: `python scripts\make_variants.py` (also auto-run at each `evaluate_all_assets.py` sweep start). Note: at commit 26f2b88 the committed variants were stale baseline files — fixed in tree this session; always regenerate before a sweep.

## 5. Operations

```powershell
.\scripts\launch_chrome_with_debugging.ps1 -Port 9222
python scripts\make_variants.py
python scripts\evaluate_all_assets.py     # full 24-cell sweep (~5 min, single WS)
python scripts\compile_check.py           # fast compile-only check of the master
python scripts\check_no_repaint.py        # repaint guard (also pre-commit)
```

Tooling inventory: [`TOOLING.md`](TOOLING.md). Validation scaffolding (walk-forward runner, bootstrap/permutation on trade logs): `scripts/run_walkforward.py`, `scripts/stats_validation.py` — pending CDP sweep time and trade-list export; no numbers claimed until run.
