import asyncio
import json
import websockets

async def main():
    with open(r"C:\Users\RehmanPC\AppData\Local\Google\Chrome\User Data\DevToolsActivePort") as f:
        port = f.readline().strip()
        path = f.readline().strip()
    ws_url = f"ws://127.0.0.1:{port}{path}"
    print(f"Connecting to Chrome at {ws_url}...")
    try:
        async with asyncio.timeout(5):
            async with websockets.connect(ws_url) as ws:
                msg = {"id": 1, "method": "Target.getTargets"}
                await ws.send(json.dumps(msg))
                res = await ws.recv()
                data = json.loads(res)
                print("Chrome targets:", data)
    except Exception as e:
        print("Chrome error:", e)

asyncio.run(main())
