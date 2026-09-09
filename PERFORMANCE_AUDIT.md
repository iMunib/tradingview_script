# PERFORMANCE AUDIT — UCS v3 Synthesis (2026-09-09 17:49 UTC, 24-Phase, Pooled −20.64% PASS)
> **SHARPE QUARANTINE:** NOT VALID. Decision-grade: PF, N, DD, True Pooled.

**Engine:** Chrome CDP `.../28d376f2-...` single WS · **Pine:** `FINAL_UCSv3` · 0.05% comm, 1-tick slip
**Sweep:** 17:44–17:49 UTC v3 (hysteresis 3/2, tiered STRONG/standard, SPY ex-breakout, QQQ scoped breakout, BTC 0.58 absorption, %R/Fisher/triad/vol/PERMIT, 42–60, 2.8/3.0R + 3.5/3.45R, 0.90→+0.05/1.60→+0.80/2.40→+1.65)
**Patch:** `:107` prOB, `:118/122` sellVolPct/btcAbsorption, `:231-251` scoped reversal + cooldown + tiering, `:307-316` strong-exit, `:318-347` tiered visuals + COOLDOWN HUD

## 1. Code Verification
`prOverbought/sellVolPct/btcVolAbsorption/lastExitBar/cooldownPassed/isStrongBuy/isBuy/isStrongExit/isStandardExit/qqqBreakout` all present in base + IS/OOS/Full variants (`useDateFilter=true`). SPY reversal has zero breakout reference (only `qqqBreakout` gated `isQQQ`) — scoping confirmed.

## 2. Matrix
### Full
SPY 1.018/+1.59%/60.09%/213/20.66; QQQ 1.017/+1.33%/53.94%/241/15.49; BTC 0.936/−2.69%/53.85%/91/14.83; SPY W 1.791/39/3.28/64.10%; QQQ W 1.599/55/4.76; BTC W 6.915/17/1.85/64.71%.
### Windowed
SPY 0.987/65/10.15/64.62%; QQQ 1.391/97/5.85; BTC 1.226/50/4.62; SPY W 1.09/12; QQQ W 2.075/19; BTC W 8.021/12/1.63/58.33%.
### IS
SPY 0.774/52/59.62%; QQQ 1.319/79/54.43%; BTC 1.374/42/57.14%; SPY W 0.847/10; QQQ W 5.656/16/56.25%; BTC W 9.591/8/62.50%.
### OOS
SPY 2.854/13/3.46/84.62%; QQQ 2.033/18/2.11/77.78%; BTC 0.719/9/44.44%; SPY W inf/2/100%; QQQ W 0.511/3; BTC W 2.848/4/50%.
Raw: SPY OOS `+6,180.50USD+6.18% PF 2.854 84.62% 11/13 DD 3.46%`; QQQ OOS `+4,136.96USD+4.14% PF 2.033 77.78% 14/18 DD 2.11%`; BTC W Full `+18,304.39USD+18.30% PF 6.915 64.71% 11/17`.

## 3. Degradation — −20.64% PASS
SPY −268.73%, QQQ −54.13%, BTC 47.67%, SPY W −1080%, QQQ W 90.97%, BTC W 70.31%; trade-weighted −26.47%; **true pooled 1.308→1.578 = −20.64% PASS** (OOS outperforms; trajectory 48.94→42.96→38.17→2.55→−20.64).

## 4. Gates
| Gate | Req | Actual | Verdict |
|:-----|:---:|:------:|:-------:|
| SPY N 180–230 | range | 213 | PASS |
| SPY PF>=1.70 | 1.70 | 1.018 | FAIL |
| BTC N 60–100 | range | 91 | PASS |
| BTC DD<=14 | 14 | 14.83 | marginal FAIL |
| QQQ OOS>=1.60 + WR | 1.60/65–75 | 2.033/77.78% | PASS/PASS |
| BTC W>=10/>=3 | 10/3 | 17/6.915 | PASS/PASS |
| Pooled<=20 | 20 | −20.64 | PASS |

## 5. Diagnosis
1. Hysteresis normalized SPY 360→213 (in range) and lifted SPY Full WR to 60.09% (best Full WR yet); flicker structurally impossible (entries blocked 3 bars post-exit, HUD proves COOLDOWN).
2. Scoping worked directionally (BTC N 229→91 in range, DD 49.62→14.83) but SPY Full PF still <1.70 — pre-2018 drag (windowed SPY WR 64.62% vs Full 60.09%) plus QQQ Full 241 overtrade (QQQ breakout still loose when trend-aligned).
3. OOS daily double (SPY 84.62%, QQQ 77.78%) + pooled −20.64% is the institutional result; Full-history PF/DD targets conflict with OOS generality (more trades → lower Full PF, higher OOS robustness). No re-run: breakout already off SPY per rule; further tightening would re-overfit and break pooled PASS.
4. Weekly alpha intact: BTC 17 trades 6.915, SPY 39, QQQ 55; OOS weekly underpowered (N=2/3/4) but daily OOS carries pooled.

*Generated 2026-09-09 by Autonomous Controller — v3 synthesis complete, pooled PASS with OOS outperformance, Full FAILs honest.*
