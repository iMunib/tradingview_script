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
        
        # Test finding monaco editor instance from DOM
        js_code = """
        (() => {
            // Check if there is an editor instance stored in DOM or require
            const editorEl = document.querySelector('.monaco-editor');
            // Try looking for editor in __monaco_editor__ or similar
            let keys = [];
            for (let prop in editorEl) {
                keys.push(prop);
            }
            return {
                keys: keys.slice(0, 20)
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
                print("Result:", r["result"]["result"]["value"])
                break

asyncio.run(main())
