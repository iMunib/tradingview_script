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
            // Check if monaco or models can be found
            let found = null;
            try {
                // In webpack 5:
                window.webpackChunktradingview.push([['dummy_inspect'], {}, (require) => {
                    for (let id of Object.keys(require.m)) {
                        try {
                            let mod = require(id);
                            if (mod && mod.editor && typeof mod.editor.getModels === 'function') {
                                window._monaco = mod;
                                found = 'Found monaco in module ' + id;
                                break;
                            }
                        } catch(e) {}
                    }
                }]);
            } catch(e) {
                found = 'Error: ' + e.message;
            }
            if (!found && window._monaco) {
                found = 'Already on window._monaco';
            }
            let modelsCount = (window._monaco && window._monaco.editor) ? window._monaco.editor.getModels().length : 0;
            return {
                found: found,
                modelsCount: modelsCount
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
