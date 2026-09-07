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
        
        # Focus editor
        await ws.send(json.dumps({
            "id": 2, "sessionId": sid,
            "method": "Runtime.evaluate",
            "params": {"expression": "window._monaco.editor.getEditors()[0].focus();"}
        }))
        await ws.recv()
        await asyncio.sleep(0.5)

        # Dispatch Ctrl+Enter
        # Modifier: 2 = Control
        await ws.send(json.dumps({
            "id": 3, "sessionId": sid,
            "method": "Input.dispatchKeyEvent",
            "params": {"type": "rawKeyDown", "key": "Enter", "code": "Enter", "windowsVirtualKeyCode": 13, "modifiers": 2}
        }))
        await ws.recv()
        await ws.send(json.dumps({
            "id": 4, "sessionId": sid,
            "method": "Input.dispatchKeyEvent",
            "params": {"type": "keyUp", "key": "Enter", "code": "Enter", "windowsVirtualKeyCode": 13, "modifiers": 2}
        }))
        await ws.recv()
        print("Dispatched Ctrl+Enter successfully!")

asyncio.run(main())
