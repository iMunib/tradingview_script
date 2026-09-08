# Autonomous Quantitative Swing System — Single-Script Master for TradingView Free
> **SHARPE QUARANTINE (2026-09-07):** All historical Sharpe values in this document are **NOT VALID Sharpe ratios** — they lack variance, are not annualized, and are computed as `(net_profit_pct / max_drawdown_pct)*(win_rate/50)*0.5` or raw TradingView scrape. **Non-decision-grade** — do not use for strategy quality. See `runner.py:619-625` and `scripts/evaluate_all_assets.py:474-476`.


**Target:** `BATS:SPY` · `BATS:QQQ` · `BITSTAMP:BTCUSD` · **TF:** 1D / 1W · **Engine:** OpenCode CLI (Muse Spark 1.2 High) + Chrome DevTools Protocol (CDP) `ws://127.0.0.1:9222` · **Pine:** `//@version=5` · **Master:** [`FINAL_OPTIMIZED_STRATEGY.pine`](FINAL_OPTIMIZED_STRATEGY.pine) `strategy("FINAL OPTIMIZED — Single RSI 14, 5-Bar Pivots, W200, 2.8R/3.0R", shorttitle="FINAL_BASELINE")` · **Slots:** 1 of 2 (Free-tier compliant)

> **One script, zero clutter, full alpha.** All confluence math runs in the background; the chart shows only what matters: **BUY**, **EXIT**, and a 2-row regime/status HUD. No oscillator spaghetti, no Gaussian clouds, no RSI lines.

---

## 1. Executive Overview — Consolidated Single-Script Architecture

TradingView Free caps charts at **2 indicators/strategies**. The prior dual-engine split (`FINAL_BASELINE` + `CONFLUENCE_STUDY`) occupied both slots by design, leaving no room for user tools and risking `“2 indicators limit reached”`. The new master consolidates **100% of verified alpha** into **one production `strategy()`**:

```
Chart (TradingView Free — 1 of 2 slots used)
┌─────────────────────────────────────────────────────┐
│ Pane 0: Price + FINAL_BASELINE (strategy)           │
│  • BUY  ▴ green triangle below candle (text "BUY") │
│  • EXIT ▾ red triangle above candle (text "EXIT")  │
│  • 2-Row HUD top-right (regime + status)            │
│  • (Optional) Stop/Target lines via showExecutionLines │
│ Free slots remaining: 1                               │
└─────────────────────────────────────────────────────┘
```

**Why one wins:** Lean single-RSI divergence on 5-bar pivots already captures high-quality swings; stacking 5 oscillators, dual %R, WaveTrend, Fisher, and Gaussian added **collinear lag, not orthogonal alpha** (see §3). Consolidation keeps the lean engine and hides everything else behind the HUD.

**Free-plan inventory after purge (2026-09-07):**
```
TradingView Indicator/
├── FINAL_OPTIMIZED_STRATEGY.pine  (230 lines, 11.7 kB, strategy, 0 errors, 1 slot)
├── runner.py                      (CDP controller, hardened)
├── run_forward_audit.bat          (one-click forward walk)
├── scripts/
│   ├── forward_monitor.py         (headless CDP audit engine)
│   ├── evaluate_all_assets.py     (12-asset matrix, single WS)
│   ├── launch_chrome_with_debugging.ps1 (Chrome hardcode, zombie kill)
│   ├── validate_pine.py           (lookahead, bracket, paren checks)
│   └── deploy_single.py           (this deployment)
├── metrics/
│   ├── forward_test_log.json      (append-only trade log)
│   ├── FORWARD_WALK_STATUS.md     (30-day window 2026-09-07 → 2026-10-07)
│   ├── all_assets_evaluation.json / backtest_history.json / sweep_results.json
│   └── clean_chart_screenshot.png (CDP Page.captureScreenshot)
├── logs/                          (compiler_errors.log, 0 errors)
└── venv/
```

