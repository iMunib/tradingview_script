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
        const titleBtn = document.querySelector('[data-qa-id="pine-script-title-button"]');
        const moreBtn = document.querySelector('[data-qa-id="script-more-options"]');
        const info = {
            titleAriaExpanded: titleBtn ? titleBtn.getAttribute('aria-expanded') : 'no titleBtn',
            titleControls: titleBtn ? titleBtn.getAttribute('aria-controls') : null,
            moreAriaExpanded: moreBtn ? moreBtn.getAttribute('aria-expanded') : 'no moreBtn',
            moreControls: moreBtn ? moreBtn.getAttribute('aria-controls') : null
        };
        // Click title
        if (titleBtn) titleBtn.click();
        return info;
    })()"""
    res = await client.eval_js(js)
    print("before click info:", json.dumps(res, indent=2, ensure_ascii=False))
    await asyncio.sleep(1.2)
    js2 = """(() => {
        const titleBtn = document.querySelector('[data-qa-id="pine-script-title-button"]');
        const moreBtn = document.querySelector('[data-qa-id="script-more-options"]');
        const after = {
            titleExpanded: titleBtn ? titleBtn.getAttribute('aria-expanded') : null,
            moreExpanded: moreBtn ? moreBtn.getAttribute('aria-expanded') : null
        };
        // Try to find controls elements
        const titleControlsId = titleBtn ? titleBtn.getAttribute('aria-controls') : null;
        const moreControlsId = moreBtn ? moreBtn.getAttribute('aria-controls') : null;
        const titleMenu = titleControlsId ? document.getElementById(titleControlsId) : null;
        const moreMenu = moreControlsId ? document.getElementById(moreControlsId) : null;
        const scan = (el) => el ? {id: el.id, tag: el.tagName, cls: (el.className||'').toString().slice(0,100), text: el.innerText.slice(0,800).replace(/\\n+/g,' | '), html: el.outerHTML.slice(0,1500)} : null;
        // Also find any element with role menu that is visible
        const allMenus = Array.from(document.querySelectorAll('[role="menu"], [role="listbox"]')).map(m=>({id:m.id, role:m.getAttribute('role'), text:m.innerText.slice(0,400), html:m.outerHTML.slice(0,1200)}));
        return {after, titleMenu: scan(titleMenu), moreMenu: scan(moreMenu), allMenus: allMenus.slice(0,10)};
    })()"""
    res2 = await client.eval_js(js2)
    print(json.dumps(res2, indent=2, ensure_ascii=False))
    # Now try clicking moreBtn as second step
    js3 = """(() => {
        const moreBtn = document.querySelector('[data-qa-id="script-more-options"]');
        if (moreBtn) moreBtn.click();
        return moreBtn ? moreBtn.getAttribute('aria-expanded') : 'no btn';
    })()"""
    res3 = await client.eval_js(js3)
    print("clicked moreBtn expanded:", res3)
    await asyncio.sleep(1.2)
    js4 = """(() => {
        const moreBtn = document.querySelector('[data-qa-id="script-more-options"]');
        const moreControlsId = moreBtn ? moreBtn.getAttribute('aria-controls') : null;
        const moreMenu = moreControlsId ? document.getElementById(moreControlsId) : null;
        const scan = (el) => el ? {id: el.id, tag: el.tagName, cls: (el.className||'').toString().slice(0,100), text: el.innerText.slice(0,800).replace(/\\n+/g,' | '), html: el.outerHTML.slice(0,2000)} : null;
        const allMenus = Array.from(document.querySelectorAll('[role="menu"], [role="listbox"]')).map(m=>({id:m.id, role:m.getAttribute('role'), text:m.innerText.slice(0,600), html:m.outerHTML.slice(0,1500)}));
        const bodyMenus = Array.from(document.querySelectorAll('[class*="menuBox"]')).map(m=>({text:m.innerText.slice(0,600), html:m.outerHTML.slice(0,1500)}));
        return {moreMenu: scan(moreMenu), allMenus: allMenus.slice(0,10), bodyMenus: bodyMenus.slice(0,5)};
    })()"""
    res4 = await client.eval_js(js4)
    print(json.dumps(res4, indent=2, ensure_ascii=False))
    await client.close()
asyncio.run(main())
