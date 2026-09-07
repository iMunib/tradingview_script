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
            const ta = document.querySelector('.monaco-editor textarea');
            const lines = Array.from(document.querySelectorAll('.view-lines .view-line')).map(l => l.innerText);
            
            // Find all buttons in pine editor toolbar
            const pineToolbar = document.querySelector('[class*="pineEditor"]') || document.querySelector('[data-name="pine-editor"]');
            const buttons = Array.from(document.querySelectorAll('button, [role="button"]'))
                .filter(b => /add to chart|update on chart|save/i.test(b.innerText || '') || /add to chart|update on chart|save/i.test(b.getAttribute('aria-label') || ''))
                .map(b => ({
                    text: b.innerText,
                    ariaLabel: b.getAttribute('aria-label'),
                    dataName: b.getAttribute('data-name')
                }));

            return {
                hasTextarea: !!ta,
                sampleLines: lines.slice(0, 10),
                buttons: buttons
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
                print("Monaco details:", json.dumps(r["result"]["result"]["value"], indent=2))
                break

asyncio.run(main())
