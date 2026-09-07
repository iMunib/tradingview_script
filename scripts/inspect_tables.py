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
        // Find all tables
        const tables = Array.from(bottom.querySelectorAll('table, [role="table"], [class*="table"]')).map(t=>({
            tag: t.tagName,
            cls: (t.className||'').toString().slice(0,80),
            text: t.innerText.slice(0,800).replace(/\\n+/g,' | '),
            html: t.outerHTML.slice(0,1500)
        }));
        // Find all elements with "Trade" in them inside bottom
        const tradeEls = Array.from(bottom.querySelectorAll('*')).filter(el=>{
            const txt = (el.innerText||'');
            return txt.length>0 && txt.length<300 && /Trade|Closed|Profit|Entry|Exit/i.test(txt) && el.children.length<3;
        }).map(el=>({tag:el.tagName, text: el.innerText.slice(0,200).replace(/\\n+/g,' | '), cls:(el.className||'').toString().slice(0,60)}));
        // Look for specific tab that might be List of Trades hidden under dropdown
        const allBtnsInBottom = Array.from(bottom.querySelectorAll('button')).map(b=>({text:(b.innerText||'').slice(0,60), aria:b.getAttribute('aria-label')||'', title:b.title||'', cls:(b.className||'').toString().slice(0,60)}));
        return {tables: tables.slice(0,10), tradeEls: tradeEls.slice(0,20), btns: allBtnsInBottom.slice(0,40)};
    })()"""
    res = await client.eval_js(js)
    print(json.dumps(res, indent=2, ensure_ascii=False))
    await client.close()
asyncio.run(main())
