import asyncio, json, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import runner
sys.stdout.reconfigure(encoding='utf-8')
async def main():
    ws_url = runner.get_ws_url()
    client = runner.CDPClient(ws_url)
    await client.connect()
    await client.find_tradingview_target()
    # Open title menu
    await client.eval_js("""(() => { const btn=document.querySelector('[data-qa-id="pine-script-title-button"]'); if(btn && btn.getAttribute('aria-expanded')==='false') btn.click(); return 'clicked'; })()""")
    await asyncio.sleep(1.2)
    # Click Create new
    js = """(() => {
        const menu = document.getElementById(':rni:') || document.querySelector('[id=":rni:"]');
        if (!menu) return 'no menu :rni';
        const items = Array.from(menu.querySelectorAll('[role="menuitem"]'));
        const createNew = items.find(el=> /Create new/i.test(el.innerText||el.getAttribute('aria-label')||''));
        if (!createNew) return 'no Create new, items=' + items.map(i=>i.innerText.slice(0,50)).join(' | ');
        // Hover to open submenu? Try click then hover
        createNew.dispatchEvent(new MouseEvent('mouseover', {bubbles:true}));
        createNew.click();
        return 'clicked Create new: ' + createNew.innerText.slice(0,100);
    })()"""
    res = await client.eval_js(js)
    print("create new click:", res)
    await asyncio.sleep(1.5)
    js2 = """(() => {
        // Find submenu for Create new (likely with id like :rt1: or near)
        const allMenus = Array.from(document.querySelectorAll('[role="menu"]'));
        const sub = allMenus.find(m=> /Blank indicator|Blank strategy|Default/i.test(m.innerText||''));
        if (sub) return {found:true, id:sub.id, text:sub.innerText.slice(0,1000), html:sub.outerHTML.slice(0,3000)};
        // Also check all elements after click
        const all = Array.from(document.querySelectorAll('[role="menuitem"]')).map(e=>({text:(e.innerText||e.getAttribute('aria-label')||'').slice(0,120), id:e.id}));
        const bodyMenus = Array.from(document.querySelectorAll('[class*="menu-"], [class*="positioner-"]')).map(m=>({text:m.innerText.slice(0,300), id:m.id, cls:(m.className||'').toString().slice(0,80)}));
        return {found:false, allItems: all.slice(0,40), bodyMenus: bodyMenus.slice(0,15), menusCount: allMenus.length, menusText: allMenus.map(m=>m.innerText.slice(0,200))};
    })()"""
    res2 = await client.eval_js(js2)
    print(json.dumps(res2, indent=2, ensure_ascii=False))
    await client.close()
asyncio.run(main())
