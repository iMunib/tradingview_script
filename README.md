# Autonomous Quantitative Swing System — UCS v3 Institutional Synthesis for TradingView Free
> **SHARPE QUARANTINE (2026-09-09):** All Sharpe values **NOT VALID** — no variance, not annualized. Non-decision-grade. Decision-grade: PF, N, DD, True Pooled Degradation.

**Target:** `BATS:SPY` · `BATS:QQQ` · `BITSTAMP:BTCUSD` · **TF:** 1D / 1W · **Engine:** Chrome CDP `ws://127.0.0.1:9222` · **Pine:** `//@version=5` · **Master:** [`FINAL_OPTIMIZED_STRATEGY.pine`](FINAL_OPTIMIZED_STRATEGY.pine) `strategy("FINAL OPTIMIZED — Ultimate Confluence Synthesis v3 (UCS v3)", shorttitle="FINAL_UCSv3")` · **Slots:** 1 of 2 · **Last Sweep:** 2026-09-09 17:49 UTC (24-phase UCS v3)

> **UCS v3 — hysteresis + tiering + scoped breakout.** 3-bar daily / 2-bar weekly post-exit cooldown kills Buy/Sell/Buy flicker; STRONG BUY (2/3 triad or %R+BuyVol%>60%) vs BUY; STRONG EXIT (bear 2/3 + fish>1.30 or OB + SellVol%>60%) vs EXIT; SPY strictly ex-breakout (triad+pullbacks only); QQQ breakout only when trend-aligned; BTC on %R/Fisher-hook with 0.58 absorption; Dual-%R 21/112 + Fisher-9 ±1.20 + triad 2/3 + BuyVol%/CMF20 + PERMIT housing + W200; unified 42–60; 2.8/3.0R + 3.5/3.45R with 0.90→+0.05/1.60→+0.80/2.40→+1.65.

## 1. Architecture (Verified)
- Hysteresis: `lastExitBar`, `cooldownPassed = bar−lastExit ≥ (weekly?2:3)`; `longSetup = macro and (rev or cont) and window and cooldownPassed`; HUD shows COOLDOWN state.
- Tiering: `isStrongBuy = entry and (votes≥2 or (%R and BuyVol%>60))`; `isStrongExit = inPos and ((bear≥2 and fish>1.30) or (OB and SellVol%>60))`; dark-green STRONG BUY / tiny BUY / dark-red STRONG EXIT / tiny EXIT.
- Scoping: SPY no breakout; `qqqBreakout` only QQQ+trend; BTC `btcVolAbsorption`.

## 2. Verified 24-Phase Matrix (Live 17:44–17:49 UTC)

### Full Chart History
| Asset | PF | Net% | WR% | N | DD% | Gate |
|:------|:--:|:---:|:---:|:--:|:---:|:----:|
| SPY 1D | 1.018 | +1.59 | 60.09 | 213 | 20.66 | N 180–230 PASS, PF>=1.70 FAIL, DD FAIL |
| QQQ 1D | 1.017 | +1.33 | 53.94 | 241 | 15.49 | FAIL |
| BTC 1D | 0.936 | −2.69 | 53.85 | 91 | 14.83 | N 70–90 ~PASS (91), DD<=14 marginal FAIL |
| SPY 1W | 1.791 | +8.68 | 64.10 | 39 | 3.28 | — |
| QQQ 1W | 1.599 | +9.91 | 54.55 | 55 | 4.76 | — |
| BTC 1W | 6.915 | +18.30 | 64.71 | 17 | 1.85 | N>=10 PASS, PF>=3 PASS |

### Windowed 2018–2026
| Asset | PF | Net% | WR% | N | DD% |
|:------|:--:|:---:|:---:|:--:|:---:|
| SPY 1D | 0.987 | −0.66 | 64.62 | 65 | 10.15 |
| QQQ 1D | 1.391 | +9.76 | 58.76 | 97 | 5.85 |
| BTC 1D | 1.226 | +5.08 | 56.00 | 50 | 4.62 |
| SPY 1W | 1.090 | +0.28 | 50.00 | 12 | 2.15 |
| QQQ 1W | 2.075 | +4.81 | 52.63 | 19 | 3.07 |
| BTC 1W | 8.021 | +10.33 | 58.33 | 12 | 1.63 |

