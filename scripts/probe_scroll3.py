"""Probe 11: synthetic WheelEvent via JS dispatch to backfill history."""
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
    for batch in range(8):
        await client.eval_js("""(() => {
            const c = document.querySelector('canvas[data-name="pane-canvas"]') ||
                      document.querySelectorAll('canvas')[0];
            const r = c.getBoundingClientRect();
            const ev = new WheelEvent('wheel', {bubbles: true, cancelable: true,
                clientX: r.x + r.width/2, clientY: r.y + r.height/2,
                deltaX: -2000, deltaY: 0, deltaMode: 0});
            (document.elementFromPoint(r.x + r.width/2, r.y + r.height/2) || c).dispatchEvent(ev);
            return true;
        })()""")
        await asyncio.sleep(1.2)
        if batch % 2 == 1:
            r2 = await client.eval_js("""(() => {
                const m = window._exposed_chartWidgetCollection.activeChartWidget.value().model();
                const ms = m.mainSeries();
                let ft = 0;
                try { ft = ms.bars().valueAt(ms.bars().firstIndex())[0]; } catch(e) {}
                return {first: ms.bars().firstIndex(), last: ms.bars().lastIndex(), firstTime: ft};
            })()""")
            print(f"batch {batch}:", _json.dumps(r2))
            if r2.get('firstTime', 9e9) < 1000000000:
                break
    await client.close()


asyncio.run(main())
