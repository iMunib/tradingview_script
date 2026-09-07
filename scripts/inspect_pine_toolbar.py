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
      const allBtns = Array.from(document.querySelectorAll('button, [role="button"], [data-name]'));
      const pineRelated = allBtns.filter(b => {
        const t = ((b.innerText||'') + '|' + (b.getAttribute('aria-label')||'') + '|' + (b.getAttribute('data-name')||'') + '|' + (b.getAttribute('title')||'')).toLowerCase();
        return /pine|editor|new|open|save|add to chart|update|publish/.test(t);
      }).map(b => ({
        text: (b.innerText||'').trim().slice(0,80),
        title: b.getAttribute('title')||'',
        aria: b.getAttribute('aria-label')||'',
        dataName: b.getAttribute('data-name')||'',
        cls: (b.className||'').toString().slice(0,120)
      }));
      const tabs = Array.from(document.querySelectorAll('[class*="tab"]')).map(e=>({text:(e.innerText||'').slice(0,80), cls:(e.className||'').toString().slice(0,120)})).slice(0,30);
      const editorDialog = document.querySelector('[class*="dialog"]') ? document.querySelector('[class*="dialog"]').innerText.slice(0,800) : 'no dialog';
      const pineEditor = document.querySelector('.monaco-editor') ? 'has monaco' : 'no monaco';
      const addBtn = document.querySelector('[title="Add to chart"]') ? 'has Add' : 'no Add';
      const updateBtn = document.querySelector('[title="Update on chart"]') ? 'has Update' : 'no Update';
      // Look for Open dropdown
      const openDropdown = document.querySelector('[data-name="open"]');
      const openHTML = openDropdown ? openDropdown.outerHTML.slice(0,800) : 'no open btn';
      // List all data-name values
      const dataNames = Array.from(document.querySelectorAll('[data-name]')).map(e=>e.getAttribute('data-name')).slice(0,50);
      return {pineRelated: pineRelated.slice(0,60), tabs: tabs.slice(0,20), editorDialog: editorDialog, pineEditor, addBtn, updateBtn, openHTML, dataNames};
    })()"""
    res = await client.eval_js(js)
    print(json.dumps(res, indent=2, ensure_ascii=False))
    await client.close()
asyncio.run(main())
