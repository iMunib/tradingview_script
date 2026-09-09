"""Diag: sample bars where v[2] fires; print magnitudes."""
import asyncio
import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)
import runner


async def main():
    client = runner.CDPClient(runner.get_ws_url())
    await client.connect()
    await client.find_tradingview_target()
    info = await client.eval_js("""(() => {
        const out = {hits: [], distinct3: {}, distinct4: {}};
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
            let n = 0;
            study._data.each((i, v) => {
                if (!v || typeof v === 'number') return;
                const a = v[2], b = v[3], c = v[4];
                if (a !== null && a !== 0 && n < 5) { out.hits.push([v[0], a, b, c]); n++; }
                const k3 = String(b), k4 = String(c);
                out.distinct3[k3] = (out.distinct3[k3] || 0) + 1;
                out.distinct4[k4] = (out.distinct4[k4] || 0) + 1;
            });
        } catch(e) { out.err = String(e).slice(0,200); }
        return out;
    })()""")
    import json
    print(json.dumps(info)[:2000], flush=True)
    await client.close()


asyncio.run(main())
