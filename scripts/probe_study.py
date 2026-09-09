"""Probe 5: can JS read strategy study plot values per bar from the model?"""
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
            const widget = coll.activeChartWidget.value();
            const model = widget.model();
            const panes = model.panes();
            out.nPanes = panes.length;
            for (let pi = 0; pi < panes.length; pi++) {
                const srcs = [];
                for (const s of panes[pi].dataSources()) {
                    let t = '';
                    try { t = s.title ? s.title() : (s.name ? s.name() : '?'); } catch(e) { t = 'ERR'; }
                    const keys = [];
                    try { for (const k in s) { if (/data|plot|study|value|point|bar/i.test(k)) keys.push(k); } } catch(e) {}
                    let meta = null;
                    try {
                        const m = s.metaInfo ? s.metaInfo() : null;
                        meta = m ? {plots: (m.plots||[]).map(p => p.id || p.title || '?').slice(0,40),
                                    styles: Object.keys(m.styles||{}).length} : null;
                    } catch(e) { meta = 'ERR:' + String(e).slice(0,80); }
                    srcs.push({title: String(t).slice(0,60), ctor: s.constructor ? s.constructor.name : '?', keys: keys.slice(0,20), meta});
                }
                out['pane'+pi] = srcs;
            }
        } catch(e) { out.err = String(e).slice(0,300); }
        return out;
    })()""")
    import json
    print(json.dumps(info, indent=1)[:5000])
    await client.close()


asyncio.run(main())
