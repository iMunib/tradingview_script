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
        
        # Click menuBtn-HNxWMF1j
        js_click = "document.querySelector('.menuBtn-HNxWMF1j').click();"
        await ws.send(json.dumps({"id": 2, "sessionId": sid, "method": "Runtime.evaluate", "params": {"expression": js_click}}))
        await ws.recv()
        await asyncio.sleep(1)

        # Inspect opened menu items
        js_inspect = """
        (() => {
            const items = Array.from(document.querySelectorAll('[data-value], [class*="item-"]'))
                .map(el => ({
                    text: el.innerText ? el.innerText.trim() : '',
                    dataValue: el.getAttribute('data-value'),
                    className: el.className
                }))
                .filter(x => /day|week|month|hour|minute|1D|1W|D|W/i.test(x.text) || ['1D', '1W', 'D', 'W', 'W', '1W'].includes(x.dataValue));
            return items.slice(0, 20);
        })()
        """
        await ws.send(json.dumps({"id": 3, "sessionId": sid, "method": "Runtime.evaluate", "params": {"expression": js_inspect, "returnByValue": True}}))
        while True:
            r = json.loads(await ws.recv())
            if r.get("id") == 3:
                print("Menu items:", json.dumps(r["result"]["result"]["value"], indent=2))
                break

asyncio.run(main())