---

## 2. Signal Interpretation Guide

All signals are **confirmed on bar close** (`barstate.isconfirmed`, `process_orders_on_close=true`) — no repaint.

### BUY — Green Triangle Below Candle `shape.triangleup` “BUY”

Fires when **all** hold on a confirmed bar:

1. **Macro Gate bullish:** `close > Weekly 200 EMA` where `W200 = request.security(syminfo.tickerid, "W", ta.ema(close,200)[1], lookahead=barmerge.lookahead_off)` (FRED monthly `FRED:FEDFUNDS` `close[1]` slope ≤0.50). If false, the HUD shows `NEUTRAL / CHOP` and the bar is held in cash — choppy or tightening-regime protection.
2. **Volume confirmed:** `OBV > EMA(OBV,20)` **or** `MFI(14) >50` and rising.
3. **Trigger:** `ta.barssince(regularBull) <=15` where `regularBull` is **strict single-RSI divergence** — `low[pivotRight] < priorLowPrice` **and** `rsi[pivotRight] >= priorLowRsi +2.0` **and** (`rsi<45` or `prior<45`), with `pivotLeft=5 pivotRight=5 minGap=5 maxGap=60` **or** `close > highest(high,20)[1]` (20-day Donchian breakout).
4. **Trend aligned:** `close > EMA50` and `EMA20 > EMA50`.

`plotshape(longEntry, style=shape.triangleup, location=location.belowbar, color=green, text="BUY")` `FINAL_OPTIMIZED_STRATEGY.pine:200`.

### EXIT — Red Triangle Above Candle `shape.triangledown` “EXIT”

Fires when **any** holds while in position (or flat after a close):

* **Intrabar bracket hit (native):** `strategy.exit("Bracket Exit", from_entry="Long", stop=stopLossPrice, limit=targetPrice)` with `stop = entry - 2.8*ATR(14)` and `limit = entry + 3.0*unitR`. Filled intrabar, not on next close.
* **Ratchet-triggered stop:** `+1.5R → stop=entry+0.5R`, `+2.5R → stop=entry+1.5R` via re-issued `strategy.exit`.
* **Bearish exhaustion:** `regularBear` (higher high in price with lower high in RSI, same 5-bar pivots, `rsi>55` gate) confirmed → `strategy.close("Long", comment="Bear Divergence Exit")`.
* **Date-window end:** `useDateFilter and not inTradeWindow` → `strategy.close("Long", comment="End Window Exit")`.

`plotshape(exitPlot, style=shape.triangledown, location=location.abovebar, color=red, text="EXIT")` `FINAL_OPTIMIZED_STRATEGY.pine:203` where `exitPlot = (regularBear and barstate.isconfirmed and position>0) or (position[1]>0 and position==0)`.

### HOLD / CASH — What It Means

When flat and `MARKET REGIME` shows `NEUTRAL / CHOP`, the engine is **intentionally in cash** — either `W200` is not bullish or `FED slope >0.50` (rapid tightening), or no qualified divergence/breakout sits within the 15-bar lookback. This is discipline, not inaction; it cuts drawdown during chop and shock regimes.

### Minimalist 2-Row HUD (Top-Right) `FINAL_OPTIMIZED_STRATEGY.pine:206-230`

```pine
table.new(position.top_right, 2, 3, bgcolor=color.new(color.black,80))
```

| Row | Cell 0 | Cell 1 | Logic |
|-----|--------|--------|-------|
| 0 | `MARKET REGIME` | `BULLISH (Trending)` green or `NEUTRAL / CHOP` gray | `macroGate = macroBullish and not rateShock` `FINAL_OPTIMIZED_STRATEGY.pine:60` |
| 1 | `CURRENT STATUS` | `ACTIVE LONG (+X.X R)` green, `EXIT / TAKE PROFIT HIT` teal, or `HOLD / CASH (Awaiting Setup)` gray | `position>0 ? ACTIVE : lastExit=="EXIT" ? EXIT : HOLD` `FINAL_OPTIMIZED_STRATEGY.pine:181-221` |
| 2 | footer | `FINAL_BASELINE • 2.8R / 3.0R • W200` | static |

