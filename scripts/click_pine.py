import sys, os, asyncio, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import runner

async def main():
    ws_url = runner.get_ws_url()
    client = runner.CDPClient(ws_url)
    await client.connect()
    await client.find_tradingview_target()

    # Open Pine Editor
    open_pine_js = '''(() => {
        let pineBtn = document.querySelector('[data-name="pine-dialog-button"]') ||
                      document.querySelector('button[aria-label="Pine"]') ||
                      Array.from(document.querySelectorAll('button')).find(b => /pine editor/i.test(b.innerText || ''));
        if (pineBtn) pineBtn.click();
        return !!pineBtn;
    })()'''
    res = await client.eval_js(open_pine_js)
    print("Opened pine:", res)
    await asyncio.sleep(2)

    # Inspect buttons in editor
    js_buttons = '''(() => {
        const editorEl = document.querySelector('.monaco-editor');
        if (!editorEl) return { error: 'no monaco editor' };
        let container = editorEl;
        while (container && !container.getAttribute('data-dialog-name') && !container.className.includes('dialog')) {
            container = container.parentElement;
        }
        const root = container || document;
        const btns = Array.from(root.querySelectorAll('button, [role="button"]')).map(b => ({
            text: (b.innerText || '').trim(),
            title: b.getAttribute('title') || '',
            ariaLabel: b.getAttribute('aria-label') || '',
            dataName: b.getAttribute('data-name') || ''
        })).filter(b => b.text || b.title || b.ariaLabel || b.dataName);
        return btns;
    })()'''
    btns = await client.eval_js(js_buttons)
    print("Editor buttons:", json.dumps(btns, indent=2))
    await client.close()

if __name__ == "__main__":
    asyncio.run(main())
