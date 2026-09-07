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
        
        # In TradingView search input:
        # Set value, dispatch input event, wait 1s, then press Enter
        js_type = """
        (() => {
            const input = document.querySelector('[data-name="symbol-search-items-dialog"] input') || 
                          document.querySelector('input[data-role="search"]');
            if (!input) return 'no input';
            input.focus();
            input.value = 'BTCUSD';
            input.dispatchEvent(new Event('input', { bubbles: true }));
            return 'typed BTCUSD';
        })()
        """
        await ws.send(json.dumps({"id": 2, "sessionId": sid, "method": "Runtime.evaluate", "params": {"expression": js_type, "returnByValue": True}}))
        await ws.recv()
        await asyncio.sleep(1.5)

        # Press Enter or click first search item
        js_select = """
        (() => {
            const firstItem = document.querySelector('[data-name="symbol-search-dialog-content-item"]') ||
                              document.querySelector('.itemRow-oRSs8UQo') ||
                              document.querySelector('[class*="itemRow"]');
            if (firstItem) {
                firstItem.click();
                return 'Clicked first item';
            }
            return 'No item found';
        })()
        """
        await ws.send(json.dumps({"id": 3, "sessionId": sid, "method": "Runtime.evaluate", "params": {"expression": js_select, "returnByValue": True}}))
        while True:
            r = json.loads(await ws.recv())
            if r.get("id") == 3:
                print("Select result:", r["result"]["result"]["value"])
                break
        
        await asyncio.sleep(2)
        # Check current symbol
        js_sym = "document.querySelector('#header-toolbar-symbol-search').innerText"
        await ws.send(json.dumps({"id": 4, "sessionId": sid, "method": "Runtime.evaluate", "params": {"expression": js_sym, "returnByValue": True}}))
        while True:
            r = json.loads(await ws.recv())
            if r.get("id") == 4:
                print("New current symbol:", r["result"]["result"]["value"])
                break

asyncio.run(main())
