import asyncio
import json
import websockets
import sys
sys.stdout.reconfigure(encoding='utf-8')

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
            // Find tabs at top of strategy tester
            const testerHeader = document.querySelector('[class*="header-"]') || document.querySelector('[class*="tabs-"]');
            const allButtons = Array.from(document.querySelectorAll('button, [role="tab"]'))
                .map(b => (b.innerText || '').trim())
                .filter(t => /overview|performance summary|list of trades/i.test(t));
            return {
                allButtons: allButtons
            };
        })()
        """
        await ws.send(json.dumps({"id": 2, "sessionId": sid, "method": "Runtime.evaluate", "params": {"expression": js_code, "returnByValue": True}}))
        while True:
            r = json.loads(await ws.recv())
            if r.get("id") == 2:
                print("Tester tabs found:", json.dumps(r["result"]["result"]["value"], indent=2))
                break

asyncio.run(main())
