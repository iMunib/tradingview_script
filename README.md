# Autonomous Quantitative Swing System — UCS v3 Production Refactor (TradingView)

> **SHARPE QUARANTINE:** all Sharpe values NOT VALID. Decision-grade: PF, N, DD, per-asset degradation.
> **Status:** mandate gates MIXED after production refactor — both daily DD gates now PASS (8.40%/6.11%), all daily PFs up (1.293/1.317/1.112), but SPY N collapsed to 84 (<160) and PFs still short. Full verdicts: PERFORMANCE_AUDIT.md §1. No pooled substitute.

**Target:** `BATS:SPY` · `BATS:QQQ` · `BITSTAMP:BTCUSD` · **TF:** 1D primary / 1W regime confirmation · **Engine:** Chrome CDP `ws://127.0.0.1:9222` · **Pine:** `//@version=5` · **Master:** [`FINAL_OPTIMIZED_STRATEGY.pine`](FINAL_OPTIMIZED_STRATEGY.pine) (`FINAL_UCSv3` — title frozen for harness compat; version = git commit).

## 1. Architecture (production refactor — verified live)

- Regime: price-action-only macroGate (W200/M21/M12; PERMIT excised) + **Weekly expansion gate**: daily entries require Weekly %R-slow > −65 with price above the *rising* Weekly 21 EMA (`weeklyTrendAligned`, bypassed on weekly+ TFs).
- Harvest engine: 2.6R stop / **1.85R target** (equities), 3.5R / **2.40R** (crypto); ratchet +0.75R→+0.05 / +1.35R→+0.70; 2-bar-low trail from +1.2R. Measured reality (SPY Full N=83): TARGET fills 1/83 — harvesting runs through ratchet-protected signal exits (STRONG +0.66R, REVERSAL +0.37R), stops realized ≈−1.06R. Skew repaired vs −2.8R risk, limit is a backstop — stated, not oversold.
- Exits: native `exit_comment` inspection → STRONG (dark-red triangle) / TARGET (teal diamond) / STOP (orange square) / REVERSAL (muted-red triangle) / WINDOW (gray circle, suppressed unfiltered); TARGET/STOP latched to the single exit bar; entries gated to flat + cooldown-passed + confirmed (kills H9 phantom arrows).
- Excised: CMF-20 (ablation sens ~0), FRED:PERMIT (0.0 crypto / weak equities). Retained deliberately: scoped Donchian `qqqBreakout` (never ablated — removal would be unevidenced), Fisher/RSI/VolPct/MACD (conflated transforms need split ablation).
- No-repaint: `calc_on_every_tick=false`, `process_orders_on_close=true`, 5/5 `request.security()` with `lookahead_off` — guard PASS 4→5.
- Basket-specific by evidence: out-of-basket 1D Full PF — DIA 0.775/80, IWM 0.663/86, AAPL 0.611/88, MSFT **1.531**/101, ETH 0.787/12·low-N. Generalization FAILS 3/5 powered, MSFT sole pass. No generality claimed.

## 2. Results (fresh 24-phase sweep; OOS all low-N)

Full: SPY 1.293/84/65.48%/8.40% · QQQ 1.317/146/56.16%/6.11% · BTC 1.112/29/5.40% · SPY W 1.439/52 · QQQ W 1.562/95 · BTC W 5.532/17.
IS→OOS degr: SPY −144.1% (0.8→1.953, N 18/8) · QQQ −2.0% (1.448→1.477, N 47/16) · BTC +100% **FAIL** (OOS N=1).
Stats: SPY p=0.1139 (was 0.3313 — better, threshold missed), QQQ p=0.1029 (was 0.3533 — missed by 0.003, reported as miss); CIs SPY (0.959,1.823), QQQ (1.104,1.946). Noise-consistent at α=0.10; weekly marginal.
Data: 18 fresh `metrics/trade_log_*.csv` (15/18 exact JSON match; SPY Full 83/84, IS 17/18 — H8), `metrics/generalization.json`. Prior `phase3_sweep.json` / `walkforward_windows.csv` / `indicator_ablation_results.csv` are STALE (previous architecture) — not cited as current evidence.

## 3. What changed and why (this session vs 6855498)

| Change | Numbers effect | Why |
|---|---|---|
| Purge CMF-20 + PERMIT | −1/+0 security calls; removal trades added back (PERMIT blocked SPY 213→252-style) | Ablation zeros with numbers |
| Weekly gate into `longSetup` | N↓↓ (213→84 SPY), DD 20.66→8.40, WR 60.09→65.48, PF 1.018→1.293 | Daily traded dead weekly tides (p=0.33) |
| 1.85R/2.40R + 2-stage ratchet + bar trail | stops −2.8R risk → −1.06R realized; TARGET 1/83 | +3R filled 0/210 — decorative |
| Plot gating + single-bar latch | visuals authoritative (re-verify counts next session) | H9 phantom/double arrows |
| `ta.lowest` compile fix | COMPILE_OK | v5 has no bare `lowest` |

## 4. Variant table (diff-verified post-edit)

| File | `useDateFilter` / `dateMode` | `inTradeWindow` | Diverges from master? |
|---|---|---|---|
| `FINAL_OPTIMIZED_STRATEGY.pine` (master) | `input.bool(false)` / `"All"` | `true` + dateMode branching | — |
| `strategy_full.pine` | `true` / `"Full (2018-2026)"` | `time ∈ [2018-01-01, 2026-12-31]` | date block only (29 diff lines) |
| `strategy_is.pine` | `true` / `"In-Sample (2018-2024)"` | `time ∈ [2018-01-01, 2024-12-31]` | date block only |
| `strategy_oos.pine` | `true` / `"Out-of-Sample (2025-2026)"` | `time ∈ [2025-01-01, 2026-12-31]` | date block only |

