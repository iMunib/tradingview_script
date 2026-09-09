"""Diag: inject emitter variant, then dump study titles + plot counts + errors."""
import asyncio
import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)
import runner
from scripts.export_trade_logs import build_emitter, inject_pine, VARIANTS


async def main():
    client = runner.CDPClient(runner.get_ws_url())
    await client.connect()
    await client.find_tradingview_target()
    epath = build_emitter(VARIANTS["OOS"], "DIAG_BTC1W")
    code = open(epath, encoding="utf-8").read()
    print("emitter plots in source:", code.count('plot(X_'), flush=True)
    try:
        await inject_pine(client, code)
        print("inject: no exception", flush=True)
    except Exception as e:
        print("inject EXC:", str(e)[:300], flush=True)
    info = await client.eval_js("""(() => {
        const out = {studies: []};
        try {
            const coll = window._exposed_chartWidgetCollection;
            const model = coll.activeChartWidget.value().model();
            out.symbol = model.mainSeries().symbol();
            out.interval = model.mainSeries().interval();
            for (const p of model.panes()) for (const s of p.dataSources()) {
                let t = '';
                try { t = s.title ? s.title() : ''; } catch(e) {}
                if (String(t).includes('FINAL')) {
                    let n = 0;
                    try { n = s.metaInfo().plots.length; } catch(e) {}
                    out.studies.push({title: String(t).slice(0,50), nplots: n});
                }
            }
            const r = document.querySelector('[class*="reportContainer-"]');
            out.reportHead = r ? r.innerText.slice(0, 300) : 'NOREPORT';
        } catch(e) { out.err = String(e).slice(0,200); }
        return out;
    })()""")
    import json
    print(json.dumps(info, indent=1)[:2000], flush=True)
    await client.close()


asyncio.run(main())
