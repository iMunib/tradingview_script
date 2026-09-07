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
            // Check Monaco editor instance
            // Often attached to editor DOM element
            let editorInstance = null;
            const editorEl = document.querySelector('.monaco-editor');
            if (editorEl) {
                // Check properties
                for (let key in editorEl) {
                    if (key.startsWith('__react') || key.startsWith('__')) {
                        // could inspect
                    }
                }
            }
            // Check window objects
            let monacoFound = false;
            for (let k of Object.keys(window)) {
                if (k.toLowerCase().includes('monaco')) {
                    return 'Window has ' + k;
                }
            }
            return 'No monaco on window';
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
