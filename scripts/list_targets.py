import asyncio
import json
import websockets

async def main():
    ws_url = "ws://127.0.0.1:9222/devtools/browser/f4211e06-b384-4568-9e42-fab8126bb7a9"
    async with websockets.connect(ws_url) as ws:
        msg = {"id": 1, "method": "Target.getTargets"}
        await ws.send(json.dumps(msg))
        while True:
            res = await ws.recv()
            data = json.loads(res)
            if data.get("id") == 1:
                targets = data["result"]["targetInfos"]
                print(f"Total targets: {len(targets)}")
                for t in targets:
                    if t.get("type") == "page":
                        print(f"PAGE: id={t.get('targetId')} title='{t.get('title')}' url='{t.get('url')}'")
                break

asyncio.run(main())
