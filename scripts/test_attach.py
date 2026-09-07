import asyncio
import json
import websockets

async def main():
    browser_ws = "ws://127.0.0.1:9222/devtools/browser/f4211e06-b384-4568-9e42-fab8126bb7a9"
    target_id = "DB89DD8D0A3BA86237AB6883FC958F78"
    async with websockets.connect(browser_ws) as ws:
        attach_msg = {
            "id": 10,
            "method": "Target.attachToTarget",
            "params": {"targetId": target_id, "flatten": True}
        }
        await ws.send(json.dumps(attach_msg))
        session_id = None
        while True:
            res = await ws.recv()
            data = json.loads(res)
            if data.get("id") == 10:
                session_id = data["result"]["sessionId"]
                break
        
        eval_msg = {
            "id": 11,
            "sessionId": session_id,
            "method": "Runtime.evaluate",
            "params": {"expression": "document.title"}
        }
        await ws.send(json.dumps(eval_msg))
        while True:
            res = await ws.recv()
            data = json.loads(res)
            if data.get("id") == 11:
                val = data["result"]["result"]["value"]
                print("Title:", repr(val))
                break

asyncio.run(main())
