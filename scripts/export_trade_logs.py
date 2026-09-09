"""Trade-log CSV export engine (Phase 2).

Architecture (adapted to observed paywall reality — documented in TOOLING.md):
  * Primary route (spec): native "Export CSV" button — PROBED ABSENT (120 buttons
    scanned, none match export/download/csv; Strategy report tabs show
    "Upgrade to get full access"). Logged as unavailable, not silently skipped.
  * Active route (spec's Secondary, Pine Native Emission): a temporary variant
    = variant source + scripts/emitter_block.pine (11 X_ plots, exit bars only)
    is injected; full history is backfilled via synthetic wheel scroll; ONE CDP
    evaluate reads the strategy study's per-bar plot values; Python dedups
    (exit_time, entry_time, profit), maps reason codes, and writes
    metrics/trade_log_<asset>_<period>.csv with columns:
    trade_num,entry_date,exit_date,entry_price,exit_price,profit_usd,
    profit_pct,exit_reason,r_multiple,runup_pct,drawdown_pct

Covers 6 core asset/TF cells x Full/IS/OOS = 18 CSVs. History is loaded ONCE
per asset/TF (scroll to earliest), then the 3 period variants are injected
back-to-back with no symbol switch in between.

Usage: python scripts/export_trade_logs.py [--only SPY_1D_Full] [--skip-scroll]
Cross-checks N and recomputed PF against metrics/all_assets_evaluation.json.
"""
import asyncio
import csv
import datetime as dt
import json
import os
import sys
import time

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)
import runner

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)

EMIT_DIR = os.path.join(ROOT_DIR, ".emit_tmp")
METRICS = os.path.join(ROOT_DIR, "metrics")
EMITTER = os.path.join(ROOT_DIR, "scripts", "emitter_block.pine")

VARIANTS = {
    # "Full" JSON cells were swept with the MASTER (useDateFilter=false =
    # unconstrained full chart history). strategy_full.pine is the WINDOWED
    # 2018-2026 variant (inTradeWindow=[2018,2026]), NOT the Full cell.
    "Full": os.path.join(ROOT_DIR, "FINAL_OPTIMIZED_STRATEGY.pine"),
    "IS": os.path.join(ROOT_DIR, "strategy_is.pine"),
    "OOS": os.path.join(ROOT_DIR, "strategy_oos.pine"),
}
# (key_prefix, symbol, interval, earliest_epoch_needed)
CELLS = [
    ("SPY_1D", "BATS:SPY", "1D", 725846400),      # 1993-01-01
    ("QQQ_1D", "BATS:QQQ", "1D", 915148800),      # 1999-01-01
    ("BTCUSD_1D", "BITSTAMP:BTCUSD", "1D", 1314835200),  # 2011-09-01 (exchange data start; warmup needs pre-2015)
    ("SPY_1W", "BATS:SPY", "1W", 725846400),
    ("QQQ_1W", "BATS:QQQ", "1W", 915148800),
    ("BTCUSD_1W", "BITSTAMP:BTCUSD", "1W", 1314835200),
]
CODE2REASON = {1: "TARGET", 2: "STOP", 3: "STRONG", 4: "REVERSAL", 5: "WINDOW", 0: "UNKNOWN"}


def build_emitter(variant_path, tag):
    with open(variant_path, encoding="utf-8") as f:
        code = f.read()
    with open(EMITTER, encoding="utf-8") as f:
        block = f.read()
    os.makedirs(EMIT_DIR, exist_ok=True)
    path = os.path.join(EMIT_DIR, f"emit_{tag}.pine")
    with open(path, "w", encoding="utf-8") as f:
        f.write(code + "\n" + block + "\n")
    return path


async def switch_symbol(client, symbol, interval):
    js = f"""(() => {{
        const coll = window._exposed_chartWidgetCollection;
        const widget = coll && coll.activeChartWidget ? coll.activeChartWidget.value() : null;
        if (!widget || !widget.hasModel()) return {{success: false}};
        const model = widget.model();
        const series = model.mainSeries();
        model.setSymbol(series, '{symbol}');
        model.setResolution(series, '{interval}');
        return {{success: true}};
    }})()"""
    await client.eval_js(js)
    await asyncio.sleep(2.0)


