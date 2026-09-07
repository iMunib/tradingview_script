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
            const legendItems = Array.from(document.querySelectorAll('[data-name="legend-source-item"], [class*="item-quatTGAC"]'))
                .map(el => ({
                    text: el.innerText.replace(/\\n/g, ' '),
                    hasError: !!el.querySelector('[class*="error"], [data-name="legend-error-icon"]'),
                    errorText: el.querySelector('[class*="error"]') ? el.querySelector('[class*="error"]').innerText : null
                }));
            return legendItems;
        })()
        """
        await ws.send(json.dumps({"id": 2, "sessionId": sid, "method": "Runtime.evaluate", "params": {"expression": js_code, "returnByValue": True}}))
        while True:
            r = json.loads(await ws.recv())
            if r.get("id") == 2:
                print("Legend items:", json.dumps(r["result"]["result"]["value"], indent=2))
                break

asyncio.run(main())
