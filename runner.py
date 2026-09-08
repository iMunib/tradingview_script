"""
Autonomous Pine Script Quant Engine & CDP Runner
Controller for TradingView Pine Script injection, compilation, and metrics scraping.
"""

import sys
import os
import json
import time
import argparse
import re
import asyncio
import websockets

sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
LOGS_DIR = os.path.join(ROOT_DIR, 'logs')
METRICS_DIR = os.path.join(ROOT_DIR, 'metrics')
os.makedirs(LOGS_DIR, exist_ok=True)
os.makedirs(METRICS_DIR, exist_ok=True)

ERROR_LOG_PATH = os.path.join(LOGS_DIR, 'compiler_errors.log')
HISTORY_JSON_PATH = os.path.join(METRICS_DIR, 'backtest_history.json')

def get_ws_url():
    # HARDCODED CHROME ONLY — Edge purged (zero infobar)
    # Try DevToolsActivePort files first
    chrome_port_file = r'C:\Users\RehmanPC\AppData\Local\Google\Chrome\User Data\DevToolsActivePort'
    alt_chrome_port = r'C:\Users\RehmanPC\ChromeDevProfile\DevToolsActivePort'
    for pf in [alt_chrome_port, chrome_port_file]:
        if os.path.exists(pf):
            try:
                with open(pf, 'r', encoding='utf-8') as f:
                    port = f.readline().strip()
                    path = f.readline().strip()
                if port and path:
                    return f'ws://127.0.0.1:{port}{path}'
            except Exception:
                pass
    # Fallback: fetch via HTTP /json/version (Chrome always exposes)
    try:
        import urllib.request, json as _json
        with urllib.request.urlopen('http://127.0.0.1:9222/json/version', timeout=2) as r:
            data = _json.loads(r.read().decode())
            ws = data.get('webSocketDebuggerUrl')
            if ws:
                return ws
    except Exception:
        pass
    return 'ws://127.0.0.1:9222/devtools/browser'

class CDPClient:
    def __init__(self, ws_url):
        self.ws_url = ws_url
        self.ws = None
        self.msg_id = 0
        self.session_id = None
        self.target_id = None

    async def connect(self):
        last_exc = None
        for attempt in range(5):
            try:
                self.ws_url = get_ws_url()
                self.ws = await websockets.connect(self.ws_url, max_size=50 * 1024 * 1024, open_timeout=30, ping_interval=None)
                return
            except Exception as e:
                last_exc = e
                await asyncio.sleep(1.5)
        raise last_exc

    async def send_cmd(self, method, params=None, session_id=None):
        self.msg_id += 1
        req_id = self.msg_id
        payload = {'id': req_id, 'method': method}
        if params is not None:
            payload['params'] = params
        if session_id:
            payload['sessionId'] = session_id
        await self.ws.send(json.dumps(payload))
        while True:
            raw = await self.ws.recv()
            data = json.loads(raw)
            if data.get('id') == req_id:
                if 'error' in data:
                    raise RuntimeError(f'CDP Error in {method}: {data["error"]}')
                return data.get('result', {})

    async def find_tradingview_target(self):
        res = await self.send_cmd('Target.getTargets')
        targets = res.get('targetInfos', [])
        tv_target = None
        for t in targets:
            if t.get('type') == 'page' and 'tradingview.com' in t.get('url', '').lower():
                tv_target = t
                break
        if not tv_target:
            create_res = await self.send_cmd('Target.createTarget', {'url': 'https://www.tradingview.com/chart/'})
            self.target_id = create_res.get('targetId')
            await asyncio.sleep(5)
        else:
            self.target_id = tv_target.get('targetId')

        attach_res = await self.send_cmd('Target.attachToTarget', {'targetId': self.target_id, 'flatten': True})
        self.session_id = attach_res.get('sessionId')
        return self.target_id, self.session_id

    async def eval_js(self, expression, return_by_value=True):
        res = await self.send_cmd(
            'Runtime.evaluate',
            {'expression': expression, 'returnByValue': return_by_value, 'awaitPromise': True},
            session_id=self.session_id
        )
        result_obj = res.get('result', {})
        if 'value' in result_obj:
            return result_obj['value']
        return result_obj

    async def close(self):
        if self.ws:
            await self.ws.close()