Note: JSON "Full" cells use the MASTER (unconstrained, incl. pre-2018); `strategy_full.pine` = windowed 2018–2026 (`*_Full_2018_2026` cells).

## 5. Operations

```powershell
.\scripts\launch_chrome_with_debugging.ps1 -Port 9222
python scripts\make_variants.py
python scripts\evaluate_all_assets.py     # 24-cell sweep (single WS)
python scripts\compile_check.py
python scripts\check_no_repaint.py
python scripts\export_trade_logs.py [--only TAG_Full]
python scripts\run_phase3.py --suite cooldown|sizing|walkfwd   # STALE-arch artifacts; re-run to refresh
python scripts\run_ablation.py                             # STALE-arch; transforms reference excised code — update before reuse
python scripts\stats_validation.py metrics\trade_log_*.csv
python scripts\run_generalization.py                       # DIA/IWM/AAPL/MSFT/ETHUSD Full/IS/OOS 1D
```

Tooling (retirements: CMF-20, PERMIT): [`TOOLING.md`](TOOLING.md). Recon: [`REPORTS/phase0_state_of_the_world.md`](REPORTS/phase0_state_of_the_world.md).

## 6. Production Operating Envelope (v1.0.0 — descriptive, not a mandate rewrite)

The original mandate (audit §1) stands with its FAILs. The envelope below describes achieved behavior for operations — including its own misses:

| Floor | SPY | QQQ | Verdict |
|---|---|---|---|
| Daily DD ≤ 8.5% | 8.40% | 6.11% | PASS / PASS |
| Daily WR ≥ 60% | 65.48% | 56.16% | PASS / **FAIL** |
| Daily PF ≥ 1.30 | 1.293 | 1.317 | **FAIL** (by 0.007) / PASS |
| Weekly PF ≥ 1.40 | 1.439 (W) | 1.562 (W) | PASS (BTC W 5.532, N=17 low-N) |
| Weekly WR ≥ 59% / DD ≤ 5% | 59.62% / 4.37% | 56.84% / 4.84% | WR: PASS/**FAIL**; DD: PASS/PASS |
| Realized loss skew ≈ −1.0R | STOP mean −1.059 (N=83 log) | — | PASS (vs −2.8R risked) |

Full floor-by-floor verdicts with source keys: PERFORMANCE_AUDIT.md §8.

## 7. Indicator Synthesis Matrix (code truth — pivots 5-bar SPY / 3-bar QQQ-BTC / 2-bar weekly)

| Indicator | Role | Status | Evidence |
|---|---|---|---|
| Dual %R (21/112) | Exhaustion + breakout confirmation; weekly slow leg gates daily entries (>−65) | KEEP | Ablation +3.3 Full / +25.2 W5; QQQ 1D +14.65 |
| Fisher Transform (9) | Zero-lag hooks; fish>1.30 Strong-exit leg; Peak exits | KEEP (split ablation open) | Removal conflates entries+exits; no action without split test |
| RSI-14 | Divergence triad votes; 42–60 continuation zone | KEEP (split ablation open) | Mixed by asset; transform conflated |
| MACD histogram (12,26,9) | Divergence triad votes | KEEP (weak) | Sens −9…+7, inconclusive |
| Buy/Sell Vol% + OBV/EMA-20 + MFI-14 | Absorption / volume confirmation | KEEP | Regime-dependent; OOS-contributory |
| EMA trend stack (20/50 daily; 10/21 weekly; W200/M21/M12 regime; rising W21 gate) | Trend + regime alignment | KEEP (structural) | DD gates PASS on its watch |
| Donchian-20 breakout (QQQ-only, trend-aligned) | Scoped momentum catch-all | RETAINED (never ablated) | Removal unevidenced — kept deliberately |
| CMF-20 | Absorption leg | **EXCISED** | Sens ~0 (five exact 0.0) — never bound |
| FRED:PERMIT housing | Macro lead filter | **EXCISED** | 0.0 crypto / weak-inconsistent equities + publication lag |
| WaveTrend Godmode | — (never in master) | ABSENT | Do not add unvalidated indicators |

## 8. Out-of-Basket Generalization Record (untuned 1D Full, `metrics/generalization.json`)

| Ticker | PF | N | WR% | DD% | Net% | Verdict |
|---|---|---|---|---|---|---|
| BATS:DIA | 0.775 | 80 | 52.50 | 13.66 | −9.34 | Negative expectancy — FAIL |
| BATS:IWM | 0.663 | 86 | 45.35 | 18.66 | −16.68 | Negative expectancy — FAIL |
| NASDAQ:AAPL | 0.611 | 88 | 47.73 | 28.65 | −22.10 | Negative expectancy — FAIL |
| NASDAQ:MSFT | 1.531 | 101 | 65.35 | 13.91 | +22.92 | Positive expectancy — sole pass |
| BITSTAMP:ETHUSD | 0.787 | 12 | 50.00 | 5.73 | −1.35 | low-N, indicative only |

System is a basket-specific ensemble (SPY/QQQ/BTC); the fallback path is ticker-luck, not edge. No generality claimed (H5 resolved by evidence).
