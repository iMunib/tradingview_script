"""Diagnose live chart state: symbol, interval, strategy presence, report text."""
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
        const out = {exposed: !!window._exposed_chartWidgetCollection};
        try {
            const coll = window._exposed_chartWidgetCollection;
            const widget = coll && coll.activeChartWidget ? coll.activeChartWidget.value() : null;
            out.hasModel = !!(widget && widget.hasModel());
            if (out.hasModel) {
                const model = widget.model();
                out.symbol = model.mainSeries().symbol();
                out.interval = model.mainSeries().interval();
                const srcs = [];
                for (let p of model.panes()) for (let s of p.dataSources()) {
                    try { srcs.push(s.title ? s.title() : (s.name ? s.name() : '?')); } catch(e) {}
                }
                out.sources = srcs;
            }
        } catch(e) { out.err = String(e); }
        const report = document.querySelector('[class*="reportContainer-"]') || document.querySelector('[class*="wrapper-dmId9qUc"]') || document.querySelector('[class*="wrapper-yprR2JgA"]');
        out.reportHead = report ? report.innerText.slice(0, 600) : 'NO-REPORT-CONTAINER';
        return out;
    })()""")
    import json
    print(json.dumps(info, indent=2)[:3000])
    await client.close()


asyncio.run(main())
