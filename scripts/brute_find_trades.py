import asyncio, json, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import runner
sys.stdout.reconfigure(encoding='utf-8')
async def main():
    ws_url = runner.get_ws_url()
    client = runner.CDPClient(ws_url)
    await client.connect()
    await client.find_tradingview_target()
    # Find all clickable tabs in bottom that could be List of Trades
    js = """(() => {
        const bottom = document.querySelector('.layout__area--bottom');
        if (!bottom) return {err:'no bottom'};
        const candidates = Array.from(bottom.querySelectorAll('button, [role="tab"]')).map(b=>({
            text:(b.innerText||b.getAttribute('aria-label')||b.title||'').trim().slice(0,60),
            id:b.id||'',
            cls:(b.className||'').toString().slice(0,60),
            html: b.outerHTML.slice(0,500)
        })).filter(c=>c.text.length>0);
        return {candidates};
    })()"""
    res = await client.eval_js(js)
    print(json.dumps(res, indent=2, ensure_ascii=False))
    # Try clicking each candidate that looks like it could be trades-related, and check for table appearance
    for idx, cand in enumerate(res.get('candidates', [])[:15]):
        txt = cand['text']
        if txt in ['Breakdown','Periodical','Benchmarking','Margin usage','Growth and decline','Distribution','Streaks','Time patterns','More','By signals','By side']:
            continue
        print(f"Trying click on {txt} idx {idx}")
        js_click = f"""(() => {{
            const bottom = document.querySelector('.layout__area--bottom');
            const btn = Array.from(bottom.querySelectorAll('button, [role="tab"]')).find(b=> (b.innerText||'').trim()==='{txt}');
            if (btn) {{ btn.click(); return 'clicked ' + btn.innerText.slice(0,80); }}
            return 'not found';
        }})()"""
        await client.eval_js(js_click)
        await asyncio.sleep(1.5)
        js_check = """(() => {
            const bottom = document.querySelector('.layout__area--bottom');
            const tables = Array.from(bottom.querySelectorAll('table')).map(t=>t.innerText.slice(0,500).replace(/\\n+/g,' | '));
            const hasList = document.body.innerText.includes('List of Trades');
            const hasTradeHash = /Trade\\s*#/i.test(bottom.innerText);
            const hasEntry = /Entry/i.test(bottom.innerText);
            return {hasList, hasTradeHash, hasEntry, tables: tables.slice(0,5), snippet: bottom.innerText.slice(0,1500).replace(/\\n+/g,' | ')};
        })()"""
        check = await client.eval_js(js_check)
        print(f"  -> check: hasList={check['hasList']} hasTradeHash={check['hasTradeHash']} hasEntry={check['hasEntry']} tables={len(check['tables'])} snippet={check['snippet'][:300]}")
        if check['hasList'] or check['hasTradeHash']:
            print(f"FOUND List of Trades via {txt}")
            break
    # Also try clicking the footer tabs for List of Trades directly via global search
    js2 = """(() => {
        // Try to find any element that could be List of Trades tab hidden in dropdown
        const all = Array.from(document.querySelectorAll('*')).filter(el=>{
            const t=(el.innerText||'').trim();
            return t==='List of Trades' || t==='Trades' || t==='Closed trades';
        });
        return all.map(el=>({text:el.innerText.slice(0,100), tag:el.tagName, cls:(el.className||'').toString().slice(0,60), parent: el.parentElement?el.parentElement.innerText.slice(0,200):''}));
    })()"""
    res2 = await client.eval_js(js2)
    print("global List search:", json.dumps(res2, indent=2, ensure_ascii=False))
    await client.close()
asyncio.run(main())
