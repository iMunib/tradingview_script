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
        const dlg = document.querySelector('[data-name="broker-login-dialog"]');
        if (!dlg) return 'no broker-login-dialog';
        const btn = dlg.querySelector('button[name="broker-login-submit-button"]') || Array.from(dlg.querySelectorAll('button')).find(b=>/Connect/i.test(b.innerText||''));
        if (!btn) return 'no connect btn, btns=' + Array.from(dlg.querySelectorAll('button')).map(b=>b.innerText.slice(0,40)).join('|');
        btn.click();
        return 'clicked Connect: ' + btn.innerText;
    })()"""
    res = await client.eval_js(js)
    print(res)
    await asyncio.sleep(3)
    js2 = """(() => {
        const bottom = document.querySelector('.layout__area--bottom');
        const bottomText = bottom ? bottom.innerText.slice(0,4000).replace(/\\n+/g,' | ') : 'no bottom';
        // Check for Paper Trading balance
        const hasPaper = document.body.innerText.includes('Paper Trading');
        const balanceSnippet = Array.from(document.querySelectorAll('*')).filter(el=> {
            const t = (el.innerText||'');
            return /\\$100,000|\\$100 000|Paper Trading.*USD|Balance/i.test(t) && t.length<500;
        }).map(el=>({text: el.innerText.slice(0,300).replace(/\\n+/g,' | '), cls:(el.className||'').toString().slice(0,80)}));
        const dialogs = Array.from(document.querySelectorAll('[role="dialog"]')).map(d=> d.innerText.slice(0,600).replace(/\\n+/g,' | '));
        // Check trading panel header
        const tpHeader = document.querySelector('.trading-panel-header-wspftEtf');
        const tpText = tpHeader ? tpHeader.innerText.slice(0,500) : 'no tpHeader';
        // Check bottom bar for Paper Trading tab
        const tradingTab = Array.from(document.querySelectorAll('button')).find(b=> /Paper Trading/i.test(b.innerText||b.getAttribute('aria-label')||''));
        const tradingHtml = tradingTab ? tradingTab.outerHTML.slice(0,800) : 'no Paper Trading tab';
        return {bottomSnippet: bottomText.slice(0,2000), hasPaper, balanceSnippet: balanceSnippet.slice(0,10), dialogs: dialogs.slice(0,5), tpText, tradingHtml};
    })()"""
    res2 = await client.eval_js(js2)
    print(json.dumps(res2, indent=2, ensure_ascii=False))
    await client.close()
asyncio.run(main())
