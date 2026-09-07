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
        const bottom = document.querySelector('.layout__area--bottom');
        if (!bottom) return {err:'no bottom'};
        const tabs = Array.from(bottom.querySelectorAll('[role="tab"], button, [class*="tab"]')).map(el=>({
            text:(el.innerText||el.getAttribute('aria-label')||el.title||'').trim().slice(0,120),
            role:el.getAttribute('role')||'',
            cls:(el.className||'').toString().slice(0,80),
            selected: el.getAttribute('aria-selected')||el.className.includes('selected')||false,
            html: el.outerHTML.slice(0,600)
        }));
        const tabTexts = tabs.filter(t=>t.text.length>0 && t.text.length<120).slice(0,40);
        // Also look for List of Trades specifically
        const listTab = Array.from(bottom.querySelectorAll('*')).filter(el=> /List of Trades/i.test(el.innerText||'' )).map(el=>({text:el.innerText.slice(0,300), tag:el.tagName, cls:(el.className||'').toString().slice(0,80), html:el.outerHTML.slice(0,1000)}));
        const bottomInner = bottom.innerHTML.slice(0,4000);
        return {tabTexts, listTab: listTab.slice(0,10), bottomInnerSnippet: bottomInner.slice(0,2000)};
    })()"""
    res = await client.eval_js(js)
    print(json.dumps(res, indent=2, ensure_ascii=False))
    await client.close()
asyncio.run(main())
