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
        
        with open("strategy.pine", "r", encoding="utf-8") as f:
            new_code = f.read()
        
        js_code = f"""
        (() => {{
            const editor = window._monaco.editor.getEditors()[0];
            const model = editor.getModel();
            editor.executeEdits('runner', [{{
                range: model.getFullModelRange(),
                text: {json.dumps(new_code)},
                forceMoveMarkers: true
            }}]);
            editor.pushUndoStop();
            
            // Now click 'Update on chart' or 'Add to chart'
            const updateBtn = document.querySelector('[title="Update on chart"]') ||
                             document.querySelector('[title="Add to chart"]') ||
                             Array.from(document.querySelectorAll('button')).find(b => /update on chart|add to chart/i.test(b.innerText || ''));
            if (updateBtn) updateBtn.click();
            return {{ clicked: updateBtn ? (updateBtn.getAttribute('title') || updateBtn.innerText) : 'none' }};
        }})()
        """
        await ws.send(json.dumps({"id": 2, "sessionId": sid, "method": "Runtime.evaluate", "params": {"expression": js_code, "returnByValue": True}}))
        while True:
            r = json.loads(await ws.recv())
            if r.get("id") == 2:
                print("Update click:", json.dumps(r["result"]["result"]["value"], indent=2))
                break
        
        # Wait 4 seconds for compilation
        await asyncio.sleep(4)
        
        # Check compiler markers & toasts
        js_markers = """
        (() => {
            const editor = window._monaco.editor.getEditors()[0];
            const markers = window._monaco.editor.getModelMarkers({ resource: editor.getModel().uri });
            const errors = markers.filter(m => m.severity === 8).map(m => ({ line: m.startLineNumber, col: m.startColumn, msg: m.message }));
            const warnings = markers.filter(m => m.severity === 4).map(m => ({ line: m.startLineNumber, col: m.startColumn, msg: m.message }));
            return { errors, warnings };
        })()
        """
        await ws.send(json.dumps({"id": 3, "sessionId": sid, "method": "Runtime.evaluate", "params": {"expression": js_markers, "returnByValue": True}}))
        while True:
            r = json.loads(await ws.recv())
            if r.get("id") == 3:
                print("Compiler result:", json.dumps(r["result"]["result"]["value"], indent=2))
                break

asyncio.run(main())
