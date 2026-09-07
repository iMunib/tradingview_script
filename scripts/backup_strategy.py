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
            const models = window._monaco.editor.getModels();
            const targetModel = models.find(m => m.uri.toString().includes('placement=dialog') && !m.uri.toString().includes('ORIGINAL')) || models[0];
            return targetModel.getValue();
        })()
        """
        await ws.send(json.dumps({"id": 2, "sessionId": sid, "method": "Runtime.evaluate", "params": {"expression": js_code, "returnByValue": True}}))
        while True:
            r = json.loads(await ws.recv())
            if r.get("id") == 2:
                script_text = r["result"]["result"]["value"]
                with open("scripts/user_original_strategy.pine", "w", encoding="utf-8") as f:
                    f.write(script_text)
                print(f"Backed up user strategy: {len(script_text)} characters.")
                break

asyncio.run(main())
