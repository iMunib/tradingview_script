import asyncio
import json
import websockets

async def main():
    browser_ws = "ws://127.0.0.1:9222/devtools/browser/f4211e06-b384-4568-9e42-fab8126bb7a9"
    target_id = "DB89DD8D0A3BA86237AB6883FC958F78"
    async with websockets.connect(browser_ws) as ws:
        # Attach
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
        
        # Check buttons and tabs at bottom of TradingView
        js_code = """
        (() => {
            const buttons = Array.from(document.querySelectorAll('button, [role="button"], [data-name]'))
                .map(el => ({
                    text: el.innerText ? el.innerText.trim() : '',
                    dataName: el.getAttribute('data-name') || '',
                    ariaLabel: el.getAttribute('aria-label') || '',
                    className: el.className
                }))
                .filter(b => b.text || b.dataName || b.ariaLabel);
            return buttons.filter(b => 
                /pine|editor|strategy|tester/i.test(b.text) || 
                /pine|editor|strategy|tester/i.test(b.dataName) ||
                /pine|editor|strategy|tester/i.test(b.ariaLabel)
            );
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
                print("Found bottom tabs/buttons:")
                print(json.dumps(r["result"]["result"]["value"], indent=2))
                break

asyncio.run(main())
