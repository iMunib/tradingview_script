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
        const allBtns = Array.from(document.querySelectorAll('button, [role="button"], a'));
        const tradeBtns = allBtns.filter(b=>{
            const t = (b.innerText||b.getAttribute('aria-label')||b.title||'').toLowerCase();
            return /trade|trading|strategy tester|pine/.test(t);
        }).map(b=>({
            text:(b.innerText||'').trim().slice(0,100),
            aria:b.getAttribute('aria-label')||'',
            title:b.title||'',
            dataName:b.getAttribute('data-name')||'',
            cls:(b.className||'').toString().slice(0,120),
            html:b.outerHTML.slice(0,900)
        }));
        // Also find header area with Unnamed Save Trade Publish
        const header = document.querySelector('[data-qa-id="chart-page-grid-area"]');
        const headerText = header ? header.innerText.slice(0,2000).replace(/\\n+/g,' | ') : 'no header';
        // Look for footer with trading panel tabs
        const footerCandidates = Array.from(document.querySelectorAll('div')).filter(d=>{
            const t = d.innerText||'';
            return t.includes('Trading Panel') || t.includes('Paper Trading');
        }).map(d=>({text:d.innerText.slice(0,500).replace(/\\n+/g,' | '), cls:(d.className||'').toString().slice(0,80), html:d.outerHTML.slice(0,1200)}));
        // Try to find any element with id containing bottom or footer
        const bottomEls = Array.from(document.querySelectorAll('[class*="bottom"], [class*="footer"], [class*="panel-"], [id*="bottom"]')).map(e=>({cls:(e.className||'').toString().slice(0,80), text: e.innerText.slice(0,300).replace(/\\n+/g,' | ')}));
        return {tradeBtns: tradeBtns.slice(0,30), headerText: headerText.slice(0,1000), footerCandidates: footerCandidates.slice(0,10), bottomEls: bottomEls.slice(0,20)};
    })()"""
    res = await client.eval_js(js)
    print(json.dumps(res, indent=2, ensure_ascii=False))
    await client.close()
asyncio.run(main())
