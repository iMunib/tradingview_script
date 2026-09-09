"""Diag: histogram of emitter X_CODE incl. 0, plus sample code-0 rows."""
import asyncio
import os
import sys
from collections import Counter

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)
import runner


async def main():
    client = runner.CDPClient(runner.get_ws_url())
    await client.connect()
    await client.find_tradingview_target()
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
            const rows = [];
            study._data.each((i, v) => { if (v && typeof v !== 'number') rows.push(v); });
            out.rows = rows;
        } catch(e) { out.err = String(e).slice(0,200); }
        return out;
    })()""")
    nplots = data["nplots"]
    base = nplots - 11
    codes = Counter()
    zeros = []
    for v in data["rows"]:
        c = v[1 + base]
        if c is None:
            continue
        codes[c] += 1
        if c == 0:
            zeros.append([v[1 + base + 1], v[1 + base + 2], v[1 + base + 6]])
    print("nplots:", nplots, "codes:", dict(codes), flush=True)
    print("code-0 sample (entry_t, exit_t, profit):", zeros[:10], flush=True)
    await client.close()


asyncio.run(main())
