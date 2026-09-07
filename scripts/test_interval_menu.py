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
        
        # Click intervals button
        js_click = "document.querySelector('#header-toolbar-intervals button, #header-toolbar-intervals').click();"
        await ws.send(json.dumps({"id": 2, "sessionId": sid, "method": "Runtime.evaluate", "params": {"expression": js_click}}))
        await ws.recv()
        await asyncio.sleep(1)

        # Inspect menu items
        js_items = """
        (() => {
            const items = Array.from(document.querySelectorAll('[data-value], [role="menuitem"]')).map(el => ({
                text: el.innerText ? el.innerText.trim() : '',
                dataValue: el.getAttribute('data-value')
            })).filter(x => x.text || x.dataValue);
            return items;
        })()
        """
        await ws.send(json.dumps({"id": 3, "sessionId": sid, "method": "Runtime.evaluate", "params": {"expression": js_items, "returnByValue": True}}))
        while True:
            r = json.loads(await ws.recv())
            if r.get("id") == 3:
                print("Interval menu items:", json.dumps(r["result"]["result"]["value"], indent=2))
                break

asyncio.run(main())
