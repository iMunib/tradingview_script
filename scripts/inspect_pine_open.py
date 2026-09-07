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
        const dlg = document.querySelector('[data-name="pine-dialog"]');
        if (!dlg) return {err:'no dlg'};
        const all = Array.from(dlg.querySelectorAll('*'));
        const btns = Array.from(dlg.querySelectorAll('button, a, [role="button"]')).map(b=>({
            tag: b.tagName,
            text: (b.innerText||'').slice(0,100),
            title: b.getAttribute('title')||'',
            aria: b.getAttribute('aria-label')||'',
            cls: (b.className||'').toString().slice(0,100),
            html: b.outerHTML.slice(0,400)
        }));
        const links = Array.from(dlg.querySelectorAll('a')).map(a=>({text: a.innerText.slice(0,100), href: a.getAttribute('href')||'', cls: a.className.toString().slice(0,100), html: a.outerHTML.slice(0,500)}));
        const spans = Array.from(dlg.querySelectorAll('span')).filter(s=>/restore|make a copy|historical/i.test(s.innerText||'')).map(s=>({text:s.innerText.slice(0,120), html:s.outerHTML.slice(0,400), parent: s.parentElement ? s.parentElement.outerHTML.slice(0,400): ''}));
        // Also check top bar of TradingView for Open menu outside dialog
        const openCandidates = Array.from(document.querySelectorAll('*')).filter(el=>/Open/i.test(el.innerText||'') && el.tagName==='BUTTON').slice(0,10).map(b=>({text:b.innerText.slice(0,80), html:b.outerHTML.slice(0,400)}));
        return {dlgText: dlg.innerText.slice(0,1000), btns: btns.slice(0,40), links, spans, openCandidates};
    })()"""
    res = await client.eval_js(js)
    print(json.dumps(res, indent=2, ensure_ascii=False))
    await client.close()
asyncio.run(main())
