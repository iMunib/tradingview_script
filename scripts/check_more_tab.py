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
        
        # Click More tab
        js_click = """
        (() => {
            const btn = Array.from(document.querySelectorAll('[role="tab"], button')).find(b => (b.innerText || '').trim() === 'More');
            if (btn) { btn.click(); return 'Clicked More'; }
            return 'Not found';
        })()
        """
        await ws.send(json.dumps({"id": 2, "sessionId": sid, "method": "Runtime.evaluate", "params": {"expression": js_click, "returnByValue": True}}))
        await ws.recv()
        await asyncio.sleep(1)

        # Inspect table inside More
        js_table = """
        (() => {
            const report = document.querySelector('[class*="details-"]') || document.querySelector('[class*="tableWrapper-"]');
            return report ? report.innerText : 'None';
        })()
        """
        await ws.send(json.dumps({"id": 3, "sessionId": sid, "method": "Runtime.evaluate", "params": {"expression": js_table, "returnByValue": True}}))
        while True:
            r = json.loads(await ws.recv())
            if r.get("id") == 3:
                print("More text:\n", r["result"]["result"]["value"])
                break

asyncio.run(main())
