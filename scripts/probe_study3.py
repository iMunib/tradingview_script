"""Probe 7: iterate study data fully; compare with main series bar count."""
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
            out.firstIndex = d.firstIndex(); out.lastIndex = d.lastIndex();
            let cnt = 0, firstT = 0, lastT = 0, nonNull = 0;
            try {
                d.each((v, i) => { cnt++;
                    if (v) { nonNull++; if (!firstT) firstT = v[0]; lastT = v[0]; } });
            } catch(e) { out.eachErr = String(e).slice(0,120); }
            out.iterCount = cnt; out.nonNull = nonNull;
            out.firstTime = firstT; out.lastTime = lastT;
            // main series
            const ms = model.mainSeries();
            out.msBars = ms.bars ? ms.bars().size() : 'n/a';
            try { out.msFirst = ms.bars().firstIndex(); out.msLast = ms.bars().lastIndex(); }
            catch(e) { out.msRange = 'ERR'; }
        } catch(e) { out.err = String(e).slice(0,300); }
        return out;
    })()""")
    import json
    print(json.dumps(info, indent=1)[:2000])
    await client.close()


asyncio.run(main())
