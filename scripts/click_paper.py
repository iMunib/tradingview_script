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
        const paper = document.querySelector('[data-broker="Paper"]');
        if (!paper) return 'no paper';
        paper.click();
        return 'clicked paper: ' + paper.getAttribute('aria-label');
    })()"""
    res = await client.eval_js(js)
    print(res)
    await asyncio.sleep(2.5)
    js2 = """(() => {
        const body = document.body.innerText.slice(0,4000).replace(/\\n+/g,' | ');
        const dialogs = Array.from(document.querySelectorAll('[role="dialog"], [class*="dialog"]')).map(d=>({text:d.innerText.slice(0,800).replace(/\\n+/g,' | '), html:d.outerHTML.slice(0,1500)}));
        const btns = Array.from(document.querySelectorAll('button')).filter(b=>/Connect|Paper Trading|Trading Panel/i.test(b.innerText||'')).map(b=>({text:b.innerText.slice(0,80), html:b.outerHTML.slice(0,800)}));
        return {bodySnippet: body.slice(0,1500), dialogs: dialogs.slice(0,5), btns: btns.slice(0,10)};
    })()"""
    res2 = await client.eval_js(js2)
    print(json.dumps(res2, indent=2, ensure_ascii=False))
    await client.close()
asyncio.run(main())
