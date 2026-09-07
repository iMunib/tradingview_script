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
        // Find bottom bar tabs
        const allBtns = Array.from(document.querySelectorAll('button, [role="button"], [data-name]'));
        const panelBtns = allBtns.filter(b => {
            const txt = (b.innerText||b.getAttribute('aria-label')||b.getAttribute('data-name')||b.title||'').toLowerCase();
            return /trading panel|trading|paper trading|strategy tester|pine editor|watchlist/i.test(txt);
        }).map(b=>({
            text: (b.innerText||'').trim().slice(0,80),
            aria: b.getAttribute('aria-label')||'',
            dataName: b.getAttribute('data-name')||'',
            title: b.getAttribute('title')||'',
            cls: (b.className||'').toString().slice(0,120),
            html: b.outerHTML.slice(0,800)
        }));
        // Also find bottom bar specific
        const bottomBar = document.querySelector('[class*="bottomBar"], [class*="footer"], [class*="panel"]');
        const bottomText = bottomBar ? bottomBar.innerText.slice(0,2000).replace(/\\n+/g,' | ') : 'no bottomBar';
        const tradingPanelBtn = document.querySelector('button[data-name="trading-panel"]') || Array.from(document.querySelectorAll('button')).find(b=> /trading panel/i.test(b.innerText||b.getAttribute('aria-label')||''));
        const tpHtml = tradingPanelBtn ? tradingPanelBtn.outerHTML.slice(0,1000) : 'no trading-panel btn';
        // Find Paper Trading tile
        const paperTiles = Array.from(document.querySelectorAll('*')).filter(el=> /Paper Trading/i.test(el.innerText||'') && el.children.length<10).map(el=>({text:el.innerText.slice(0,400).replace(/\\n+/g,' | '), tag:el.tagName, cls:(el.className||'').toString().slice(0,80), html:el.outerHTML.slice(0,1000)}));
        const bodySnippet = document.body.innerText.slice(0,3000).replace(/\\n+/g,' | ');
        return {panelBtns: panelBtns.slice(0,40), bottomText, tpHtml, paperTiles: paperTiles.slice(0,10), bodySnippet: bodySnippet.slice(0,1000)};
    })()"""
    res = await client.eval_js(js)
    print(json.dumps(res, indent=2, ensure_ascii=False))
    await client.close()
asyncio.run(main())
