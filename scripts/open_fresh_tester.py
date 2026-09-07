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
            // Click strategy tester bottom button
            const btn = Array.from(document.querySelectorAll('button, [role="button"]'))
                .find(b => (b.innerText || '').toLowerCase().includes('strategy tester') || b.getAttribute('data-name') === 'backtesting');
            if (btn) btn.click();
            return btn ? 'Clicked tester' : 'Not found';
        })()
        """
        await ws.send(json.dumps({"id": 2, "sessionId": sid, "method": "Runtime.evaluate", "params": {"expression": js_code, "returnByValue": True}}))
        while True:
            r = json.loads(await ws.recv())
            if r.get("id") == 2:
                print("Click tester:", r["result"]["result"]["value"])
                break
        
        await asyncio.sleep(2)
        js_check = """
        (() => {
            const report = document.querySelector('[class*="reportContainer-"]') || document.querySelector('[class*="wrapper-dmId9qUc"]');
            return report ? report.innerText : 'No report';
        })()
        """
        await ws.send(json.dumps({"id": 3, "sessionId": sid, "method": "Runtime.evaluate", "params": {"expression": js_check, "returnByValue": True}}))
        while True:
            r = json.loads(await ws.recv())
            if r.get("id") == 3:
                print("Report text:\n", r["result"]["result"]["value"])
                break

asyncio.run(main())
