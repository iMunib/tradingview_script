"""Diag: dump study plot id/title order + sample values for indices 2,3,4."""
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
        const out = {};
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
            out.plots = study.metaInfo().plots.map(p => ({id: p.id, title: p.title || ''}));
            const samp = {};
            let n = 0;
            study._data.each((i, v) => {
                if (!v || typeof v === 'number' || n >= 3) return;
                // find first 3 bars where index2 nonzero
                if (v[2] !== null && v[2] !== 0) { samp['bar' + n] = v.slice(0, 10); n++; }
            });
            out.samples = samp;
        } catch(e) { out.err = String(e).slice(0,200); }
        return out;
    })()""")
    import json
    print(json.dumps(info, indent=1)[:2500], flush=True)
    await client.close()


asyncio.run(main())
