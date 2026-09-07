import asyncio
import json
import websockets

async def main():
    target_id = "DB89DD8D0A3BA86237AB6883FC958F78"
    page_ws = f"ws://127.0.0.1:9222/devtools/page/{target_id}"
    print(f"Connecting to page WS: {page_ws}")
    async with websockets.connect(page_ws) as ws:
        # Enable Runtime and evaluate document.title
        await ws.send(json.dumps({"id": 1, "method": "Runtime.enable"}))
        await ws.send(json.dumps({"id": 2, "method": "Runtime.evaluate", "params": {"expression": "document.title"}}))
        while True:
            res = await ws.recv()
            data = json.loads(res)
            if data.get("id") == 2:
                print("Page title evaluation result:", data)
                break

asyncio.run(main())
