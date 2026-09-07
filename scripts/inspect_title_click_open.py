import asyncio, json, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import runner
sys.stdout.reconfigure(encoding='utf-8')
async def main():
    ws_url = runner.get_ws_url()
    client = runner.CDPClient(ws_url)
    await client.connect()
    await client.find_tradingview_target()
    js_click = """(() => {
        const btn = document.querySelector('[data-qa-id="pine-script-title-button"]');
        if (btn) btn.click();
        return btn ? btn.getAttribute('aria-expanded') : 'no btn';
    })()"""
    res = await client.eval_js(js_click)
    print("clicked title, expanded:", res)
    await asyncio.sleep(1.5)
    js = """(() => {
        const titleBtn = document.querySelector('[data-qa-id="pine-script-title-button"]');
        const controls = titleBtn ? titleBtn.getAttribute('aria-controls') : null;
        const menu = controls ? document.getElementById(controls) : null;
        const getMenu = (el) => el ? {id: el.id, cls:(el.className||'').toString().slice(0,100), text: el.innerText.slice(0,5000).replace(/\\n+/g,' | '), html: el.outerHTML.slice(0,6000)} : null;
        const titleMenu = getMenu(menu);
        // Also search for any element containing New default
        const newItems = Array.from(document.querySelectorAll('*')).filter(el=> {
            const t = (el.innerText||'').trim();
            return t.length<200 && /New default|New blank|Untitled script/i.test(t);
        }).map(el=>({tag:el.tagName, text:el.innerText.slice(0,200), cls:(el.className||'').toString().slice(0,80), html:el.outerHTML.slice(0,1000)}));
        const allMenus = Array.from(document.querySelectorAll('[role="menu"], [role="listbox"], [class*="menu-"]')).map(m=>({id:m.id, role:m.getAttribute('role'), text:m.innerText.slice(0,800), cls:(m.className||'').toString().slice(0,80)}));
        return {titleMenu, newItems: newItems.slice(0,20), allMenus: allMenus.slice(0,15)};
    })()"""
    res2 = await client.eval_js(js)
    print(json.dumps(res2, indent=2, ensure_ascii=False))
    await client.close()
asyncio.run(main())
