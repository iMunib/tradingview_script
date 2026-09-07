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
            // Close any error or warning dialogs (like max indicators reached)
            const closeButtons = Array.from(document.querySelectorAll('[data-name="close"], button')).filter(b => b.innerText && b.innerText.trim().toLowerCase() === 'close');
            closeButtons.forEach(b => b.click());

            const coll = window._exposed_chartWidgetCollection;
            const model = coll.activeChartWidget.value().model();
            const allPanes = model.panes();
            let removed = [];
            for (let p of allPanes) {
                for (let s of p.dataSources()) {
                    const title = s.title ? s.title() : '';
                    if (/strategy|quant|evidence/i.test(title)) {
                        model.removeSource(s);
                        removed.push(title);
                    }
                }
            }
            return { removed };
        })()
        """
        await ws.send(json.dumps({"id": 2, "sessionId": sid, "method": "Runtime.evaluate", "params": {"expression": js_code, "returnByValue": True}}))
        while True:
            r = json.loads(await ws.recv())
            if r.get("id") == 2:
                print("Removed:", json.dumps(r["result"]["result"]["value"], indent=2))
                break

asyncio.run(main())
