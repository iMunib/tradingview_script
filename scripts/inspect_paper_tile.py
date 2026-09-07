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
        const dlg = document.querySelector('[data-name="select-broker-dialog"]');
        if (!dlg) return {err:'no dialog'};
        const text = dlg.innerText.slice(0,3000).replace(/\\n+/g,' | ');
        const btns = Array.from(dlg.querySelectorAll('button')).map(b=>({text:(b.innerText||b.getAttribute('aria-label')||'').slice(0,100), cls:(b.className||'').toString().slice(0,80), html:b.outerHTML.slice(0,800)}));
        // Find Paper Trading specific
        const paperSection = Array.from(dlg.querySelectorAll('*')).find(el=> (el.innerText||'').includes('Paper Trading') && el.innerText.length<500);
        const paperHtml = paperSection ? paperSection.outerHTML.slice(0,2000) : 'no paperSection';
        const paperTiles = Array.from(dlg.querySelectorAll('[class*="broker"] , [class*="tile"] , [role="listitem"]')).slice(0,10).map(el=>({text:el.innerText.slice(0,300), cls:(el.className||'').toString().slice(0,80), html:el.outerHTML.slice(0,1000)}));
        return {text, btns: btns.slice(0,20), paperHtml, paperTiles};
    })()"""
    res = await client.eval_js(js)
    print(json.dumps(res, indent=2, ensure_ascii=False))
    await client.close()
asyncio.run(main())
