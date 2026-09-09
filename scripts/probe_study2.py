"""Probe 6: study _data access shape for per-bar plot values + time mapping."""
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
            let study = null;
            for (const p of model.panes()) for (const s of p.dataSources()) {
                let t = '';
                try { t = s.title ? s.title() : ''; } catch(e) {}
                if (String(t).includes('FINAL_UCSv3')) study = s;
            }
            if (!study) return {err: 'study not found'};
            const d = study._data;
            out.dataCtor = d.constructor ? d.constructor.name : '?';
            out.dataMethods = Object.getOwnPropertyNames(Object.getPrototypeOf(d)).slice(0,40);
            // try size/length
            for (const k of ['size','length','bars','count']) {
                try { const v = d[k]; out[k] = typeof v === 'function' ? v.call(d) : v; }
                catch(e) { out[k] = 'ERR'; }
            }
            // try get(0)/get last
            const n = out.size || out.length || 0;
            out.n = n;
            for (const idx of [0, 1, Math.max(0,n-1)]) {
                for (const m of ['get','at','valueAt','barAt']) {
                    try {
                        if (typeof d[m] === 'function') {
                            const r = d[m](idx);
                            out[m+idx] = JSON.stringify(r).slice(0,300);
                            break;
                        }
                    } catch(e) {}
                }
            }
            // time mapping
            try {
                const ts = model.timeScale();
                out.tsMethods = Object.getOwnPropertyNames(Object.getPrototypeOf(ts))
                    .filter(k => /time|index|point/i.test(k)).slice(0,20);
            } catch(e) { out.tsMethods = 'ERR'; }
        } catch(e) { out.err = String(e).slice(0,300); }
        return out;
    })()""")
    import json
    print(json.dumps(info, indent=1)[:4000])
    await client.close()


asyncio.run(main())
