import asyncio
import json
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import runner

async def handle():
    ws_url = runner.get_ws_url()
    client = runner.CDPClient(ws_url)
    await client.connect()
    await client.find_tradingview_target()
    # Hardened handler: polls for save/overwrite, 2-indicator limit, AND Allow/remove debugging — auto-clicks to keep zero-click flow
    handler_js = """(() => {
        const dialogs = Array.from(document.querySelectorAll('[class*="dialog"], [class*="modal"], [class*="popup"], [role="dialog"]'));
        const allBtns = Array.from(document.querySelectorAll('button, [data-name="close"]'));
        // 0) Allow / Remove debugging — auto-allow (user requested minimal prompts)
        const allowDialog = dialogs.find(d => /allow|remove.*debug|confirm.*remove|delete.*script|do you want to remove/i.test(d.innerText || ''));
        if (allowDialog) {
            const cands = Array.from(allowDialog.querySelectorAll('button'));
            const allowBtn = cands.find(b => /^allow$/i.test((b.innerText||'').trim())) || cands.find(b => /allow|confirm|yes|remove|delete/i.test(b.innerText||'') && !/cancel|deny|close/i.test(b.innerText||''));
            if (allowBtn && !allowBtn.disabled) { allowBtn.click(); return 'Auto-allowed: ' + (allowBtn.innerText||'').trim(); }
        }
        const globalAllow = allBtns.find(b => /^allow$/i.test((b.innerText||'').trim()) && b.offsetParent !== null);
        if (globalAllow) {
            const p = globalAllow.closest('[class*="dialog"], [class*="modal"]');
            if (p && /allow|remove|debug/i.test(p.innerText||'')) { globalAllow.click(); return 'Auto-allowed global'; }
        }
        // 1) Save / Overwrite dialog
        const saveDialog = dialogs.find(d => /save this script|save.*script|overwrite/i.test(d.innerText || ''));
        if (saveDialog) {
            const btns = Array.from(saveDialog.querySelectorAll('button'));
            const saveBtn = btns.find(b => /^save$/i.test((b.innerText||'').trim())) ||
                            btns.find(b => /overwrite/i.test(b.innerText||'')) ||
                            btns.find(b => /save &/i.test(b.innerText||'')) ||
                            btns.find(b => /confirm|yes/i.test(b.innerText||''));
            if (saveBtn && !saveBtn.disabled) { saveBtn.click(); return 'Clicked Save: ' + (saveBtn.innerText||'').trim(); }
            return 'Save dialog found, no button: ' + saveDialog.innerText.slice(0,120);
        }
        // 2) 2-indicator limit / upgrade modal
        const limitDialog = dialogs.find(d => /limit reached|maximum.*indicat|upgrade.*plan|too many.*indicat|3 indicators|2 indicators/i.test(d.innerText || ''));
        if (limitDialog) {
            const closeBtn = Array.from(limitDialog.querySelectorAll('button, [data-name="close"]')).find(b => /close|ok|got it|dismiss|cancel/i.test(b.innerText||'') || b.getAttribute('data-name')==='close');
            if (closeBtn) { closeBtn.click(); return 'Dismissed limit modal: ' + (closeBtn.innerText||'close'); }
            const xBtn = document.querySelector('[data-name="close"], [aria-label="Close"]');
            if (xBtn) { xBtn.click(); return 'Dismissed limit fallback X'; }
            return 'Limit dialog found, no close button';
        }
        // 3) Any visible dialog with buttons — try close for blocking overlays
        if (dialogs.length) {
            const visible = dialogs.find(d => d.offsetParent !== null);
            if (visible) return 'Dialog present: ' + visible.innerText.slice(0,150).replace(/\\n/g,' | ');
        }
        return 'No save/limit dialog found';
    })()"""
    # Poll for up to 8 seconds to catch delayed modals
    final_res = 'No dialog'
    for i in range(16):
        res = await client.eval_js(handler_js)
        print(f"[{i}] Dialog handler result:", res)
        final_res = res
        if isinstance(res, str) and ('Clicked Save' in res or 'Dismissed limit' in res or 'Auto-allowed' in res):
            await asyncio.sleep(0.6)
            continue
        if res == 'No save/limit dialog found':
            if i >= 2:
                break
        await asyncio.sleep(0.5)
    print("Final dialog handler result:", final_res)
    await asyncio.sleep(1)
    await client.close()

if __name__ == '__main__':
    asyncio.run(handle())
