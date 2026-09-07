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
            // Check header elements for symbol and timeframe
            const symbolBtn = document.querySelector('#header-toolbar-symbol-search') || 
                             document.querySelector('[data-name="legend-series-item"]') ||
                             document.querySelector('[class*="symbolSearch"]');
            
            // Check interval/timeframe buttons
            const intervalBtn = document.querySelector('#header-toolbar-intervals') ||
                               document.querySelector('[data-name="timeframe-button"]');
            
            return {
                symbolBtn: symbolBtn ? { id: symbolBtn.id, text: symbolBtn.innerText, dataName: symbolBtn.getAttribute('data-name') } : null,
                intervalBtn: intervalBtn ? { id: intervalBtn.id, text: intervalBtn.innerText, dataName: intervalBtn.getAttribute('data-name') } : null
            };
        })()
        """
        await ws.send(json.dumps({
            "id": 2, "sessionId": sid,
            "method": "Runtime.evaluate",
            "params": {"expression": js_code, "returnByValue": True}
        }))
        while True:
            r = json.loads(await ws.recv())
            if r.get("id") == 2:
                print("Header elements:", json.dumps(r["result"]["result"]["value"], indent=2))
                break

asyncio.run(main())
