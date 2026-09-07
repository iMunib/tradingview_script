import asyncio, json, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import runner
sys.stdout.reconfigure(encoding='utf-8')
async def main():
    ws_url = runner.get_ws_url()
    client = runner.CDPClient(ws_url)
    await client.connect()
    await client.find_tradingview_target()
    js = """(() => {
        const dlg = document.querySelector('[data-name="broker-login-dialog"]');
        if (!dlg) return {err:'no dlg'};
        const btn = dlg.querySelector('button[name="broker-login-submit-button"]');
        const allBtns = Array.from(dlg.querySelectorAll('button')).map(b=>({text:b.innerText.slice(0,80), name:b.getAttribute('name')||'', disabled:b.disabled, cls:(b.className||'').toString().slice(0,80), type:b.type}));
        const form = dlg.querySelector('form');
        const formHtml = form ? form.outerHTML.slice(0,1200) : 'no form';
        const dlgText = dlg.innerText.slice(0,800);
        // Check for any input
        const inputs = Array.from(dlg.querySelectorAll('input')).map(i=>({name:i.name, type:i.type, value:i.value, placeholder:i.placeholder}));
        return {dlgText, allBtns, formHtml, inputs, btnDisabled: btn?btn.disabled:null};
    })()"""
    res = await client.eval_js(js)
    print(json.dumps(res, indent=2, ensure_ascii=False))
    await client.close()
asyncio.run(main())
