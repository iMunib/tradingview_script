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
        const allDataName = Array.from(document.querySelectorAll('[data-name]')).map(e=>({name:e.getAttribute('data-name'), text:(e.innerText||'').slice(0,80).replace(/\\n+/g,' | '), tag:e.tagName, cls:(e.className||'').toString().slice(0,80)}));
        const allWithTrading = Array.from(document.querySelectorAll('*')).filter(el=> {
            const t = (el.innerText||'') + '|' + (el.getAttribute('aria-label')||'') + '|' + (el.getAttribute('data-name')||'') + '|' + (el.title||'');
            return /Trading|Paper|Broker/i.test(t);
        }).map(el=>({text:(el.innerText||'').slice(0,200).replace(/\\n+/g,' | '), aria:el.getAttribute('aria-label')||'', name:el.getAttribute('data-name')||'', title:el.title||'', tag:el.tagName, cls:(el.className||'').toString().slice(0,80), html:el.outerHTML.slice(0,800)}));
        // Find bottom bar tabs
        const bottomBtns = Array.from(document.querySelectorAll('[class*="tab"] button, [class*="bottom"] button, [class*="panel"] button')).map(b=>({text:(b.innerText||'').slice(0,60), aria:b.getAttribute('aria-label')||'', name:b.getAttribute('data-name')||'', cls:(b.className||'').toString().slice(0,60)}));
        // Also check for footer
        const foot = document.querySelector('footer') ? document.querySelector('footer').innerText.slice(0,1000) : 'no footer';
        const panelArea = document.querySelector('[class*="bottom"]') ? document.querySelector('[class*="bottom"]').innerText.slice(0,1000) : 'no bottom class';
        // Try to find trading panel via evaluate that tradingView exposes
        const hasTradingPanel = !!document.querySelector('[data-name="trading-panel"]') || !!document.querySelector('[class*="trading"]');
        return {allDataName: allDataName.slice(0,80), allWithTrading: allWithTrading.slice(0,20), bottomBtns: bottomBtns.slice(0,30), foot, panelArea, hasTradingPanel};
    })()"""
    res = await client.eval_js(js)
    print(json.dumps(res, indent=2, ensure_ascii=False))
    await client.close()
asyncio.run(main())
