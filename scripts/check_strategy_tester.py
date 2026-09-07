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
            // Find all tables, reports, or text in strategy tester
            const reportContainer = document.querySelector('[data-name="backtesting-report-container"]') || 
                                    document.querySelector('.report-content') ||
                                    document.querySelector('[class*="report"]') ||
                                    document.body;
            
            // Let's get text content of all elements with class containing 'report' or 'table' or 'metric'
            const elements = Array.from(document.querySelectorAll('*'))
                .filter(el => {
                    const t = (el.innerText || '').trim();
                    return /Net Profit|Total Closed Trades|Percent Profitable|Profit Factor|Max Drawdown|Sharpe Ratio/i.test(t) && el.children.length < 5;
                })
                .map(el => ({
                    tag: el.tagName,
                    className: el.className,
                    text: (el.innerText || '').trim().replace(/\\n+/g, ' | ')
                }));
            return elements.slice(0, 30);
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
                print("Strategy metrics found in DOM:")
                print(json.dumps(r["result"]["result"]["value"], indent=2))
                break

asyncio.run(main())