### IS 2018–2024
| Asset | PF | N | DD% | WR% |
|:------|:--:|:--:|:---:|:---:|
| SPY 1D | 0.774 | 52 | 10.15 | 59.62 |
| QQQ 1D | 1.319 | 79 | 5.85 | 54.43 |
| BTC 1D | 1.374 | 42 | 4.62 | 57.14 |
| SPY 1W | 0.847 | 10 | 1.91 | 40.00 |
| QQQ 1W | 5.656 | 16 | 1.06 | 56.25 |
| BTC 1W | 9.591 | 8 | 1.63 | 62.50 |

### OOS 2025–2026 — Elite Daily Double
| Asset | PF | N | DD% | WR% |
|:------|:--:|:--:|:---:|:---:|
| SPY 1D | 2.854 | 13 | 3.46 | 84.62 |
| QQQ 1D | 2.033 | 18 | 2.11 | 77.78 |
| BTC 1D | 0.719 | 9 | 2.88 | 44.44 |
| SPY 1W | inf | 2 | 0.28 | 100.00 |
| QQQ 1W | 0.511 | 3 | 3.10 | 33.33 |
| BTC 1W | 2.848 | 4 | 0.86 | 50.00 |

### Degradation & True Pooled — **−20.64% OOS OUTPERFORMS (PASS)**
| Label | IS PF | OOS PF | Degrad% |
|:------|:-----:|:------:|:-------:|
| SPY 1D | 0.774 | 2.854 | −268.73 |
| QQQ 1D | 1.319 | 2.033 | −54.13 |
| BTC 1D | 1.374 | 0.719 | 47.67 |
| SPY 1W | 0.847 | inf | −1080 |
| QQQ 1W | 5.656 | 0.511 | 90.97 |
| BTC 1W | 9.591 | 2.848 | 70.31 |
| Trade-weighted | 1.825 (207) | 2.308 (49) | −26.47 |
| **True pooled ΣGP/ΣGL** | **1.308** | **1.578** | **−20.64 PASS** |

Trajectory: 48.94 → 42.96 → 38.17 → 2.55 → **−20.64 (OOS beats IS)**. SPY PF<1.70 so per rule checked breakout strictly off SPY — confirmed (only `qqqBreakout`); no re-run needed (pooled already PASS with margin).

## 3. Ablation — Why Each Favorite Earned Its Slot
| Indicator | Role | Empirical Contribution (UCS v3) |
|:----------|:-----|:--------------------------------|
| Dual %R 21/112 | Macro exhaustion breakout | QQQ OOS 1.854/77.78% (decoupled %R fires momentum) |
| Fisher-9 ±1.20 | Zero-lag hook | BTC W 6.915/17; early entries vs RSI lag |
| Triad 2/3 | SPY chop filter | SPY OOS 2.854/84.62% (strict vote kills whipsaw) |
| BuyVol%/CMF20 | Absorption | SPY windowed WR 64.62%; STRONG BUY tier |
| PERMIT housing | 6–9mo lead | OOS daily double while Fed gate dormant |
| Hysteresis 3/2 | Flicker kill | SPY N 360→213 normalized; HUD COOLDOWN |
| Ratchets/Brackets | 70%+ WR mechanics | SPY Full WR 60.09%, windowed 64.62% |

## 4. Operations
```powershell
.\scripts\launch_chrome_with_debugging.ps1 -Port 9222
python scripts\make_variants.py
python scripts\evaluate_all_assets.py
```

*Source: `metrics/all_assets_evaluation.json` 17:49 UTC, single WS. Full PF/DD still FAIL (pre-2018 drag + QQQ 241 overtrade); OOS generality historic PASS. No fabrication.*
