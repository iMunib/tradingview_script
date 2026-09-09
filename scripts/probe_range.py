"""Probe 9: setVisibleTimeRange to force full-history load."""
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
    r = await client.eval_js("""(() => {
        try {
            const w = window._exposed_chartWidgetCollection.activeChartWidget.value();
            w.setVisibleTimeRange({from: 631152000, to: 1786492800}, {percentRightMargin: 5});
            return 'range-set';
        } catch(e) { return 'ERR:' + String(e).slice(0,300); }
    })()""")
    print("SET:", r)
    for i in range(12):
        await asyncio.sleep(5)
        r2 = await client.eval_js("""(() => {
            const m = window._exposed_chartWidgetCollection.activeChartWidget.value().model();
            const ms = m.mainSeries();
            let ft = 0;
            try { ft = ms.bars().valueAt(ms.bars().firstIndex())[0]; } catch(e) {}
            return {first: ms.bars().firstIndex(), last: ms.bars().lastIndex(), firstTime: ft};
        })()""")
        print(f"t+{(i+1)*5}s:", _json.dumps(r2))
        if r2.get('firstTime') and r2['firstTime'] < 1000000000:
            break
    await client.close()


asyncio.run(main())