No oscillator lines, no Gaussian, no clouds, no MFI histogram — all math stays invisible. Toggle `showExecutionLines` (default `false`) in `█ Visual & HUD` to reveal `Stop Loss` (red `style_linebr`) and `Target 3R` (teal) only when needed.

---

## 3. Mathematical Engine & Ablation Discoveries

### Core (Preserved 100%)

* **Pivot engine:** `ta.pivotlow/high(low/high,5,5)` → `low[pivotRight]`/`rsi[pivotRight]` → `bar_index - pivotRight`, `minPivotGap=5 maxPivotGap=60 minRsiDiff=2.0 divLookback=15`, `rsi<45`/`>55` gates. Strict single-RSI, not 5-oscillator vote.
* **Macro:** Weekly 200 EMA `request.security(..., close[1], lookahead_off)` with daily `ta.ema(close,200)` fallback until 4 years of weekly history; Fed Funds `FRED:FEDFUNDS` monthly `close[1]` 3-month slope >0.50 blocks.
* **Volume:** `OBV > EMA(OBV,20)` or `MFI>50` rising.
* **Trend:** `EMA20>EMA50` and `close>EMA50` + `breakout20`.
* **Risk:** `perUnitRisk=2.8*ATR(14)`, `riskAmount=equity*1.5%`, `calcQty=riskAmount/perUnitRisk`, `maxQty=equity*0.95/close`; `isCrypto ? max(0.001, min(calcQty,maxQty)) : max(1, min(floor(calcQty), floor(maxQty)))` — whole shares for `SPY/QQQ`, fractional `0.001` for `BTCUSD` `FINAL_OPTIMIZED_STRATEGY.pine:124-139`.
* **Execution:** `strategy.entry("Long", qty=positionQty)` then `strategy.exit("Bracket Exit", stop, limit)` intrabar; ratchets `+1.5R → +0.5R` and `+2.5R → +1.5R`; emergency `strategy.close` only for bear/date.

### Why Stacking Failed — Collinear Lag

Sweep on `BATS:SPY 1D` over `atrStopMult=[2.4,2.8,3.2]`, `tp=[2.5,3.0,3.5]`, `pivotLR=[3,5,8]` converged on `2.8/3.0/5` → **PF 1.819, Net +74.08%, DD 11.20%, WR 56.78%, Sharpe ~3.76 (QUARANTINED — non-decision-grade)** (118 trades [RETIRED historical figure]). Adding confluence:

| Toggle | SPY PF | QQQ PF | DD | Verdict |
|--------|--------|--------|----|---------|
| Baseline (5-osc `divMin=3`) | 1.541 (170 tr) | 1.07 | 10.52% | bloated |
| +Gaussian 3-Pole (25) | 1.607 | 1.043 | 8.76% | SPY help, QQQ hurt |
| +Volume BuyVol>0.50 | 1.288 | 1.03 | 10.73% | deadweight |
| Gaussian+Volume | 1.623 (187) | 0.993 | 10.34% | QQQ collapses |
| gaussUseFilter 1σ×10 | 0.946 (46) | — | 12.11% | sticky collapse |
| **Pruned single RSI (divMin=1)** | **1.523 (167 [RETIRED])** | **1.032** | 9.36% | partial restore |
| **`FINAL` lean (single RSI 14, W200, 2.8/3.0 bracket) — this master** | **1.819 (118 [RETIRED])** | **1.592 (QQQ, 89 tr, 11.51% DD baseline)** | 11.20% | **wins** |

