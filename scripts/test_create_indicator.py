import asyncio, json, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import runner
sys.stdout.reconfigure(encoding='utf-8')
async def main():
    ws_url = runner.get_ws_url()
    client = runner.CDPClient(ws_url)
    await client.connect()
    await client.find_tradingview_target()
    # Ensure pine editor open
    await client.eval_js("""(() => { const btn=document.querySelector('[data-name="pine-dialog-button"]'); if(btn) btn.click(); return 'ok'; })()""")
    await asyncio.sleep(1.0)
    # Open title menu if not open
    await client.eval_js("""(() => { const btn=document.querySelector('[data-qa-id="pine-script-title-button"]'); if(btn && btn.getAttribute('aria-expanded')==='false') btn.click(); return 'opened'; })()""")
    await asyncio.sleep(1.0)
    # Click Create new
    await client.eval_js("""(() => {
        const menu = document.getElementById(':rni:') || document.querySelector('[role="menu"]');
        const items = menu ? Array.from(menu.querySelectorAll('[role="menuitem"]')) : [];
        const createNew = items.find(el=> /Create new/i.test(el.innerText||''));
        if (createNew) { createNew.dispatchEvent(new MouseEvent('mouseover',{bubbles:true})); return 'found'; }
        return 'not found';
    })()""")
    await asyncio.sleep(0.6)
    # Actually the Create new button id is :rsr: — click it to open submenu already did, but now click Indicator
    js = """(() => {
        const subMenu = document.getElementById(':rsq:') || Array.from(document.querySelectorAll('[role="menu"]')).find(m=>/Indicator/.test(m.innerText));
        if (!subMenu) return 'no submenu :rsq';
        const items = Array.from(subMenu.querySelectorAll('[role="menuitem"]'));
        const ind = items.find(el=> /Indicator/.test(el.innerText||''));
        if (!ind) return 'no Indicator, items=' + items.map(i=>i.innerText.slice(0,50)).join('|');
        ind.click();
        return 'clicked Indicator: ' + ind.innerText.slice(0,100);
    })()"""
    res = await client.eval_js(js)
    print("click Indicator:", res)
    await asyncio.sleep(2.5)
    # Check editor state after
    js2 = """(() => {
        const titleBtn = document.querySelector('[data-qa-id="pine-script-title-button"]');
        const title = titleBtn ? titleBtn.innerText.slice(0,120) : 'no title';
        const hasAdd = !!document.querySelector('[title="Add to chart"]');
        const hasUpdate = !!document.querySelector('[title="Update on chart"]');
        let monacoSnippet='no monaco';
        if (window._monaco && window._monaco.editor) {
            const models = window._monaco.editor.getModels();
            monacoSnippet = models[models.length-1].getValue().slice(0,300).replace(/\\n/g,' | ');
        }
        return {title, hasAdd, hasUpdate, monacoSnippet};
    })()"""
    res2 = await client.eval_js(js2)
    print(json.dumps(res2, indent=2, ensure_ascii=False))
    # Check chart sources (should still be 1, not yet added)
    js3 = """(() => {
        const coll = window._exposed_chartWidgetCollection;
        const model = coll.activeChartWidget.value().model();
        let sources=[];
        for(let p of model.panes()) for(let s of p.dataSources()) sources.push(s.title?s.title():'');
        return sources;
    })()"""
    res3 = await client.eval_js(js3)
    print("sources:", json.dumps(res3, ensure_ascii=False))
    await client.close()
asyncio.run(main())
