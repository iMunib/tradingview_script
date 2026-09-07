import os
import sys
import asyncio
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT_DIR)
import runner

async def main():
    ws_url = runner.get_ws_url()
    client = runner.CDPClient(ws_url)
    await client.connect()
    await client.find_tradingview_target()
    # Hardened: handles Allow/remove debugging, limit/upgrade, and save dialogs with polling — minimal user clicks
    js = """(() => {
        const dialogs = Array.from(document.querySelectorAll('[class*="dialog"], [class*="modal"], [class*="popup"], [role="dialog"], [class*="toast"], [class*="notification"]'));
        const allowDialog = dialogs.find(d => /allow|remove.*debug|confirm.*remove|delete.*script|do you want to remove/i.test(d.innerText || ''));
        if (allowDialog) {
            const btn = Array.from(allowDialog.querySelectorAll('button')).find(b=> /^allow$/i.test((b.innerText||'').trim()) || /allow|confirm|yes|remove/i.test(b.innerText||'') && !/cancel|deny/i.test(b.innerText||''));
            if (btn) { btn.click(); return 'auto_allowed:' + btn.innerText.trim(); }
        }
        const limitDialog = dialogs.find(d => /limit reached|maximum.*indicat|upgrade.*plan|too many.*indicat|3 indicators|2 indicators/i.test(d.innerText || ''));
        if (limitDialog) {
            const closeBtn = Array.from(limitDialog.querySelectorAll('button, [data-name="close"], [aria-label="Close"]')).find(b => /close|ok|got it|dismiss|cancel/i.test(b.innerText||'') || b.getAttribute('data-name')==='close' || b.getAttribute('aria-label')==='Close');
            if (closeBtn) { closeBtn.click(); return 'dismissed_limit:' + (closeBtn.innerText||'close'); }
            const xBtn = document.querySelector('[data-name="close"], [aria-label="Close"]');
            if (xBtn) { xBtn.click(); return 'dismissed_limit_fallback'; }
        }
        const saveDialog = dialogs.find(d => /save this script|overwrite/i.test(d.innerText || ''));
        if (saveDialog) {
            const saveBtn = Array.from(saveDialog.querySelectorAll('button')).find(b=>/save|overwrite|confirm/i.test(b.innerText||''));
            if (saveBtn) { saveBtn.click(); return 'clicked_save:' + saveBtn.innerText.trim(); }
        }
        const btns = Array.from(document.querySelectorAll('button, [data-name="close"], [aria-label="Close"]'));
        const closeBtn = btns.find(b => (b.innerText || '').trim().toLowerCase() === 'close' || b.getAttribute('data-name') === 'close');
        if (closeBtn) { closeBtn.click(); return 'clicked close: ' + (closeBtn.innerText || 'data-name=close'); }
        return 'no close/limit/save button found — dialogs:' + dialogs.map(d=>d.innerText.slice(0,60)).join(' | ').slice(0,200);
    })()"""
    # Poll 6 times
    for i in range(6):
        res = await client.eval_js(js)
        print(f'[{i}] Modal Dismiss:', res)
        if isinstance(res, str) and ('no close' in res or 'no close/limit' in res):
            break
        await asyncio.sleep(0.5)
    await client.close()

if __name__ == '__main__':
    asyncio.run(main())
