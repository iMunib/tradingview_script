"""
Resume the AMTE-Precision 24-phase sweep from the incrementally-saved JSON.
Runs only the phases missing from metrics/all_assets_evaluation.json, using the
same persistent_pipeline + freshness gate as evaluate_all_assets.py, then merges
results back and recomputes the per-pair degradation keys + pooled summary.
"""
import os, sys, json, time, asyncio

sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

import runner
import evaluate_all_assets as eva

EVAL_RESULTS = eva.EVAL_RESULTS

with open(EVAL_RESULTS, encoding='utf-8') as f:
    all_data = json.load(f)

TASKS = [
    {"name": "SPY_1D_Full", "symbol": "BATS:SPY", "interval": "1D", "pine": eva.BASE_PINE, "sample": "Full Chart History"},
    {"name": "QQQ_1D_Full", "symbol": "BATS:QQQ", "interval": "1D", "pine": eva.BASE_PINE, "sample": "Full Chart History"},
    {"name": "BTCUSD_1D_Full", "symbol": "BITSTAMP:BTCUSD", "interval": "1D", "pine": eva.BASE_PINE, "sample": "Full Chart History"},
    {"name": "SPY_1W_Full", "symbol": "BATS:SPY", "interval": "1W", "pine": eva.BASE_PINE, "sample": "Full Chart History"},
    {"name": "QQQ_1W_Full", "symbol": "BATS:QQQ", "interval": "1W", "pine": eva.BASE_PINE, "sample": "Full Chart History"},
    {"name": "BTCUSD_1W_Full", "symbol": "BITSTAMP:BTCUSD", "interval": "1W", "pine": eva.BASE_PINE, "sample": "Full Chart History"},
    {"name": "SPY_1D_Full_2018_2026", "symbol": "BATS:SPY", "interval": "1D", "pine": eva.FULL_PINE, "sample": "Full Windowed (2018–2026)"},
    {"name": "QQQ_1D_Full_2018_2026", "symbol": "BATS:QQQ", "interval": "1D", "pine": eva.FULL_PINE, "sample": "Full Windowed (2018–2026)"},
    {"name": "BTCUSD_1D_Full_2018_2026", "symbol": "BITSTAMP:BTCUSD", "interval": "1D", "pine": eva.FULL_PINE, "sample": "Full Windowed (2018–2026)"},
    {"name": "SPY_1W_Full_2018_2026", "symbol": "BATS:SPY", "interval": "1W", "pine": eva.FULL_PINE, "sample": "Full Windowed (2018–2026)"},
    {"name": "QQQ_1W_Full_2018_2026", "symbol": "BATS:QQQ", "interval": "1W", "pine": eva.FULL_PINE, "sample": "Full Windowed (2018–2026)"},
    {"name": "BTCUSD_1W_Full_2018_2026", "symbol": "BITSTAMP:BTCUSD", "interval": "1W", "pine": eva.FULL_PINE, "sample": "Full Windowed (2018–2026)"},
    {"name": "SPY_1D_IS", "symbol": "BATS:SPY", "interval": "1D", "pine": eva.IS_PINE, "sample": "In-Sample (2018–2024)"},
    {"name": "QQQ_1D_IS", "symbol": "BATS:QQQ", "interval": "1D", "pine": eva.IS_PINE, "sample": "In-Sample (2018–2024)"},
    {"name": "BTCUSD_1D_IS", "symbol": "BITSTAMP:BTCUSD", "interval": "1D", "pine": eva.IS_PINE, "sample": "In-Sample (2018–2024)"},
    {"name": "SPY_1W_IS", "symbol": "BATS:SPY", "interval": "1W", "pine": eva.IS_PINE, "sample": "In-Sample (2018–2024)"},
    {"name": "QQQ_1W_IS", "symbol": "BATS:QQQ", "interval": "1W", "pine": eva.IS_PINE, "sample": "In-Sample (2018–2024)"},
    {"name": "BTCUSD_1W_IS", "symbol": "BITSTAMP:BTCUSD", "interval": "1W", "pine": eva.IS_PINE, "sample": "In-Sample (2018–2024)"},
    {"name": "SPY_1D_OOS", "symbol": "BATS:SPY", "interval": "1D", "pine": eva.OOS_PINE, "sample": "Out-of-Sample (2025–2026)"},
    {"name": "QQQ_1D_OOS", "symbol": "BATS:QQQ", "interval": "1D", "pine": eva.OOS_PINE, "sample": "Out-of-Sample (2025–2026)"},
    {"name": "BTCUSD_1D_OOS", "symbol": "BITSTAMP:BTCUSD", "interval": "1D", "pine": eva.OOS_PINE, "sample": "Out-of-Sample (2025–2026)"},
    {"name": "SPY_1W_OOS", "symbol": "BATS:SPY", "interval": "1W", "pine": eva.OOS_PINE, "sample": "Out-of-Sample (2025–2026)"},
    {"name": "QQQ_1W_OOS", "symbol": "BATS:QQQ", "interval": "1W", "pine": eva.OOS_PINE, "sample": "Out-of-Sample (2025–2026)"},
    {"name": "BTCUSD_1W_OOS", "symbol": "BITSTAMP:BTCUSD", "interval": "1W", "pine": eva.OOS_PINE, "sample": "Out-of-Sample (2025–2026)"},
]

