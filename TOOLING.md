# TOOLING — scripts, CLIs, CDP harness methods (active / retired)

## Extraction architecture (Phase 2 research record)

Probed 2026-09-09 (scripts `probe_tester*.py`, `probe_study*.py`, `probe_scroll*.py`, `probe_range.py`):
- Native Strategy-Tester "Export CSV" button: ABSENT (120 buttons scanned, none match export/download/csv; report tabs show "Upgrade to get full access to Strategy r[eports]"). Primary route per spec unavailable — logged, not silently skipped.
- "List of Trades" / "Performance Summary" DOM tabs: ABSENT (paywalled; only Overview + Performance chart tabs render). DOM-scrape route impossible.
- Working channel (spec's Pine Native Emission): strategy study object is reachable in the chart model (`activeChartWidget.model()` panes → dataSource titled `FINAL_UCSv3`), with `metaInfo().plots` and per-bar vectors via `_data.valueAt(i)` / `_data.each((i, v) => …)` (note: index-first callback args). Emitter block (`scripts/emitter_block.pine`) plots 12 X_ series on exit bars; Python reads + dedups on (exit_time, entry_time, profit).
- Full-history backfill: `setVisibleTimeRange` is a not-implemented stub on this widget build; synthetic `WheelEvent` dispatch on the pane canvas extends the cache (~280 bars/2.4s; SPY 1D to Jan 1993 verified `firstTime=728317800`).
- `Input.dispatchMouseEvent` is unsupported on this CDP session (use JS event dispatch, not the Input domain).
- Compile-error detection must ALSO scan the report pane ("Caution! …", e.g. `nz()` rejects strings — caught live this session) because Monaco-marker lookup can miss; `scripts/compile_check.py` does both.

## Active

| Tool | Purpose | Status this session |
|---|---|---|
| `scripts/evaluate_all_assets.py` | 24-cell CDP sweep (single WS): variant regen + inject + overview scrape → `metrics/all_assets_evaluation.json` + degradation + pooled summary (pooled numbers retained in file, NOT used for verdicts) | Read/reused (`persistent_pipeline`, `ensure_browser`); not re-run (baselines stand) |
| `scripts/make_variants.py` | Generates `strategy_full/is/oos.pine` from master (date-block only) | Run; diff-verified 29 lines each |
| `scripts/compile_check.py` | Compile (+metrics) check of a Pine file; hardened with report-pane error scan | Run — COMPILE_OK; SPY 1D Full repro identical |
| `scripts/check_no_repaint.py` + `.git/hooks/pre-commit` | Asserts `lookahead_off` non-decreasing, all `request.security()` covered | Run — PASS (4→4); hook blocked nothing (nothing regressed) |
| `scripts/export_trade_logs.py` + `scripts/emitter_block.pine` | Trade-log CSV engine: emitter-temp-variant inject → scroll backfill → model read → 18 CSVs + JSON cross-check | Run — 18 CSVs written (13 exact MATCH, 5 bounded engine-delta, audit H8) |
| `scripts/run_phase3.py` | `--suite cooldown` (minCooldownBars 3/5/8/13 × 6 Full) / `sizing` (fixed 100k base × 6) / `walkfwd` (5 spec windows × 6 × train/test) | Run — `metrics/phase3_sweep.json` (30 runs), `metrics/walkforward_windows.csv` (30 rows) |
| `scripts/run_ablation.py` | Leave-one-out over 8 present indicators × 6 cells × Full + W5-test → `metrics/indicator_ablation_results.csv` (120 rows incl. baselines + WaveTrend-absent rows) | Run — 96 excluded-cell runs |
| `scripts/stats_validation.py` | Block-bootstrap (10-trade blocks, 2000 resamples, seed 7) 90% PF CI + sign-flip permutation null + maxDD proxy; `profit_usd` alias added | Run on Full + IS logs |
| `scripts/verify_visuals.py` (+ `diag_mag.py`, `diag_plots.py`) | Counts shape-plot firings per class from chart model; cross-checks CSV exit reasons | Run — §4 verification (found + documented STOP×2 emission, entry over-plot) |
| `scripts/diag_chart.py` | Chart-state dump (symbol/interval/sources/report head) | Run — caught the `nz(string)` compile failure + stale-strategy state |
| `scripts/run_generalization.py` | **New (this session).** Out-of-basket sweep: DIA/IWM/AAPL/MSFT/ETHUSD × Full/IS/OOS 1D via current master/IS/OOS variants → `metrics/generalization.json` | **Run** — 15 cells: MSFT PF 1.531 sole pass; DIA 0.775, IWM 0.663, AAPL 0.611 powered FAILs; ETH N=12 low-N |
| `runner.py` (`CDPClient`, `get_ws_url`) | CDP transport on `ws://127.0.0.1:9222` | Used throughout; browser stayed up all session |
| `git` | version control | Used throughout (`fetch`/`pull --rebase` + push with output shown) |

## Retired this session (excised from master per evidence — see audit H10)

CMF-20 calculation + `cmf>0.05` absorption legs (ablation sens ~0, five exact 0.0); FRED:PERMIT security call + `permitsSlope` + housing macroGate leg (sens 0.0 crypto / weak-inconsistent equities + publication lag); 3-stage ratchet 0.90→+0.05/1.60→+0.80/2.40→+1.65 and +3.0R/+3.45R decorative targets (0 fills in 210 trades); ungated entry shapes + 2-bar TARGET/STOP emission (H9). Scoped Donchian `qqqBreakout` RETAINED (never ablated; removal unevidenced).

## Retired / forensic (kept for audit trail; do not extend)

`scripts/probe_tester.py`, `probe_tester2/3/4.py`, `probe_study.py`, `probe_study2/3.py`, `probe_scroll.py`, `probe_scroll2/3.py`, `probe_range.py`, `diag_emit.py`, `diag_emit2/3.py`, `diag_code0.py` — one-shot DOM/model probes whose findings are condensed above. `scripts/run_walkforward.py` — superseded by `run_phase3.py --suite walkfwd` (spec windows); `scripts/run_baseline_check.py`, `run_oos_check.py`, `quick_test.py`, `test_matrix.py`, `diagnose_tasks_bc.py`, `resume_prec.py`, `test_macro_d200.py`, `eval_full_comparison.py`, `inspect_live.py` — prior diagnostic sprawl. `baseline_pure.pine`, `test_strategy.pine`, `metrics/backtest_history.json`, `baseline_history_backup_*.json`, `diag_tasks_bc.json`, `.diag_tmp/`, `.openclaw/`, `logs/`, `__pycache__/` — untracked noise, never committed.

## Pending (specified, not built)

Per-trade List-of-Trades DOM export (needs paid plan); intrabar-grain fill-sequencing audit for the H8 residual (needs tick data); 10+ untuned-ticker generalization run (5-ticker H5 run done this session: 1/5 pass — full 10+ still open); entry-vote vs exit-trigger split ablations (Fisher/RSI/VolPct/MACD); re-run of walk-forward + ablation suites against the CURRENT master (`run_phase3.py`/`run_ablation.py` transforms reference excised CMF/PERMIT code — update before reuse; their committed CSVs are stale-arch).

Note: `run_phase3.py` and `run_ablation.py` rows above describe the prior-architecture runs; artifacts superseded by this session's sweep/trade-logs/generalization until re-run.
