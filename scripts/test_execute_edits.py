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
        
        with open("strategy.pine", "r", encoding="utf-8") as f:
            new_code = f.read()
        
        js_code = f"""
        (() => {{
            const editor = window._monaco.editor.getEditors()[0];
            const model = editor.getModel();
            const fullRange = model.getFullModelRange();
            editor.executeEdits('runner', [{{
                range: fullRange,
                text: {json.dumps(new_code)},
                forceMoveMarkers: true
            }}]);
            editor.pushUndoStop();
            return {{
                valLength: model.getValue().length,
                valStart: model.getValue().slice(0, 80)
            }};
        }})()
        """
        await ws.send(json.dumps({"id": 2, "sessionId": sid, "method": "Runtime.evaluate", "params": {"expression": js_code, "returnByValue": True}}))
        while True:
            r = json.loads(await ws.recv())
            if r.get("id") == 2:
                print("ExecuteEdits result:", json.dumps(r["result"]["result"]["value"], indent=2))
                break

asyncio.run(main())
