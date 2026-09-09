"""Probe 8: scroll-back history loading API."""
import asyncio
import os
import sys
import json as _json

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)
import runner


async def main():
    client = runner.CDPClient(runner.get_ws_url())
    await client.connect()
    await client.find_tradingview_target()
    js = """(() => {
        const out = {};
        try {
            const coll = window._exposed_chartWidgetCollection;
            const widget = coll.activeChartWidget.value();
            out.widgetMethods = Object.getOwnPropertyNames(Object.getPrototypeOf(widget))
                .filter(k => /scroll|chart|goto|date|time/i.test(k));
            const ch = widget.chart ? widget.chart() : null;
            out.hasChart = !!ch;
            if (ch) out.chartMethods = Object.getOwnPropertyNames(Object.getPrototypeOf(ch))
                .filter(k => /scroll|position|date|time|history|more/i.test(k));
            const model = widget.model();
            const ms = model.mainSeries();
            out.msFirst = ms.bars().firstIndex(); out.msLast = ms.bars().lastIndex();
            try { out.firstTime = ms.bars().valueAt(out.msFirst)[0]; } catch(e) { out.firstTime = 'ERR'; }
        } catch(e) { out.err = String(e).slice(0,300); }
        return out;
    })()"""
    print(_json.dumps(await client.eval_js(js), indent=1)[:2500])
    # try scrollToPosition far left
    r = await client.eval_js("""(() => {
        try {
            const w = window._exposed_chartWidgetCollection.activeChartWidget.value();
            w.chart().scrollToPosition(-100000, false);
            return 'scrolled';
        } catch(e) { return 'ERR:' + String(e).slice(0,200); }
    })()""")
    print("SCROLL:", r)
    await asyncio.sleep(6)
    r2 = await client.eval_js("""(() => {
        const m = window._exposed_chartWidgetCollection.activeChartWidget.value().model();
        const ms = m.mainSeries();
        let ft = 0;
        try { ft = ms.bars().valueAt(ms.bars().firstIndex())[0]; } catch(e) {}
        return {first: ms.bars().firstIndex(), last: ms.bars().lastIndex(), firstTime: ft};
    })()""")
    print(_json.dumps(r2, indent=1)[:600])
    await client.close()


asyncio.run(main())