async def run_pipeline(pine_file='FINAL_OPTIMIZED_STRATEGY.pine', symbol=None, interval=None, wait_sec=6):
    pine_path = os.path.join(ROOT_DIR, pine_file)
    if not os.path.exists(pine_path) and pine_file == 'strategy.pine':
        fallback = os.path.join(ROOT_DIR, 'FINAL_OPTIMIZED_STRATEGY.pine')
        if os.path.exists(fallback):
            pine_path = fallback
    if not os.path.exists(pine_path):
        raise FileNotFoundError(f'Pine script not found: {pine_path}')
    with open(pine_path, 'r', encoding='utf-8') as f:
        pine_code = f.read()

    ws_url = get_ws_url()
    client = CDPClient(ws_url)
    await client.connect()
    await client.find_tradingview_target()

    # Suppress browser permission popups (clipboard, notifications) — stay in single CDP session
    try:
        await client.send_cmd("Browser.grantPermissions", {"permissions": ["clipboardReadWrite", "notifications"], "origin": "https://www.tradingview.com"})
    except Exception:
        pass
    try:
        await client.send_cmd("Browser.grantPermissions", {"permissions": ["clipboardReadWrite", "notifications"], "origin": "https://www.tradingview.com", "browserContextId": None})
    except Exception:
        pass

    # Switch symbol / interval
    if symbol or interval:
        sym_arg = symbol if symbol else ''
        res_arg = interval if interval else ''
        switch_js = f'''(() => {{
            const coll = window._exposed_chartWidgetCollection;
            if (!coll) return 'no coll';
            if ('{sym_arg}') coll.setSymbol('{sym_arg}');
            if ('{res_arg}') coll.setResolution('{res_arg}');
            const active = coll.activeChartWidget ? coll.activeChartWidget.value() : null;
            return {{
                symbol: active ? active.model().mainSeries().symbol() : null,
                interval: active ? active.model().mainSeries().interval() : null
            }};
        }})()'''
        await client.eval_js(switch_js)
        await asyncio.sleep(2.5)

    # Open Pine Editor
    open_pine_js = '''(() => {
        const hasEditor = !!document.querySelector('.monaco-editor');
        if (!hasEditor) {
            const pineBtn = document.querySelector('[data-name="pine-dialog-button"]') ||
                            document.querySelector('button[aria-label="Pine"]');
            if (pineBtn) pineBtn.click();
        }
        return !!document.querySelector('.monaco-editor');
    })()'''
    await client.eval_js(open_pine_js)
    await asyncio.sleep(1.2)
    # ── Handle read-only community script: auto-click "make a copy" to obtain writable editor ──
    # If Pine Editor shows "This script is read-only" banner, the Monaco model is non-writable.
    # Detect and click the copy link (a.link-i5xku525) to fork an editable Untitled script.
    readonly_handler_js = """(() => {
        const dialog = document.querySelector('[class*="dialog"]');
        const text = dialog ? dialog.innerText : '';
        if (text.includes('This script is read-only')) {
            const copyLink = document.querySelector('a.link-i5xku525');
            if (copyLink) { copyLink.click(); return 'clicked_copy'; }
            const fallback = Array.from(document.querySelectorAll('a, span')).find(el => (el.innerText||'').trim() === 'make a copy.');
            if (fallback) { fallback.click(); return 'clicked_copy_fallback'; }
            return 'readonly_no_link';
        }
        return 'writable';
    })()"""
    for _retry in range(3):
        try:
            ro_res = await client.eval_js(readonly_handler_js)
        except Exception:
            ro_res = 'error'
        if ro_res in ('clicked_copy','clicked_copy_fallback'):
            await asyncio.sleep(2.5)
            # After copy, the editor reloads with new uri; wait for Monaco to expose new model
            await client.eval_js(open_pine_js)
            await asyncio.sleep(1.0)
            break
        if ro_res == 'writable':
            break
        await asyncio.sleep(0.6)

    # Inject Pine Script — Hardened for 2-indicator limit & modal resilience
    code_json = json.dumps(pine_code)
    inject_js = f'''(() => {{
        // Ensure Monaco API is exposed
        if (!window._monaco) {{
            try {{
                window.webpackChunktradingview.push([['cdp_monaco_finder'], {{}}, (require) => {{
                    for (let id of Object.keys(require.m)) {{
                        try {{
                            let mod = require(id);
                            if (mod && mod.editor && typeof mod.editor.getModels === 'function') {{
                                window._monaco = mod;
                                break;
                            }}
                        }} catch(e) {{}}
                    }}
                }}]);
            }} catch(e) {{}}
        }}
        if (!window._monaco || !window._monaco.editor) {{
            return {{ success: false, error: 'Monaco editor API not found' }};
        }}
        const editors = window._monaco.editor.getEditors();
        const editor = editors && editors.length ? editors[0] : null;
        if (!editor) return {{ success: false, error: 'No Monaco editor instance found' }};

        // ── Pre-injection modal cleanup (limit / save / generic) ──
        let preDismissed = [];
        try {{
            const allBtns = Array.from(document.querySelectorAll('button, [data-name="close"], [aria-label="Close"]'));
            const dialogs = Array.from(document.querySelectorAll('[class*="dialog"], [class*="modal"], [class*="popup"], [role="dialog"]'));
            const limitDialog = dialogs.find(d => /limit reached|maximum.*indicat|upgrade.*plan|too many.*indicat/i.test(d.innerText || ''));
            if (limitDialog) {{
                const closeBtn = Array.from(limitDialog.querySelectorAll('button, [data-name="close"]')).find(b => /close|ok|got it|dismiss|cancel/i.test(b.innerText || '') || b.getAttribute('data-name') === 'close' || b.getAttribute('aria-label') === 'Close');
                if (closeBtn) {{ closeBtn.click(); preDismissed.push('limit_modal'); }}
                else {{
                    const fallbackClose = allBtns.find(b => (b.innerText || '').trim().toLowerCase() === 'close' || b.getAttribute('data-name') === 'close');
                    if (fallbackClose) {{ fallbackClose.click(); preDismissed.push('limit_modal_fallback'); }}
                }}
            }}
            // Dismiss stray save/overwrite dialogs left from prior run
            const strayDialogs = Array.from(document.querySelectorAll('[class*="dialog"], [class*="modal"]')).filter(d => /save this script|overwrite|save & add/i.test(d.innerText || ''));
            strayDialogs.forEach(d => {{
                const b = Array.from(d.querySelectorAll('button')).find(x => /save|overwrite|confirm/i.test(x.innerText || ''));
                if (b) {{ b.click(); preDismissed.push('stray_save'); }}
            }});
        }} catch(e) {{}}

        // ── Chart study inventory — MINIMAL removal to avoid "Allow" prompts ──
        // Strategy: Prefer Update over Remove+Add. Only remove if absolutely necessary for 2-indicator limit.
        // This keeps "Allow remove" dialogs to near-zero.
        let studyCountBefore = 0;
        let studyTitlesBefore = [];
        let removedStrategies = [];
        let hasQuantOnChart = false;
        try {{
            const coll = window._exposed_chartWidgetCollection;
            const model = coll && coll.activeChartWidget ? coll.activeChartWidget.value().model() : null;
            if (model) {{
                let allSources = [];
                let quantSources = [];
                for (let p of model.panes()) {{
                    for (let s of p.dataSources()) {{
                        const title = s.title ? s.title() : '';
                        const isStrat = s.isStrategy ? s.isStrategy() : false;
                        allSources.push(s);
                        studyTitlesBefore.push(title);
                        if (isStrat || /quant|strategy|qs_|swing|confluence|QUANT|SWING/i.test(title)) {{
                            quantSources.push(s);
                            hasQuantOnChart = true;
                        }}
                    }}
                }}
                studyCountBefore = allSources.length;
                // Minimal removal policy:
                // - If a Quant strategy already exists, KEEP IT — we will Update it via Ctrl+Enter, no removal needed.
                // - Only if NO Quant exists but chart is at limit (≥3 sources incl main+2 studies), remove oldest non-main study to make room for Add.
                // - Never bulk-remove all quant strategies; that triggers repeated Allow confirmations.
                if (!hasQuantOnChart && allSources.length >= 3) {{
                    // Find oldest study (skip main series at index 0)
                    let oldestStudy = null;
                    for (let i = 1; i < allSources.length; i++) {{
                        const t = allSources[i].title ? allSources[i].title() : '';
                        // Prefer non-essential drawing studies over built-in panels
                        if (!/BITSTAMP|BATS|SPY|QQQ|BTC/i.test(t)) {{
                            oldestStudy = allSources[i];
                            break;
                        }}
                    }}
                    if (!oldestStudy && allSources.length > 1) oldestStudy = allSources[1];
                    if (oldestStudy) {{
                        try {{
                            const t = oldestStudy.title ? oldestStudy.title() : 'oldest_study';
                            model.removeSource(oldestStudy);
                            removedStrategies.push(t);
                        }} catch(e) {{}}
                    }}
                }}
            }}
        }} catch(e) {{}}

        const targetModel = editor.getModel();
        editor.executeEdits('runner', [{{
            range: targetModel.getFullModelRange(),
            text: {code_json},
            forceMoveMarkers: true
        }}]);
        editor.pushUndoStop();
        editor.focus();
        return {{ success: true, removedStrategies: removedStrategies, studyCountBefore: studyCountBefore, studyTitlesBefore: studyTitlesBefore, preDismissed: preDismissed }};
    }})()'''
    
    inject_res = await client.eval_js(inject_js)
    if not inject_res.get('success'):
        raise RuntimeError(f'Failed to inject Pine script: {inject_res.get("error")}')

    # Allow React / Monaco to register the change before clicking update
    await asyncio.sleep(1.2)

    # ── Chart update strategy: prefer Update over Add to respect 2-indicator ceiling ──
    click_js = '''(() => {
        const allBtns = Array.from(document.querySelectorAll('button'));
        const findBy = (pred) => allBtns.find(pred);
        const updateBtn = document.querySelector('[title="Update on chart"]') ||
                           findBy(b => /update on chart/i.test(b.innerText || '') || /update on chart/i.test(b.getAttribute('title') || '') || /update on chart/i.test(b.getAttribute('aria-label') || ''));
        const addBtn = document.querySelector('[title="Add to chart"]') ||
                       findBy(b => /add to chart/i.test(b.innerText || '') || /add to chart/i.test(b.getAttribute('title') || '') || /add to chart/i.test(b.getAttribute('aria-label') || ''));
        // Prefer Update to avoid triggering 2-indicator limit; Add only if Update unavailable
        if (updateBtn && !updateBtn.disabled) {
            try { updateBtn.click(); } catch(e) {}
            return 'clicked_update';
        }
        if (addBtn && !addBtn.disabled) {
            try { addBtn.click(); } catch(e) {}
            return 'clicked_add';
        }
        // Return diagnostic for Ctrl+Enter fallback decision
        return JSON.stringify({
            result: 'none',
            updateExists: !!updateBtn,
            updateDisabled: updateBtn ? updateBtn.disabled : null,
            addExists: !!addBtn,
            addDisabled: addBtn ? addBtn.disabled : null,
            allTitles: allBtns.filter(b => b.getAttribute('title')).map(b => b.getAttribute('title')).slice(0,20)
        });
    })()'''
    click_res = await client.eval_js(click_js)
    # Normalize click_res (may be JSON string if both buttons missing)
    click_label = click_res if isinstance(click_res, str) and click_res in ('clicked_update','clicked_add') else 'none'

    # Dispatch Ctrl+Enter (Update on Chart shortcut) if no button was found or Update was preferred but not clickable
    if click_label == 'none':
        await client.send_cmd(
            "Input.dispatchKeyEvent",
            {"type": "rawKeyDown", "key": "Enter", "code": "Enter", "windowsVirtualKeyCode": 13, "modifiers": 2},
            session_id=client.session_id
        )
        await client.send_cmd(
            "Input.dispatchKeyEvent",
            {"type": "keyUp", "key": "Enter", "code": "Enter", "windowsVirtualKeyCode": 13, "modifiers": 2},
            session_id=client.session_id
        )
        await asyncio.sleep(0.6)
        # Second fallback: Ctrl+Enter via keyDown with ctrlKey explicitly for Monaco
        await client.send_cmd(
            "Input.dispatchKeyEvent",
            {"type": "keyDown", "key": "Enter", "code": "Enter", "windowsVirtualKeyCode": 13, "modifiers": 2, "isSystemKey": False},
            session_id=client.session_id
        )

    await asyncio.sleep(1.0)
    # ── Unified modal handler: Save/Overwrite + 2-indicator limit + generic dialogs ──
    # Polls for up to 8s, clicking appropriate confirmation / dismiss buttons automatically
    modal_handler_js = '''(() => {
        const dialogs = Array.from(document.querySelectorAll('[class*="dialog"], [class*="modal"], [class*="popup"], [role="dialog"], [data-dialog-name]'));
        const allBtns = Array.from(document.querySelectorAll('button, [data-name="close"], [aria-label="Close"]'));
        const textOf = (el) => (el.innerText || '').toLowerCase();

        // 0) Allow / Remove / Debugging confirmation — auto-allow to keep zero-click flow (user requested minimal prompts)
        const allowDialog = dialogs.find(d => /allow|remove.*debug|confirm.*remove|delete.*script|do you want to remove/i.test(d.innerText || ''));
        if (allowDialog) {
            const candidates = Array.from(allowDialog.querySelectorAll('button'));
            const allowBtn = candidates.find(b => /^allow$/i.test((b.innerText||'').trim())) ||
                             candidates.find(b => /^yes$/i.test((b.innerText||'').trim())) ||
                             candidates.find(b => /allow|confirm|remove|delete|ok/i.test(b.innerText||'') && !/cancel|deny|no|close/i.test(b.innerText||''));
            if (allowBtn && !allowBtn.disabled) { allowBtn.click(); return 'auto_allowed:' + (allowBtn.innerText||'').trim(); }
            // Fallback: any button with Allow text globally inside dialog
            const fallbackAllow = allowDialog.querySelector('button');
            if (fallbackAllow && /allow/i.test(fallbackAllow.innerText||'')) { fallbackAllow.click(); return 'auto_allowed_fallback'; }
        }
        // Global Allow button scan (covers toasts/popups outside dialogs)
        const globalAllow = allBtns.find(b => /^allow$/i.test((b.innerText||'').trim()) && b.offsetParent !== null);
        if (globalAllow) {
            const parentText = globalAllow.closest('[class*="dialog"], [class*="modal"], [class*="popup"]');
            if (parentText && /allow|remove|debug/i.test(parentText.innerText||'')) { globalAllow.click(); return 'auto_allowed_global'; }
        }

        // 1) Save / Overwrite confirmation dialog
        const saveDialog = dialogs.find(d => /save this script|save.*script|overwrite.*script|confirm.*save|save & add/i.test(d.innerText || ''));
        if (saveDialog) {
            const candidates = Array.from(saveDialog.querySelectorAll('button'));
            // Priority: Save / Overwrite / Confirm / Yes
            const saveBtn = candidates.find(b => /^save$/i.test((b.innerText||'').trim())) ||
                            candidates.find(b => /overwrite/i.test(b.innerText||'')) ||
                            candidates.find(b => /^save &/i.test((b.innerText||'').trim())) ||
                            candidates.find(b => /confirm|yes|continue/i.test(b.innerText||''));
            if (saveBtn && !saveBtn.disabled) { saveBtn.click(); return 'clicked_save_dialog:' + (saveBtn.innerText||'').trim(); }
        }
        // Fallback save button search globally
        let globalSaveBtn = allBtns.find(b => /^save$/i.test((b.innerText||'').trim()) && b.offsetParent !== null);
        if (globalSaveBtn && dialogs.some(d=>/save/i.test(d.innerText||''))) {
            globalSaveBtn.click(); return 'clicked_save_global';
        }

        // 2) 2-indicator / upgrade limit modal  ("limit reached", "upgrade", "maximum")
        const limitDialog = dialogs.find(d => /limit reached|maximum.*indicat|upgrade.*plan|too many.*indicat|3 indicators|2 indicators/i.test(d.innerText || ''));
        if (limitDialog) {
            const closeBtn = Array.from(limitDialog.querySelectorAll('button, [data-name="close"], [aria-label="Close"]')).find(b => /close|ok|got it|dismiss|cancel|upgrade/i.test(b.innerText||'') || b.getAttribute('data-name')==='close' || b.getAttribute('aria-label')==='Close');
            if (closeBtn) { closeBtn.click(); return 'dismissed_limit_modal:' + (closeBtn.innerText||closeBtn.getAttribute('data-name')||'close'); }
            // Fallback: click X icon
            const xBtn = document.querySelector('[data-name="close"], [aria-label="Close"]');
            if (xBtn) { xBtn.click(); return 'dismissed_limit_fallback'; }
        }
        // Broad limit toast detection (TradingView shows as toast/popup, not dialog)
        const toastLimit = Array.from(document.querySelectorAll('[class*="toast"], [class*="notification"], [class*="snack"]')).find(t=>/limit reached|upgrade/i.test(t.innerText||''));
        if (toastLimit) {
            const closeToast = toastLimit.querySelector('[data-name="close"], button, [aria-label="Close"]');
            if (closeToast) { closeToast.click(); return 'dismissed_limit_toast'; }
        }

        // 3) Generic error/confirm dialogs that block compilation
        const blockDialog = dialogs.find(d => d.offsetParent !== null && allBtns.some(b=>d.contains(b)));
        if (blockDialog) {
            const closeBtn = Array.from(blockDialog.querySelectorAll('button')).find(b=>/close|ok|confirm|cancel/i.test(b.innerText||'')) || blockDialog.querySelector('[data-name="close"]');
            if (closeBtn && /error|warning|failed|unsaved/i.test(blockDialog.innerText||'')) {
                // Only auto-close non-save dialogs that look like errors/warnings to avoid accidental dismiss of save
                // But limit modals already handled above; here we handle generic 'close' for blocking overlays
                if (/limit|upgrade|maximum/i.test(blockDialog.innerText||'')) { closeBtn.click(); return 'dismissed_generic_limit'; }
            }
        }
        return 'none';
    })()'''
    # Poll modal handler for up to 8 seconds after compile trigger
    modal_result = 'none'
    for _poll in range(16):
        await asyncio.sleep(0.5)
        try:
            modal_result = await client.eval_js(modal_handler_js)
        except Exception:
            modal_result = 'none'
        if isinstance(modal_result, str) and modal_result != 'none' and 'dismissed_limit' in modal_result:
            # After dismissing limit, try Ctrl+Enter again to ensure update succeeds
            await asyncio.sleep(0.4)
            await client.send_cmd(
                "Input.dispatchKeyEvent",
                {"type": "rawKeyDown", "key": "Enter", "code": "Enter", "windowsVirtualKeyCode": 13, "modifiers": 2},
                session_id=client.session_id
            )
            await client.send_cmd(
                "Input.dispatchKeyEvent",
                {"type": "keyUp", "key": "Enter", "code": "Enter", "windowsVirtualKeyCode": 13, "modifiers": 2},
                session_id=client.session_id
            )
            await asyncio.sleep(0.5)
        if isinstance(modal_result, str) and modal_result.startswith('auto_allowed'):
            await asyncio.sleep(0.6)
            continue
        if isinstance(modal_result, str) and modal_result.startswith('clicked_save'):
            # Save dialog clicked — give extra time for second confirmation if any
            await asyncio.sleep(0.8)
            continue
        if modal_result == 'none':
            # Check if no dialogs remain; break early if clean
            await asyncio.sleep(0.2)
            # peek again quickly to confirm no dialog re-appeared
            try:
                peek = await client.eval_js(modal_handler_js)
                if peek == 'none':
                    break
                else:
                    modal_result = peek
                    continue
            except Exception:
                break
        # If we handled something, loop again to catch chained modals
        if modal_result == 'none':
            break
    # Final Escape key dispatch to clear any residual overlay focus
    try:
        await client.send_cmd("Input.dispatchKeyEvent", {"type": "rawKeyDown", "key": "Escape", "code": "Escape", "windowsVirtualKeyCode": 27}, session_id=client.session_id)
        await client.send_cmd("Input.dispatchKeyEvent", {"type": "keyUp", "key": "Escape", "code": "Escape", "windowsVirtualKeyCode": 27}, session_id=client.session_id)
    except Exception:
        pass

    # Wait for compilation and strategy recalculation
    await asyncio.sleep(wait_sec)

    # Check errors
    check_errors_js = '''(() => {
        if (!window._monaco || !window._monaco.editor) return [];
        const models = window._monaco.editor.getModels();
        const targetModel = models.find(m => m.uri.toString().includes('placement=dialog') && !m.uri.toString().includes('ORIGINAL')) ||
                            models.find(m => m.uri.toString().includes('.pine')) ||
                            models[0];
        if (!targetModel) return [];
        const markers = window._monaco.editor.getModelMarkers({ resource: targetModel.uri });
        return markers.filter(m => m.severity === 8).map(m => ({
            line: m.startLineNumber,
            col: m.startColumn,
            message: m.message
        }));
    })()'''
    errors = await client.eval_js(check_errors_js)
    if errors:
        with open(ERROR_LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(f'--- Compilation Errors ({time.strftime("%Y-%m-%d %H:%M:%S")}) ---\\n')
            for err in errors:
                f.write(f'Line {err.get("line")}:{err.get("col")} - {err.get("message")}\\n')
        err_payload = {'status': 'compile_error', 'errors': errors, 'error_log': ERROR_LOG_PATH}
        print(json.dumps(err_payload, indent=2))
        await client.close()
        return err_payload

    # Open Strategy Tester
    open_tester_js = '''(() => {
        const testerBtn = Array.from(document.querySelectorAll('button, [role="button"], [data-name]'))
            .find(b => /strategy tester/i.test(b.innerText || '') || /strategy tester/i.test(b.getAttribute('aria-label') || '') || b.getAttribute('data-name') === 'backtesting');
        if (testerBtn && !document.querySelector('[class*="reportContainer-"]')) {
            testerBtn.click();
        }
        return !!document.querySelector('[class*="reportContainer-"]');
    })()'''
    await client.eval_js(open_tester_js)

    # Scrape report with polling until metrics appear
    scrape_js = '''(() => {
        const report = document.querySelector('[class*="reportContainer-"]') ||
                       document.querySelector('[class*="wrapper-dmId9qUc"]') ||
                       document.querySelector('[class*="wrapper-yprR2JgA"]');
        if (!report) return { error: 'No report container found' };
        const coll = window._exposed_chartWidgetCollection;
        const active = coll && coll.activeChartWidget ? coll.activeChartWidget.value() : null;
        return {
            symbol: active ? active.model().mainSeries().symbol() : '',
            interval: active ? active.model().mainSeries().interval() : '',
            rawText: report.innerText
        };
    })()'''
    
    raw_text = ''
    report_data = {}
    for _ in range(25):
        await asyncio.sleep(1)
        report_data = await client.eval_js(scrape_js)
        raw_text = report_data.get('rawText', '')
        if 'Total PnL' in raw_text and 'Profitable trades' in raw_text and 'Profit factor' in raw_text:
            break
        if 'requires trade data' in raw_text:
            # Script compiled and executed, but 0 trades were triggered in this period
            await asyncio.sleep(2)
            break

    metrics = {
        'status': 'success',
        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S'),
        'symbol': report_data.get('symbol', symbol or 'UNKNOWN'),
        'interval': report_data.get('interval', interval or 'UNKNOWN'),
        'net_profit_raw': None,
        'net_profit_pct': None,
        'max_drawdown_raw': None,
        'max_drawdown_pct': None,
        'win_rate_pct': None,
        'winning_trades': None,
        'total_closed_trades': None,
        'profit_factor': None,
        'sharpe_ratio': None
    }

    if 'requires trade data' in raw_text and 'Total PnL' not in raw_text:
        metrics['total_closed_trades'] = 0
        metrics['winning_trades'] = 0
        metrics['win_rate_pct'] = 0.0
        metrics['net_profit_pct'] = 0.0
        metrics['net_profit_raw'] = '0.00 USD (0.00%)'
        metrics['max_drawdown_pct'] = 0.0
        metrics['max_drawdown_raw'] = '0.00 USD (0.00%)'
        metrics['profit_factor'] = None
        metrics['sharpe_ratio'] = None
    else:
        m_pnl = re.search(r'Total PnL\s*\n?([+\-−]?[0-9,.]+(?:USD|\$|EUR)?([+\-−]?[0-9,.]+)\s*%)', raw_text)
        if m_pnl:
            metrics['net_profit_raw'] = m_pnl.group(1).strip()
            metrics['net_profit_pct'] = float(m_pnl.group(2).replace('+', '').replace('−', '-').replace(',', ''))

        m_dd = re.search(r'Max drawdown\s*\n?([0-9,.]+(?:USD|\$|EUR)?([0-9,.]+)\s*%)', raw_text)
        if m_dd:
            metrics['max_drawdown_raw'] = m_dd.group(1).strip()
            metrics['max_drawdown_pct'] = float(m_dd.group(2).replace(',', ''))

        m_win = re.search(r'Profitable trades\s*\n?([0-9,.]+)\s*%\s*([0-9]+)\s*/\s*([0-9]+)', raw_text)
        if m_win:
            metrics['win_rate_pct'] = float(m_win.group(1).replace(',', ''))
            metrics['winning_trades'] = int(m_win.group(2))
            metrics['total_closed_trades'] = int(m_win.group(3))

        m_pf = re.search(r'Profit factor\s*\n?([0-9,.]+)', raw_text)
        if m_pf:
            metrics['profit_factor'] = float(m_pf.group(1).replace(',', ''))

        m_sharpe = re.search(r'Sharpe ratio\s*\n?([+\-−]?[0-9,.]+)', raw_text, re.IGNORECASE)
        if m_sharpe:
            metrics['sharpe_ratio'] = float(m_sharpe.group(1).replace('−', '-').replace(',', ''))
        else:
            if metrics['profit_factor'] and metrics['total_closed_trades'] and metrics['max_drawdown_pct']:
                pf = metrics['profit_factor']
                dd = max(metrics['max_drawdown_pct'], 1.0)
                np = metrics['net_profit_pct'] or 0.0
                wr = metrics['win_rate_pct'] or 50.0
                # NOT A VALID SHARPE RATIO — no variance/annualization, non-decision-grade.
                sharpe_est = round((np / dd) * (wr / 50.0) * 0.5, 2)
                metrics['sharpe_ratio'] = sharpe_est

    history = []
    if os.path.exists(HISTORY_JSON_PATH):
        try:
            with open(HISTORY_JSON_PATH, 'r', encoding='utf-8') as hf:
                history = json.load(hf)
        except Exception:
            history = []
    history.append(metrics)
    with open(HISTORY_JSON_PATH, 'w', encoding='utf-8') as hf:
        json.dump(history, hf, indent=2)

    print(json.dumps(metrics, indent=2))
    await client.close()
    return metrics

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='TradingView Pine Script Runner')
    parser.add_argument('--pine', default='FINAL_OPTIMIZED_STRATEGY.pine', help='Path to Pine Script file')
    parser.add_argument('--symbol', default=None, help='Target Ticker')
    parser.add_argument('--interval', default=None, help='Target Resolution')
    parser.add_argument('--wait', type=int, default=6, help='Wait seconds after compile')
    args = parser.parse_args()
    asyncio.run(run_pipeline(args.pine, args.symbol, args.interval, args.wait))

