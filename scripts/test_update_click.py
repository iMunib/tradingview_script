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
        
        # In TradingView:
        # Let's inspect what happens on Ctrl+Enter or clicking Update on chart
        js_code = """
        (() => {
            const btn = document.querySelector('[title="Update on chart"]');
            if (!btn) return 'No update button';
            btn.click();
            return 'Clicked update on chart';
        })()
        """
        await ws.send(json.dumps({"id": 2, "sessionId": sid, "method": "Runtime.evaluate", "params": {"expression": js_code, "returnByValue": True}}))
        while True:
            r = json.loads(await ws.recv())
            if r.get("id") == 2:
                print("Click result:", r["result"]["result"]["value"])
                break
        
        # Wait 3 seconds and check notifications or console errors
        await asyncio.sleep(3)
        js_check = """
        (() => {
            const toasts = Array.from(document.querySelectorAll('[class*="toast"], [class*="notification"], [class*="error"], [class*="console"]'))
                .map(el => el.innerText).filter(Boolean);
            const markers = window._monaco ? window._monaco.editor.getModelMarkers({}) : [];
            return {
                toasts: toasts.slice(0, 10),
                markers: markers.map(m => ({ line: m.startLineNumber, msg: m.message, sev: m.severity }))
            };
        })()
        """
        await ws.send(json.dumps({"id": 3, "sessionId": sid, "method": "Runtime.evaluate", "params": {"expression": js_check, "returnByValue": True}}))
        while True:
            r = json.loads(await ws.recv())
            if r.get("id") == 3:
                print("Status check:", json.dumps(r["result"]["result"]["value"], indent=2))
                break

asyncio.run(main())