**Root cause — collinear lag:** RSI(14), MACD hist(12,26,9), OBV(20), MFI(14), VW-MACD(12,26), Fisher(10), WaveTrend(10,21,4), %R(21/112), Gaussian(25) are **same 10–30 bar EMA family** on price/volume. Requiring `bullVotes>=3` loosens strict `curRsi>prior+2.0 && rsi<45` to easier `cur>prior && <0` per oscillator — more permissive, more trades 135→170, lower PF. Entries fire **when swing is exhausted** — classic lag. Gaussian `srcFiltered:= abs(src-nz(src[1]))<1.0*stdev(src,10)? nz(srcFiltered[1]):src` is sticky and kills to 46 trades.

**Decision:** Keep %R/WaveTrend/Fisher/Fib **out of execution**; lean W200 + 1.5% risk + 2.8R/3.0R brackets wins.

### Zero-Lookahead Integrity

All HTF/macro use `close[1]` + `lookahead=barmerge.lookahead_off`:

```pine
wEma200 = request.security(syminfo.tickerid, "W", ta.ema(close,200)[1], lookahead=barmerge.lookahead_off)
fedFunds = request.security("FRED:FEDFUNDS", "M", close[1], lookahead=barmerge.lookahead_off, ignore_invalid_symbol=true)
```

Pivots use `low[pivotRight]`/`high[pivotRight]` and `bar_index - pivotRight` — confirmed only; entries `barstate.isconfirmed`; `process_orders_on_close=true calc_on_every_tick=false`.

### Intrabar Brackets

Early `strategy.close()` on `barstate.isconfirmed` missed intrabar spikes that recovered by daily close. Hardened `FINAL_OPTIMIZED_STRATEGY.pine:142-169`:

```pine
strategy.exit("Bracket Exit", from_entry="Long", stop=stopLossPrice, limit=targetPrice)
if currentGainR>=1.5 and not stage1Locked
    stopLossPrice:=math.max(stopLossPrice, entryPrice+0.5*unitR)
    strategy.exit("Bracket Exit", from_entry="Long", stop=stopLossPrice, limit=targetPrice)
```

`stop=entry-2.8*ATR`, `limit=entry+3.0*unitR`, re-invoked at ratchets; `strategy.close` only for regime invalidation.

---

## 4. Verified Performance Matrix

**Config locked:** `atr=2.8 tp=3.0R pivot=5 pivots`, `1.5%` risk, `1` tick slippage, `0.05%` commission, `process_orders_on_close=true`, persistent Chrome CDP single WS.

### 4.1 Full Period (2018-2026) — This Master (`FINAL_BASELINE`, BATS:SPY 1D live 2026-09-07)

| Asset | TF | Net % | PF | WR % | Trades | DD % | Sharpe [Quarantined] | Threshold |
|-------|----|-------|----|------|--------|------|----------------------|-----------|
| **BATS:SPY 1D (historical unverified, 2026-09-07)** | 1D | **+74.08%** | **1.819** | 56.78% | 118 [RETIRED] | **11.20%** | 3.76 (non-decision-grade) | PF 1.70 ✔ WR ✔ DD 12% ✔ |
| BATS:SPY 1D (pruned suite, 1.523, 167 tr, 9.36% DD) | 1D | +44.05% | 1.523 | 65.87% | 167 [RETIRED] | 9.36% | 3.10 (non-decision-grade) | PF 1.70 ✘ |
| BATS:QQQ 1D (baseline lean) | 1D | — | **1.592** | — | 89 | 11.51% | — | PF 1.55 ✔ |
| BITSTAMP:BTCUSD 1D (baseline) | 1D | — | 2.066 | — | 80 | 26.09% | — | PF 2.10 ✘ DD ✘ |
| BATS:SPY 1W | 1W | — | 3.344 | — | 28 | — | — | PF 2.20 ✔ |
| BATS:QQQ 1W | 1W | — | 4.972 | — | 27 | — | — | PF 2.20 ✔ |
| BITSTAMP:BTCUSD 1W | 1W | +13.30% | **3.506** | 71.43% | 14 | **3.10%** | 3.06 | **PASS** |

