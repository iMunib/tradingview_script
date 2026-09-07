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
            const editor = window._monaco.editor.getEditors()[0];
            const currentVal = editor.getModel().getValue();
            
            // Check button
            const updateBtn = document.querySelector('[title="Update on chart"]');
            const saveBtn = document.querySelector('[title="Save script"]') || document.querySelector('[title="Save"]');
            const allButtons = Array.from(document.querySelectorAll('button')).map(b => ({
                text: b.innerText,
                title: b.getAttribute('title'),
                disabled: b.disabled
            })).filter(b => b.title || /save|update|add/i.test(b.text));

            return {
                modelLength: currentVal.length,
                firstLine: currentVal.split('\\n')[0],
                secondLine: currentVal.split('\\n')[1],
                allButtons: allButtons
            };
        })()
        """
        await ws.send(json.dumps({"id": 2, "sessionId": sid, "method": "Runtime.evaluate", "params": {"expression": js_code, "returnByValue": True}}))
        while True:
            r = json.loads(await ws.recv())
            if r.get("id") == 2:
                print("Editor state:", json.dumps(r["result"]["result"]["value"], indent=2))
                break

asyncio.run(main())