PAIRS = [
    ("SPY_1D", "SPY_1D_IS", "SPY_1D_OOS"),
    ("QQQ_1D", "QQQ_1D_IS", "QQQ_1D_OOS"),
    ("BTCUSD_1D", "BTCUSD_1D_IS", "BTCUSD_1D_OOS"),
    ("SPY_1W", "SPY_1W_IS", "SPY_1W_OOS"),
    ("QQQ_1W", "QQQ_1W_IS", "QQQ_1W_OOS"),
    ("BTCUSD_1W", "BTCUSD_1W_IS", "BTCUSD_1W_OOS"),
]


def recompute_degradation(all_data):
    for label, is_k, oos_k in PAIRS:
        is_rec = all_data.get(is_k, {})
        oos_rec = all_data.get(oos_k, {})
        pf_is = is_rec.get("profit_factor") if isinstance(is_rec, dict) else None
        pf_oos = oos_rec.get("profit_factor") if isinstance(oos_rec, dict) else None
        if pf_is and pf_oos:
            all_data["%s_degradation_pct" % label] = round(((pf_is - pf_oos) / pf_is) * 100.0, 2)


async def main():
    eva.ensure_browser()
    client = runner.CDPClient(runner.get_ws_url())
    await client.connect()
    await client.find_tradingview_target()
    try:
        await client.send_cmd('Browser.grantPermissions', {'permissions': ['clipboardReadWrite', 'notifications'], 'origin': 'https://www.tradingview.com'})
    except Exception:
        pass

    missing = [t for t in TASKS if t["name"] not in all_data]
    print('[RESUME] %d phases already complete, %d to run:' % (len(TASKS) - len(missing), len(missing)))
    for t in missing:
        print('  -', t['name'])

    for t in missing:
        try:
            print('\n>>>>>>>>>> PHASE %s <<<<<<<<<<' % t['name'])
            out = await eva.persistent_pipeline(client, t['pine'], t['symbol'], t['interval'], wait_sec=6)
            if out:
                rec = {"symbol": t['symbol'], "interval": t['interval'], "sample": t['sample'],
                       "net_profit_pct": out.get("net_profit_pct"), "net_profit_raw": out.get("net_profit_raw"),
                       "profit_factor": out.get("profit_factor"), "max_drawdown_pct": out.get("max_drawdown_pct"),
                       "max_drawdown_raw": out.get("max_drawdown_raw"), "win_rate_pct": out.get("win_rate_pct"),
                       "winning_trades": out.get("winning_trades"), "total_closed_trades": out.get("total_closed_trades"),
                       "sharpe_ratio": out.get("sharpe_ratio")}
                all_data[t['name']] = rec
                recompute_degradation(all_data)
                print('Completed %s: PF %s DD %s WR %s Trades %s' % (t['name'], rec['profit_factor'], rec['max_drawdown_pct'], rec['win_rate_pct'], rec['total_closed_trades']))
            else:
                print('Failed %s (no metrics)' % t['name'])
                all_data[t['name']] = {"status": "failed"}
        except Exception as e:
            print('[FAIL] %s -> %r' % (t['name'], e))
            all_data[t['name']] = {"status": "failed", "error": repr(e)}
        with open(EVAL_RESULTS, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, indent=2)
        await asyncio.sleep(1.5)

    recompute_degradation(all_data)
    with open(EVAL_RESULTS, 'w', encoding='utf-8') as f:
        json.dump(all_data, f, indent=2)
    print('\n[RESUME DONE] %s' % EVAL_RESULTS)
    await client.close()


if __name__ == '__main__':
    asyncio.run(main())