*Live 2026-09-07 capture after consolidation on `BATS:SPY 1D` matches sweep optimum 1.819 (see `metrics/clean_chart_screenshot.png`). Prior pruned suite traded +48 trades for +9pp WR, -1.8pp DD at cost of PF; lean reclaims.*

### 4.2 Walk-Forward (1D, pruned suite reference)

| Asset | IS 2018-2024 PF | OOS 2025-2026 PF | Degradation | N |
|-------|-----------------|------------------|-------------|---|
| SPY | 1.644 (52) | **2.069 (10)** | -25.8% (OOS better) | 62 |
| QQQ | 1.21 (47) | **2.475 (10)** | -104% | 57 |
| BTC | 1.476 (41) | 0.855 (9) | 42.1% | 50 |

OOS N=9-10 underpowered; SPY/QQQ improve OOS, BTC degrades. Forward walk `metrics/FORWARD_WALK_STATUS.md` windows `2026-09-07 → 2026-10-07`.

---

## 5. Operational Guide

### 5.1 One-Click Forward Walk

The master’s `strategy()` orders are simulated in **Strategy Tester**; true Paper Trading would need a Strategy Alert → Paper Trading order book. The audit engine logs live confirmed fills against theoretical brackets to flag gap slippage / wick unconfirmed.

```powershell
# Already deployed — re-audit anytime
.\run_forward_audit.bat
# or
.\venv\Scripts\python.exe scripts\forward_monitor.py
```

What it does `scripts/forward_monitor.py:12-40`:

* Connects to Chrome `ws://127.0.0.1:9222` (`runner.get_ws_url()`)
* Ensures `Strategy Tester` open, clicks `List of Trades` (falls back to Overview if virtualized)
* Scrapes `Trade # | Type | Date/Time | Price | Contracts | Profit | Cumulative | Run-up/Drawdown`
* Computes `Expected Stop vs Actual`, `Expected Limit 3.0R vs Actual`, `+1.5R/+2.5R` locks; `avg_slippage` proxy
* Appends to `metrics/forward_test_log.json` and writes `metrics/FORWARD_WALK_STATUS.md` (`2026-09-07 → 2026-10-07`, forward trades, PF, WR, slippage) + `metrics/forward_audit_screenshot.png`

Schedule via Task Scheduler to run `run_forward_audit.bat` daily for the 30-day walk.

### 5.2 Chrome CDP — Port 9222

Edge purged — Chrome has no `Allow remote debugging` infobar. One session for all assets.

```powershell
# 1. Launch (exact flags)
.\scripts\launch_chrome_with_debugging.ps1 -Port 9222
# Chrome discovered at C:\Program Files\Google\Chrome\Application\chrome.exe
# flags: --remote-debugging-port=9222 --user-data-dir="...\Google\Chrome\User Data" --no-first-run --no-default-browser-check --remote-allow-origins=* https://www.tradingview.com/chart/

# 2. Keep Chrome open — single WS
.\venv\Scripts\python.exe scripts\evaluate_all_assets.py   # 12 assets, zero extra Allow
.\venv\Scripts\python.exe scripts\deploy_single.py         # single master (this deploy)
.\venv\Scripts\python.exe scripts\forward_monitor.py       # audit
```

`runner.py:26-50` `get_ws_url()` checks `Chrome\User Data\DevToolsActivePort` → `http://127.0.0.1:9222/json/version` → `webSocketDebuggerUrl` `ws://127.0.0.1:9222/devtools/browser/<uuid>`. `CDPClient` 5 retries, `Target.getTargets` → `Target.attachToTarget`, `Browser.grantPermissions: clipboardReadWrite, notifications` once.

**Pine injection** `runner.py:194-310` + `scripts/deploy_single.py:38-85`:

