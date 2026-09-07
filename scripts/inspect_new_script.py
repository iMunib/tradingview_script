import asyncio, json, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import runner
sys.stdout.reconfigure(encoding='utf-8')
async def main():
    ws_url = runner.get_ws_url()
    client = runner.CDPClient(ws_url)
    await client.connect()
    await client.find_tradingview_target()
    # Click pine script title button
    js_click = """(() => {
        const btn = document.querySelector('[data-qa-id="pine-script-title-button"]');
        if (!btn) return 'no title btn';
        btn.click();
        return 'clicked title';
    })()"""
    res = await client.eval_js(js_click)
    print("click title:", res)
    await asyncio.sleep(1.5)
    js_menu = """(() => {
        const all = Array.from(document.querySelectorAll('[role="menu"], [class*="menu"], [data-qa-id]'));
        const menuItems = Array.from(document.querySelectorAll('[role="menuitem"], [class*="item-"], [data-name]')).map(e=>({text:(e.innerText||'').slice(0,120), qa: e.getAttribute('data-qa-id')||'', role:e.getAttribute('role')||'', html:e.outerHTML.slice(0,500)}));
        const inner = document.body.innerHTML.slice(0,5000);
        return {menuItems: menuItems.slice(0,40), allCount: all.length};
    })()"""
    res2 = await client.eval_js(js_menu)
    print(json.dumps(res2, indent=2, ensure_ascii=False))
    await client.close()
asyncio.run(main())
