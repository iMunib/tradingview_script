import asyncio, json, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import runner
sys.stdout.reconfigure(encoding='utf-8')
async def main():
    ws_url = runner.get_ws_url()
    client = runner.CDPClient(ws_url)
    await client.connect()
    await client.find_tradingview_target()
    # Click title button
    js = """(() => {
        const btn = document.querySelector('[data-qa-id="pine-script-title-button"]');
        if (!btn) return 'no btn';
        btn.click();
        return 'clicked title';
    })()"""
    res = await client.eval_js(js)
    print(res)
    await asyncio.sleep(1.5)
    js2 = """(() => {
        // Check for any element that appears after click outside dialog
        const allPopups = Array.from(document.querySelectorAll('[class*="popup"], [class*="menu-"], [class*="list-"], [class*="dialog-"], [role="listbox"], [role="menu"]'));
        const popupData = allPopups.map(p=>({cls:(p.className||'').toString().slice(0,120), text:p.innerText.slice(0,600).replace(/\\n+/g,' | '), html:p.outerHTML.slice(0,1200)}));
        // Also check body for New
        const body = document.body.innerHTML;
        const newIdx = body.indexOf('New');
        const snippet = newIdx>=0 ? body.slice(Math.max(0,newIdx-500), newIdx+1000) : 'no New in body';
        // Check for data-qa-id containing script
        const qas = Array.from(document.querySelectorAll('[data-qa-id]')).map(e=>({qa:e.getAttribute('data-qa-id'), text:(e.innerText||'').slice(0,120), cls:(e.className||'').toString().slice(0,80)}));
        return {popupCount: allPopups.length, popupData: popupData.slice(0,10), qas: qas.slice(0,60), snippet: snippet.slice(0,2000)};
    })()"""
    res2 = await client.eval_js(js2)
    print(json.dumps(res2, indent=2, ensure_ascii=False))
    await client.close()
asyncio.run(main())