async def inject_pine(client, pine_code):
    code_json = json.dumps(pine_code)
    # ensure editor visible
    await client.eval_js("""(() => {
        const monacoEl = document.querySelector('.monaco-editor');
        if (!(monacoEl && monacoEl.offsetParent !== null)) {
            const b = document.querySelector('[data-name="pine-dialog-button"]') ||
                Array.from(document.querySelectorAll('button')).find(x => /pine editor/i.test((x.innerText||'')));
            if (b) b.click();
        }
        return true;
    })()""")
    await asyncio.sleep(1.0)
    inj = await client.eval_js(f"""(() => {{
        if (!window._monaco) return {{success: false}};
        const eds = window._monaco.editor.getEditors();
        const ed = eds && eds.length ? eds[0] : null;
        if (!ed) return {{success: false}};
        const m = ed.getModel();
        ed.executeEdits('export', [{{range: m.getFullModelRange(), text: {code_json}, forceMoveMarkers: true}}]);
        ed.pushUndoStop(); ed.focus();
        return {{success: true}};
    }})()""")
    if not inj.get("success"):
        raise RuntimeError("Monaco inject failed")
    await asyncio.sleep(0.5)
    pre_snap = await client.eval_js("""(() => {
        const r = document.querySelector('[class*="reportContainer-"]');
        return r ? r.innerText : '';
    })()""")
    await client.eval_js("""(() => {
        const all = Array.from(document.querySelectorAll('button'));
        const byTitle = (re) => all.find(b => re.test(b.getAttribute('title')||''));
        const byText = (re) => all.find(b => re.test(b.innerText||''));
        const add = byTitle(/add to chart/i) || byText(/add to chart/i);
        const upd = byTitle(/update on chart/i) || byText(/update on chart/i);
        if (add && !add.disabled && add.offsetParent !== null) add.click();
        else if (upd && !upd.disabled && upd.offsetParent !== null) upd.click();
        return true;
    })()""")
    # wait compile: Monaco markers + report Caution scan + FRESH report (differs from pre-click)
    for _ in range(45):
        await asyncio.sleep(1.0)
        errs = await client.eval_js("""(() => {
            try {
                if (!window._monaco || !window._monaco.editor) return [];
                const ms = window._monaco.editor.getModels();
                const tm = ms.find(m => m.uri.toString().includes('placement=dialog')) || ms[0];
                if (!tm) return [];
                return window._monaco.editor.getModelMarkers({resource: tm.uri})
                    .filter(m => m.severity === 8).map(m => m.message);
            } catch(e) { return []; }
        })()""")
        if errs:
            raise RuntimeError("Pine compile errors: " + str(errs[:3]))
        rep = await client.eval_js("""(() => {
            const r = document.querySelector('[class*="reportContainer-"]');
            return r ? r.innerText.slice(0, 400) : '';
        })()""")
        if "Caution!" in rep or "cannot call" in rep:
            raise RuntimeError("Report-pane error: " + rep[:300])
        if rep != (pre_snap or "")[:400] and ("Profit factor" in rep or "Profitable trades" in rep):
            break
    await asyncio.sleep(6.0)


