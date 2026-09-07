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
            titleExpanded: titleBtn ? titleBtn.getAttribute('aria-expanded') : null,
            titleControls: titleBtn ? titleBtn.getAttribute('aria-controls') : null,
            moreExpanded: moreBtn ? moreBtn.getAttribute('aria-expanded') : null,
            moreControls: moreBtn ? moreBtn.getAttribute('aria-controls') : null
        };
        const getMenu = (id) => {
            if (!id) return null;
            const el = document.getElementById(id);
            if (!el) return null;
            return {
                id: el.id,
                cls: (el.className||'').toString().slice(0,100),
                text: el.innerText.slice(0,3000).replace(/\\n+/g,' | '),
                html: el.outerHTML.slice(0,4000)
            };
        };
        const titleMenu = getMenu(info.titleControls);
        const moreMenu = getMenu(info.moreControls);
        // Also try to find any menu with script list
        const scriptList = Array.from(document.querySelectorAll('[class*="menu-"], [class*="list-"]')).filter(el=>/All-in-One|Untitled|New blank|New default/i.test(el.innerText||'')).map(el=>({text:el.innerText.slice(0,800), cls:(el.className||'').toString().slice(0,80), html:el.outerHTML.slice(0,2000)}));
        return {info, titleMenu, moreMenu, scriptList: scriptList.slice(0,10)};
    })()"""
    res = await client.eval_js(js)
    print(json.dumps(res, indent=2, ensure_ascii=False))
    await client.close()
asyncio.run(main())
