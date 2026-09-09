"""Probe 10: synthetic horizontal wheel scroll to backfill history."""
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
    rect = await client.eval_js("""(() => {
        const c = document.querySelector('canvas[data-name="pane-canvas"], canvas');
        if (!c) return null;
        const r = c.getBoundingClientRect();
        return {x: r.x + r.width/2, y: r.y + r.height/2, w: r.width, h: r.height};
    })()""")
    print("RECT:", _json.dumps(rect)[:300])
    if not rect:
        return
    x, y = int(rect['x']), int(rect['y'])
    await client.send_cmd("Input.dispatchMouseEvent",
                          {"type": "mouseMoved", "x": x, "y": y})
    for batch in range(6):
        for _ in range(15):
            await client.send_cmd("Input.dispatchMouseEvent",
                                  {"type": "mouseWheel", "x": x, "y": y,
                                   "deltaX": -600, "deltaY": 0})
            await asyncio.sleep(0.15)
        await asyncio.sleep(4)
        r2 = await client.eval_js("""(() => {
            const m = window._exposed_chartWidgetCollection.activeChartWidget.value().model();
            const ms = m.mainSeries();
            let ft = 0;
            try { ft = ms.bars().valueAt(ms.bars().firstIndex())[0]; } catch(e) {}
            return {first: ms.bars().firstIndex(), last: ms.bars().lastIndex(), firstTime: ft};
        })()""")
        print(f"batch {batch}:", _json.dumps(r2))
    await client.close()


asyncio.run(main())
