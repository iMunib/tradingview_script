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
        // click title again if menu not open
        const btn = document.querySelector('[data-qa-id="pine-script-title-button"]');
        if (btn) btn.click();
        return 'clicked';
    })()"""
    await client.eval_js(js)
    await asyncio.sleep(1.2)
    js2 = """(() => {
        // Scan all visible menus/popups after click
        const all = Array.from(document.querySelectorAll('*')).filter(el => {
            const style = window.getComputedStyle(el);
            return style.display !== 'none' && style.visibility !== 'hidden' && el.offsetParent !== null;
        });
        const texts = all.filter(el => el.innerText && el.innerText.length>0 && el.innerText.length<300).map(el=>({tag:el.tagName, cls:(el.className||'').toString().slice(0,80), text:el.innerText.slice(0,200).replace(/\\n+/g,' | ')}));
        // Find elements containing 'New' or 'Blank' or 'Default'
        const newItems = texts.filter(t=>/New|Blank|Default|Create|Untitled/i.test(t.text));
        // Also raw body
        const bodyMenus = Array.from(document.querySelectorAll('[class*="menu-"], [class*="popup-"], [role="menu"]')).map(m=>({html:m.outerHTML.slice(0,1500), text:m.innerText.slice(0,500)}));
        return {newItems: newItems.slice(0,30), bodyMenus: bodyMenus.slice(0,10), totalVisible: texts.length};
    })()"""
    res = await client.eval_js(js2)
    print(json.dumps(res, indent=2, ensure_ascii=False))
    await client.close()
asyncio.run(main())