async def backfill_history(client, earliest, max_batches=220, need_stable=8):
    stable = 0
    last_first = None
    for b in range(max_batches):
        await client.eval_js("""(() => {
            const c = document.querySelector('canvas[data-name="pane-canvas"]') ||
                      document.querySelectorAll('canvas')[0];
            const r = c.getBoundingClientRect();
            const cx = r.x + r.width/2, cy = r.y + r.height/2;
            c.dispatchEvent(new MouseEvent('mousemove', {bubbles: true, clientX: cx, clientY: cy}));
            const ev = new WheelEvent('wheel', {bubbles: true, cancelable: true,
                clientX: cx, clientY: cy, deltaX: -2000, deltaY: 0, deltaMode: 0});
            (document.elementFromPoint(cx, cy) || c).dispatchEvent(ev);
            return true;
        })()""")
        await asyncio.sleep(1.0)
        st = await client.eval_js("""(() => {
            const m = window._exposed_chartWidgetCollection.activeChartWidget.value().model();
            const ms = m.mainSeries();
            let ft = 0;
            try { ft = ms.bars().valueAt(ms.bars().firstIndex())[0]; } catch(e) {}
            return {first: ms.bars().firstIndex(), last: ms.bars().lastIndex(), firstTime: ft};
        })()""")
        ft = st.get("firstTime") or 0
        if ft and ft <= earliest:
            return st
        if st.get("first") == last_first:
            stable += 1
            if stable >= need_stable:
                # one long settle: deep-history chunks can arrive late
                await asyncio.sleep(8.0)
                st2 = await client.eval_js("""(() => {
                    const m = window._exposed_chartWidgetCollection.activeChartWidget.value().model();
                    const ms = m.mainSeries();
                    let ft = 0;
                    try { ft = ms.bars().valueAt(ms.bars().firstIndex())[0]; } catch(e) {}
                    return {first: ms.bars().firstIndex(), last: ms.bars().lastIndex(), firstTime: ft};
                })()""")
                if st2.get("first") == last_first:
                    return st2
                stable = 0
                last_first = st2.get("first")
        else:
            stable = 0
            last_first = st.get("first")
    return st


async def read_emitter(client, settle_sec=25):
    """One evaluate per poll: all bars of the strategy study's plot vectors.
    Waits until the study cache is populated and stable (recalc after inject)."""
    last_n = -1
    stable = 0
    data = {"rows": [], "nplots": 0}
    for _ in range(settle_sec):
        data = await client.eval_js("""(() => {
            const out = {rows: [], nplots: 0};
            try {
                const coll = window._exposed_chartWidgetCollection;
                const model = coll.activeChartWidget.value().model();
                let study = null, best = -1;
                for (const p of model.panes()) for (const s of p.dataSources()) {
                    let t = '';
                    try { t = s.title ? s.title() : ''; } catch(e) {}
                    if (String(t).includes('FINAL_UCSv3')) {
                        let n = 0;
                        try { n = s.metaInfo().plots.length; } catch(e) {}
                        if (n > best) { best = n; study = s; }
                    }
                }
                if (!study) { out.err = 'study not found'; return out; }
                out.nplots = best;
                const d = study._data;
                const rows = [];
                d.each((i, v) => { if (v && typeof v !== 'number') rows.push(v); });
                out.rows = rows;
            } catch(e) { out.err = String(e).slice(0,200); }
            return out;
        })()""")
        if data.get("err"):
            return data
        n = len(data.get("rows", []))
        if n > 0 and n == last_n:
            stable += 1
            if stable >= 3:
                return data
        else:
            stable = 0
            last_n = n
        await asyncio.sleep(1.0)
    return data


def rows_to_trades(rows, nplots):
    # emitter plots are the LAST 12 of nplots (2 plots + 7 shapes + 12 emitter + X_JUST)
    assert nplots >= 21, f"expected >=21 plots, got {nplots}"
    base = nplots - 12  # index offset within value array (value[0] = time)
    trades = []
    for v in rows:
        code = v[1 + base]
        if code is None or code == 0:
            continue
        rec = {
            "code": int(code),
            "entry_t": v[1 + base + 1], "exit_t": v[1 + base + 2],
            "entry_p": v[1 + base + 3], "exit_p": v[1 + base + 4],
            "qty": v[1 + base + 5], "profit": v[1 + base + 6],
            "r": v[1 + base + 7], "run": v[1 + base + 8], "dd": v[1 + base + 9],
        }
        if None in (rec["entry_t"], rec["exit_t"], rec["profit"]):
            continue
        trades.append(rec)
    # X_JUST diagnostic: raw count of position-transition bars (index base+11)
    just_n = 0
    for v in rows:
        try:
            j = v[1 + base + 11]
        except IndexError:
            j = None
        if j == 1:
            just_n += 1
    print(f"  X_JUST bars={just_n}", flush=True)
    # dedup (exit bar + exit bar+1 double emission) on (exit_t, entry_t, profit)
    seen, uniq = set(), []
    for t in sorted(trades, key=lambda r: (r["exit_t"], r["entry_t"])):
        k = (t["exit_t"], t["entry_t"], round(t["profit"], 2))
        if k not in seen:
            seen.add(k)
            uniq.append(t)
    print(f"  raw emissions={len(trades)} unique={len(uniq)}", flush=True)
    return uniq


