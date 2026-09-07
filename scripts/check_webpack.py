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
            // Check window.webpackChunk or similar
            let results = {};
            if (window.webpackChunktradingview) {
                results.webpack = 'webpackChunktradingview found';
            }
            // Let's check how monaco is instantiated or if any element has __monaco
            // In Monaco editor, monaco is often in an AMD require or global monaco
            // Let's check window.require
            if (typeof window.require !== 'undefined') {
                results.hasRequire = true;
            }
            return results;
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
                print("Result:", r["result"]["result"]["value"])
                break

asyncio.run(main())
