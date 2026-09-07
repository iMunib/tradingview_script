import asyncio
import json
import websockets

async def main():
    ws_url = "ws://127.0.0.1:9222/devtools/browser/f4211e06-b384-4568-9e42-fab8126bb7a9"
    async with websockets.connect(ws_url) as ws:
        # Create a new tab or navigate
        msg = {
            "id": 2,
            "method": "Target.createTarget",
            "params": {"url": "https://www.tradingview.com/chart/"}
        }
        await ws.send(json.dumps(msg))
        res = await ws.recv()
        print("CreateTarget response:", res)

asyncio.run(main())
