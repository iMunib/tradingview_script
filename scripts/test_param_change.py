import sys, os, asyncio, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import runner

async def main():
    ws_url = runner.get_ws_url()
    client = runner.CDPClient(ws_url)
    await client.connect()
    await client.find_tradingview_target()

    with open("strategy.pine", "r", encoding="utf-8") as f:
        code = f.read()
    code = code.replace("atrStopMult = input.float(2.5", "atrStopMult = input.float(2.0")

    js_edit = f"""
    (() => {{
        const editor = window._monaco.editor.getEditors()[0];
        const model = editor.getModel();
        editor.executeEdits('test', [{{
            range: model.getFullModelRange(),
            text: {json.dumps(code)},
            forceMoveMarkers: true
        }}]);
        editor.pushUndoStop();
        editor.focus();

        const editorEl = document.querySelector('.monaco-editor');
        let container = editorEl;
        while (container && !container.getAttribute('data-dialog-name') && !container.className.includes('dialog')) {{
            container = container.parentElement;
        }}
        const root = container || document;
        const buttons = Array.from(root.querySelectorAll('button, [role="button"]')).map(b => ({{
            text: (b.innerText || '').trim(),
            title: b.getAttribute('title') || '',
            ariaLabel: b.getAttribute('aria-label') || '',
            dataName: b.getAttribute('data-name') || ''
        }})).filter(b => b.text || b.title || b.ariaLabel || b.dataName);
        return buttons;
    }})()
    """
    res = await client.eval_js(js_edit)
    print("Buttons after edit:", json.dumps(res, indent=2))
    await client.close()

if __name__ == "__main__":
    asyncio.run(main())
