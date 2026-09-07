import asyncio
import json
import websockets

async def main():
    browser_ws = "ws://127.0.0.1:9222/devtools/browser/f4211e06-b384-4568-9e42-fab8126bb7a9"
    target_id = "DB89DD8D0A3BA86237AB6883FC958F78"
    async with websockets.connect(browser_ws) as ws:
        await ws.send(json.dumps({
            "id": 1, "method": "Target.attachToTarget",
            "params": {"targetId": target_id, "flatten": True}
        }))
        sid = None
        while True:
            r = json.loads(await ws.recv())
            if r.get("id") == 1:
                sid = r["result"]["sessionId"]
                break
        
        js_code = """
        (() => {
            // Find all studies on chart
            const coll = window._exposed_chartWidgetCollection;
            const model = coll.activeChartWidget.value().model();
            const allPanes = model.panes();
            const sources = [];
            for (let p of allPanes) {
                for (let s of p.dataSources()) {
                    sources.push({
                        id: s.id ? s.id() : null,
                        title: s.title ? s.title() : null
                    });
                }
            }
            return sources;
        })()
        """
        await ws.send(json.dumps({"id": 2, "sessionId": sid, "method": "Runtime.evaluate", "params": {"expression": js_code, "returnByValue": True}}))
        while True:
            r = json.loads(await ws.recv())
            if r.get("id") == 2:
                print("All chart data sources:", json.dumps(r["result"]["result"]["value"], indent=2))
                break

asyncio.run(main())