def write_csv(path, trades):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["trade_num", "entry_date", "exit_date", "entry_price",
                    "exit_price", "profit_usd", "profit_pct", "exit_reason",
                    "r_multiple", "runup_pct", "drawdown_pct"])
        for i, t in enumerate(trades, 1):
            notional = (t["entry_p"] or 0) * (t["qty"] or 0)
            pct = (t["profit"] / notional * 100.0) if notional else 0.0
            w.writerow([
                i,
                dt.datetime.fromtimestamp(t["entry_t"] / 1000, dt.timezone.utc).strftime("%Y-%m-%d"),
                dt.datetime.fromtimestamp(t["exit_t"] / 1000, dt.timezone.utc).strftime("%Y-%m-%d"),
                round(t["entry_p"], 2) if t["entry_p"] else "",
                round(t["exit_p"], 2) if t["exit_p"] else "",
                round(t["profit"], 2),
                round(pct, 3),
                CODE2REASON.get(t["code"], "UNKNOWN"),
                round(t["r"], 3) if t["r"] is not None else "",
                round(t["run"], 3) if t["run"] is not None else "",
                round(t["dd"], 3) if t["dd"] is not None else "",
            ])
    return len(trades)


async def main():
    only = None
    for a in sys.argv[1:]:
        if a.startswith("--only"):
            only = a.split("=", 1)[1] if "=" in a else sys.argv[sys.argv.index(a) + 1]
    skip_scroll = "--skip-scroll" in sys.argv
    baseline = {}
    bp = os.path.join(METRICS, "all_assets_evaluation.json")
    if os.path.exists(bp):
        baseline = json.load(open(bp, encoding="utf-8"))
    ws_url = runner.get_ws_url()
    client = runner.CDPClient(ws_url)
    await client.connect()
    await client.find_tradingview_target()
    summary = []
    for prefix, symbol, interval, earliest in CELLS:
        jobs = [(p, VARIANTS[p]) for p in ("Full", "IS", "OOS")
                if (only is None or f"{prefix}_{p}" == only)]
        if not jobs:
            continue
        print(f"\n=== {prefix} {symbol} {interval} ===", flush=True)
        await switch_symbol(client, symbol, interval)
        if not skip_scroll:
            st = await backfill_history(client, earliest)
            print(f"history: first={st.get('first')} last={st.get('last')} "
                  f"firstTime={st.get('firstTime')}", flush=True)
        for period, vpath in jobs:
            tag = f"{prefix}_{period}"
            epath = build_emitter(vpath, tag)
            with open(epath, encoding="utf-8") as f:
                code = f.read()
            t0 = time.time()
            await inject_pine(client, code)
            data = await read_emitter(client)
            if data.get("err"):
                print(f"{tag}: READ ERR {data['err']}", flush=True)
                continue
            trades = rows_to_trades(data["rows"], data["nplots"])
            outp = os.path.join(METRICS, f"trade_log_{tag}.csv")
            n = write_csv(outp, trades)
            gp = sum(t["profit"] for t in trades if t["profit"] > 0)
            gl = -sum(t["profit"] for t in trades if t["profit"] < 0)
            pf = round(gp / gl, 3) if gl > 0 else None
            b = baseline.get(tag, {})
            print(f"{tag}: N={n} PF_recomputed={pf} "
                  f"| JSON N={b.get('total_closed_trades')} PF={b.get('profit_factor')} "
                  f"DD={b.get('max_drawdown_pct')} "
                  f"({time.time()-t0:.0f}s, plots={data['nplots']}, rawrows={len(data['rows'])})",
                  flush=True)
            summary.append((tag, n, pf, b.get("total_closed_trades"), b.get("profit_factor")))
            await asyncio.sleep(2.0)
    await client.close()
    print("\n=== SUMMARY ===")
    for tag, n, pf, jn, jpf in summary:
        match = "MATCH" if (n == jn and (pf == jpf or (pf is None and jpf is None))) else "MISMATCH"
        print(f"{tag}: csv N={n} PF={pf} | json N={jn} PF={jpf} -> {match}")


if __name__ == "__main__":
    asyncio.run(main())