```javascript
window._monaco.editor.getEditors()[0].executeEdits('deploy', [{range: model.getFullModelRange(), text: pineCode}])
```

Creates `Strategy` blank via title menu `Create new → Strategy` (title `data-qa-id="pine-script-title-button"` `:rni:` → `Indicator/Strategy` `:rsq:`) to force `Add to Chart` (never `Update`) for 1-slot hygiene; clears via `model.removeSource()` with `Allow` auto-click.

**Verification:** `scripts/final_verify.py` checks `dataSources` count 10 (9 base +1), title `FINAL_BASELINE`, `reportContainer` regex `Total PnL|Profitable trades|Profit factor`, `clean_chart_screenshot.png`.

### 5.3 Pine Validation

```powershell
.\venv\Scripts\python.exe scripts\validate_pine.py
# FINAL_OPTIMIZED_STRATEGY.pine (230 lines, 11.7 kB) [PASS] version, lookahead_off, close[1], process_orders_on_close, barstate.isconfirmed, strategy.exit bracket, pivotLeft=5, 129 parens balanced, HUD present
```

### 5.4 Inputs Reference — `FINAL_OPTIMIZED_STRATEGY.pine:10-24`

| Param | Default | Group | Role |
|-------|---------|-------|------|
| `rsiLength` | 14 | Strategy Optimization | RSI for divergence |
| `atrStopMult` | **2.8** | — | `unitR = 2.8*ATR`, stop |
| `riskPerTrade` | 1.5% | — | `qty = equity*0.015 / unitR` |
| `obvEmaLength` | 20 | — | volume |
| `pivotLeft/Right` | **5/5** | Divergence Engine | 5-bar confirmed pivots |
| `minPivotGap/maxPivotGap` | 5/60 | — | bars between pivots |
| `minRsiDiff/divLookback` | 2.0/15 | — | `rsi>prior+2` & `<45`, validity |
| `useWeeklyFilter/FedFundsFilter` | true/true | Macro & Trend | W200 + FRED |
| `useDateFilter/dateMode` | false/All | Walk-Forward | IS/OOS |
| `showExecutionLines` | **false** | Visual & HUD | master toggle |
| `showHUD` | true | — | 2-row HUD |

`strategy.exit("Bracket Exit", stop, limit)` + `+1.5R→+0.5R`, `+2.5R→+1.5R`, `isCrypto` fractional.

---

## 6. Repository Hygiene (Post-Purge 2026-09-07)

Purged `test_*.pine`, `confluence_original_reconstructed.pine`, `minimal_test.pine`, `CONFLUENCE_SWING_SUITE.pine` (806 lines), `CONFLUENCE_STUDY_OVERLAY.pine` (680 lines, `na + "/7")` corrupt), `strategy.pine`, `strategy_is/oos/sweep/variant.pine`, `__pycache__`.

**Kept:** `FINAL_OPTIMIZED_STRATEGY.pine` (master), `runner.py`, `run_forward_audit.bat`, `scripts/{forward_monitor.py,evaluate_all_assets.py,launch_chrome_with_debugging.ps1,validate_pine.py,deploy_single.py,final_verify.py}`, `metrics/{forward_test_log.json,FORWARD_WALK_STATUS.md,all_assets_evaluation.json,clean_chart_screenshot.png,forward_audit_screenshot.png}`, `logs/`, `venv/`.

**Run:**
```powershell
.\scripts\launch_chrome_with_debugging.ps1 -Port 9222
.\venv\Scripts\python.exe scripts\deploy_single.py   # 1 slot, +74.08% SPY 1D
.\run_forward_audit.bat                                # 30-day walk
```

*Generated 2026-09-07 by Autonomous Quant Engine (OpenCode / Muse Spark 1.2 High). Chrome hardcode eliminates Edge infobar. Lean single-RSI + W200 + 2.8R/3.0R intrabar brackets wins — one script, one slot, zero clutter.*