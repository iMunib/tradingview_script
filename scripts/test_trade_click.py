import asyncio, json, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import runner
sys.stdout.reconfigure(encoding='utf-8')
async def main():
    ws_url = runner.get_ws_url()
    client = runner.CDPClient(ws_url)
    await client.connect()
    await client.find_tradingview_target()
    # Click Trade button
    js = """(() => {
        const tradeBtn = document.querySelector('[data-qa-id="trade-button"]');
        if (!tradeBtn) return 'no tradeBtn';
        tradeBtn.click();
        return 'clicked trade: ' + tradeBtn.innerText.slice(0,80);
    })()"""
    res = await client.eval_js(js)
    print(res)
    await asyncio.sleep(2.5)
    js2 = """(() => {
        const bottom = document.querySelector('.layout__area--bottom');
        const bottomText = bottom ? bottom.innerText.slice(0,3000).replace(/\\n+/g,' | ') : 'no bottom';
        const panelTiles = Array.from(document.querySelectorAll('*')).filter(el=>{
            const t=(el.innerText||'').toLowerCase();
            return /paper trading|connect.*paper|broker|paper by tradingview/i.test(t);
        }).map(el=>({text:el.innerText.slice(0,400).replace(/\\n+/g,' | '), tag:el.tagName, cls:(el.className||'').toString().slice(0,80), html:el.outerHTML.slice(0,1200)}));
        const allData = Array.from(document.querySelectorAll('[data-name]')).map(e=>e.getAttribute('data-name')).slice(0,80);
        // Look for connect buttons
        const connectBtns = Array.from(document.querySelectorAll('button')).filter(b=>/connect/i.test(b.innerText||'')).map(b=>({text:b.innerText.slice(0,80), cls:(b.className||'').toString().slice(0,80), html:b.outerHTML.slice(0,800)}));
        return {bottomText: bottomText.slice(0,2000), panelTiles: panelTiles.slice(0,10), allData, connectBtns: connectBtns.slice(0,10)};
    })()"""
    res2 = await client.eval_js(js2)
    print(json.dumps(res2, indent=2, ensure_ascii=False))
    await client.close()
asyncio.run(main())
