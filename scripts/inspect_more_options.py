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
        const btn = document.querySelector('[data-qa-id="script-more-options"]');
        if (!btn) return 'no more btn';
        btn.click();
        return 'clicked more';
    })()"""
    res = await client.eval_js(js)
    print("step1:", res)
    await asyncio.sleep(1.2)
    js2 = """(() => {
        const items = Array.from(document.querySelectorAll('[role="menuitem"], [class*="item"], [class*="menu-"]')).map(e=>({text:(e.innerText||'').slice(0,150), cls:(e.className||'').toString().slice(0,120), qa: e.getAttribute('data-qa-id')||'', role:e.getAttribute('role')||''}));
        const menus = Array.from(document.querySelectorAll('[class*="menuBox"], [class*="popupItem"], [data-qa-id*="menu"]')).map(m=>({html:m.outerHTML.slice(0,1200), text:m.innerText.slice(0,800)}));
        // Also check dialog overlay
        const overlays = Array.from(document.querySelectorAll('[class*="menu-"], [class*="list-"], [role="listbox"]')).map(e=>({text:e.innerText.slice(0,400), html:e.outerHTML.slice(0,1200)}));
        const bodyText = document.body.innerText.slice(0,3000);
        return {items: items.slice(0,60), menus: menus.slice(0,10), overlays: overlays.slice(0,10), bodySnippet: bodyText.slice(0,1000)};
    })()"""
    res2 = await client.eval_js(js2)
    print(json.dumps(res2, indent=2, ensure_ascii=False))
    # Try to find New default script
    js3 = """(() => {
        const all = Array.from(document.querySelectorAll('*')).filter(e=>/New default script|New blank|Open default/i.test(e.innerText||''));
        return all.map(e=>({text:e.innerText.slice(0,200), tag:e.tagName, cls:(e.className||'').toString().slice(0,80), html:e.outerHTML.slice(0,800)}));
    })()"""
    res3 = await client.eval_js(js3)
    print("newCandidates:", json.dumps(res3, indent=2, ensure_ascii=False))
    await client.close()
asyncio.run(main())
