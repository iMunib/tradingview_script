# TOOLING — scripts, CLIs, automation targets (active / retired)

## Active

| Tool | Purpose | Invoked this session? |
|---|---|---|
| `scripts/evaluate_all_assets.py` | 24-cell CDP sweep (single WS): injects Pine per symbol/TF, scrapes Strategy Tester overview, writes `metrics/all_assets_evaluation.json` + degradation + pooled summary. Contains `generate_partitioned_files()` (regenerates variants at sweep start) and `persistent_pipeline()` (inject + compile-check + scrape) | Read (full, 654 lines); `persistent_pipeline` reused by `compile_check.py` for live verify 18:09 UTC |
| `scripts/make_variants.py` | Generates `strategy_full/is/oos.pine` from master (date-block regex only) | Read + **run** (regenerated post-fix variants; diff-verified date-only) |
| `scripts/compile_check.py` | **New.** Compile-only live check of a Pine file (inject + Monaco severity-8 markers, no JSON writes) | **Run** — `COMPILE_OK`, SPY 1D Full repro identical |
| `scripts/check_no_repaint.py` | **New.** Asserts `lookahead_off` count non-decreasing vs HEAD and every `request.security()` carries it | **Run** — PASS (4→4) |
| `.git/hooks/pre-commit` | **New** (local, uncommitted by git design). Runs the repaint guard; blocks weakening commits | Installed; collaborators must copy from `scripts/check_no_repaint.py` docs |
| `scripts/run_walkforward.py` | **New.** Walk-forward runner: 5 test windows (2022–2026YTD) × train windows, reuses `persistent_pipeline`; writes `metrics/walkforward_windows.csv` | Written, **not yet run** (needs ~60-cell CDP sweep) |
| `scripts/stats_validation.py` | **New.** Block-bootstrap 90% CI on PF/maxDD + permutation null test; operates on `metrics/trade_log_<asset>_<period>.csv` | Written, **blocked** (no trade logs yet) |
| `runner.py` (`CDPClient`, `get_ws_url`) | CDP transport; browser WS on `ws://127.0.0.1:9222` | Used via imports; browser confirmed listening |
| `git` | version control; `git pull --rebase` done pre-work (`fetch`: origin/main = 0cfe809, no new remote) | Used throughout |

## Retired / dead (do not use)

| Tool | Status |
|---|---|
| `baseline_pure.pine` (233 lines, Single-RSI FINAL_BASELINE) | Untracked leftover; superseded by UCS v3 master. Retire (delete or archive) after review |
| `test_strategy.pine` (268 lines, Dual-Swing experiment) | Untracked experiment; not referenced by evaluator. Retire after review |
| `scripts/diagnose_tasks_bc.py`, `quick_test.py`, `test_matrix.py`, `resume_prec.py`, `run_baseline_check.py`, `run_oos_check.py`, `test_macro_d200.py`, `eval_full_comparison.py`, `inspect_live.py` | Same-day diagnostic sprawl (commit 26f2b88); unneeded for the mandated protocol. Keep for forensics, do not extend |
| `metrics/backtest_history.json` (741 rows), `baseline_history_backup_*.json`, `diag_tasks_bc.json`, `test_matrix_results.json`, `all_assets_evaluation_truncated_1604.json` | Forensic backups, not sources for any verdict in PERFORMANCE_AUDIT.md |
| `.diag_tmp/`, `.openclaw/`, `__pycache__/`, `logs/` (15 same-day eval logs) | Workspace noise; `logs/compiler_errors.log` is the only live log |

## Browser-automation targets (TradingView chart `9PftNvuy`)

Chart model API (`setSymbol`/`setResolution`), Monaco editor injection, "Add to chart"/"Update on chart" click, Strategy Tester report scrape (`Total PnL`, `Profitable trades`, `Profit factor`, `Max drawdown`). No trade-list (per-trade) export exists yet — required spec for unblocking trade logs: one row per closed trade with entry/exit datetime, entry/exit price, qty, P&L, and exit-reason comment (`Strong Exit` / `Exit Reversal` / `Exit Target` / `Exit Stop` / `Window End`), exported to `metrics/trade_log_<asset>_<period>.csv`.
