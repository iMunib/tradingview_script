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
        // Try to find More button in bottom Strategy Tester
        const moreBtn = Array.from(document.querySelectorAll('button')).find(b=> b.innerText.trim()==='More' && b.closest('.layout__area--bottom'));
        if (!moreBtn) return {err:'no More btn in bottom', allMore: Array.from(document.querySelectorAll('button')).filter(b=>b.innerText.trim()==='More').map(b=>({text:b.innerText, cls:b.className.slice(0,80), parent: b.closest('.layout__area--bottom')?'in bottom':'outside'}))};
        const rect = moreBtn.getBoundingClientRect();
        return {found:true, text:moreBtn.innerText, cls:moreBtn.className.slice(0,80), rect:{x:rect.x,y:rect.y,w:rect.width,h:rect.height}, html:moreBtn.outerHTML.slice(0,800)};
    })()"""
    res = await client.eval_js(js)
    print(json.dumps(res, indent=2, ensure_ascii=False))
    # Click More
    await client.eval_js("""(() => {
        const btn = Array.from(document.querySelectorAll('button')).find(b=> b.innerText.trim()==='More' && b.closest('.layout__area--bottom'));
        if (btn) btn.click();
        return !!btn;
    })()""")
    await asyncio.sleep(1.5)
    js2 = """(() => {
        const menus = Array.from(document.querySelectorAll('[role="menu"]'));
        const items = menus.map(m=>({id:m.id, text:m.innerText.slice(0,1000).replace(/\\n+/g,' | '), html:m.outerHTML.slice(0,2000)}));
        const allWithList = Array.from(document.querySelectorAll('*')).filter(el=> /List of Trades/i.test(el.innerText||'') ).map(el=>({text:el.innerText.slice(0,400), tag:el.tagName, cls:(el.className||'').toString().slice(0,80)}));
        return {menus: items.slice(0,10), list: allWithList.slice(0,10)};
    })()"""
    res2 = await client.eval_js(js2)
    print(json.dumps(res2, indent=2, ensure_ascii=False))
    await client.close()
asyncio.run(main())
