"""
Dual-Script Chart Injection — Autonomous Closed Loop
Slot 1: FINAL_OPTIMIZED_STRATEGY.pine  (FINAL_BASELINE)
Slot 2: CONFLUENCE_STUDY_OVERLAY.pine (CONFLUENCE_STUDY)
Respects TradingView Free 2-indicator limit.
"""
import asyncio, json, os, sys, re, time, pathlib
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import runner
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FINAL_PINE = os.path.join(ROOT, "FINAL_OPTIMIZED_STRATEGY.pine")
OVERLAY_PINE = os.path.join(ROOT, "CONFLUENCE_STUDY_OVERLAY.pine")

async def inject_pine(client, pine_code, expect_title, is_first=False):
    code_json = json.dumps(pine_code)
    # Pre-injection: ensure Monaco exposed and handle readonly
    inject_js = f'''(async () => {{
        // Ensure Monaco API exposed
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
        const targetModel = editor.getModel();
        if (!targetModel) return {{ success: false, error: 'No model' }};
        editor.executeEdits('dual_inject', [{{
            range: targetModel.getFullModelRange(),
            text: {code_json},
            forceMoveMarkers: true
        }}]);
        editor.pushUndoStop();
        editor.focus();
        return {{ success: true }};
    }})()'''
    res = await client.eval_js(inject_js)
    if not res.get('success'):
        raise RuntimeError(f"Inject failed for {expect_title}: {res}")
    await asyncio.sleep(1.2)
    # Click Add to Chart (force Add for dual injection, never Update)
    click_js = """(() => {
        const allBtns = Array.from(document.querySelectorAll('button'));
        const findBy = (pred) => allBtns.find(pred);
        const updateBtn = document.querySelector('[title="Update on chart"]');
        const addBtn = document.querySelector('[title="Add to chart"]');
        // For dual injection, force Add if available, else Update
        if (addBtn && !addBtn.disabled) {
            try { addBtn.click(); } catch(e) {}
            return 'clicked_add';
        }
        if (updateBtn && !updateBtn.disabled) {
            try { updateBtn.click(); } catch(e) {}
            return 'clicked_update';
        }
        return JSON.stringify({
            result: 'none',
            updateExists: !!updateBtn,
            updateDisabled: updateBtn ? updateBtn.disabled : null,
            addExists: !!addBtn,
            addDisabled: addBtn ? addBtn.disabled : null,
            titles: Array.from(document.querySelectorAll('button')).filter(b=>b.getAttribute('title')).map(b=>b.getAttribute('title')).slice(0,10)
        });
    })()"""
    click_res = await client.eval_js(click_js)
    label = click_res if isinstance(click_res, str) and click_res in ('clicked_add','clicked_update') else 'none'
    if label == 'none':
        # Ctrl+Enter fallback
        await client.send_cmd("Input.dispatchKeyEvent", {"type":"rawKeyDown","key":"Enter","code":"Enter","windowsVirtualKeyCode":13,"modifiers":2}, session_id=client.session_id)
        await client.send_cmd("Input.dispatchKeyEvent", {"type":"keyUp","key":"Enter","code":"Enter","windowsVirtualKeyCode":13,"modifiers":2}, session_id=client.session_id)
        await asyncio.sleep(0.6)
        await client.send_cmd("Input.dispatchKeyEvent", {"type":"keyDown","key":"Enter","code":"Enter","windowsVirtualKeyCode":13,"modifiers":2}, session_id=client.session_id)
        label = 'ctrl_enter'
    await asyncio.sleep(1.0)
    # Unified modal handler polling (Allow, Save, Limit)
    modal_handler_js = """(() => {
        const dialogs = Array.from(document.querySelectorAll('[class*="dialog"], [class*="modal"], [class*="popup"], [role="dialog"], [data-dialog-name]'));
        const allBtns = Array.from(document.querySelectorAll('button, [data-name="close"], [aria-label="Close"]'));
        const allowDialog = dialogs.find(d => /allow|remove.*debug|confirm.*remove|delete.*script|do you want to remove/i.test(d.innerText || ''));
        if (allowDialog) {
            const candidates = Array.from(allowDialog.querySelectorAll('button'));
            const allowBtn = candidates.find(b => /^allow$/i.test((b.innerText||'').trim())) || candidates.find(b => /^yes$/i.test((b.innerText||'').trim())) || candidates.find(b => /allow|confirm|remove|delete|ok/i.test(b.innerText||'') && !/cancel|deny|no|close/i.test(b.innerText||''));
            if (allowBtn && !allowBtn.disabled) { allowBtn.click(); return 'auto_allowed:' + (allowBtn.innerText||'').trim(); }
            const fallbackAllow = allowDialog.querySelector('button');
            if (fallbackAllow && /allow/i.test(fallbackAllow.innerText||'')) { fallbackAllow.click(); return 'auto_allowed_fallback'; }
        }
        const globalAllow = allBtns.find(b => /^allow$/i.test((b.innerText||'').trim()) && b.offsetParent !== null);
        if (globalAllow) {
            const parentText = globalAllow.closest('[class*="dialog"], [class*="modal"], [class*="popup"]');
            if (parentText && /allow|remove|debug/i.test(parentText.innerText||'')) { globalAllow.click(); return 'auto_allowed_global'; }
        }
        const saveDialog = dialogs.find(d => /save this script|save.*script|overwrite.*script|confirm.*save|save & add/i.test(d.innerText || ''));
        if (saveDialog) {
            const candidates = Array.from(saveDialog.querySelectorAll('button'));
            const saveBtn = candidates.find(b => /^save$/i.test((b.innerText||'').trim())) || candidates.find(b => /overwrite/i.test(b.innerText||'')) || candidates.find(b => /^save &/i.test((b.innerText||'').trim())) || candidates.find(b => /confirm|yes|continue/i.test(b.innerText||''));
            if (saveBtn && !saveBtn.disabled) { saveBtn.click(); return 'clicked_save_dialog:' + (saveBtn.innerText||'').trim(); }
        }
        let globalSaveBtn = allBtns.find(b => /^save$/i.test((b.innerText||'').trim()) && b.offsetParent !== null);
        if (globalSaveBtn && dialogs.some(d=>/save/i.test(d.innerText||''))) { globalSaveBtn.click(); return 'clicked_save_global'; }
        const limitDialog = dialogs.find(d => /limit reached|maximum.*indicat|upgrade.*plan|too many.*indicat|3 indicators|2 indicators/i.test(d.innerText || ''));
        if (limitDialog) {
            const closeBtn = Array.from(limitDialog.querySelectorAll('button, [data-name="close"], [aria-label="Close"]')).find(b => /close|ok|got it|dismiss|cancel|upgrade/i.test(b.innerText||'') || b.getAttribute('data-name')==='close' || b.getAttribute('aria-label')==='Close');
            if (closeBtn) { closeBtn.click(); return 'dismissed_limit_modal:' + (closeBtn.innerText||closeBtn.getAttribute('data-name')||'close'); }
            const xBtn = document.querySelector('[data-name="close"], [aria-label="Close"]');
            if (xBtn) { xBtn.click(); return 'dismissed_limit_fallback'; }
        }
        const toastLimit = Array.from(document.querySelectorAll('[class*="toast"], [class*="notification"], [class*="snack"]')).find(t=>/limit reached|upgrade/i.test(t.innerText||''));
        if (toastLimit) {
            const closeToast = toastLimit.querySelector('[data-name="close"], button, [aria-label="Close"]');
            if (closeToast) { closeToast.click(); return 'dismissed_limit_toast'; }
        }
        return 'none';
    })()"""
    for _poll in range(16):
        await asyncio.sleep(0.5)
        try:
            modal_result = await client.eval_js(modal_handler_js)
        except Exception:
            modal_result = 'none'
        if isinstance(modal_result, str) and modal_result != 'none' and 'dismissed_limit' in modal_result:
            await asyncio.sleep(0.4)
            await client.send_cmd("Input.dispatchKeyEvent", {"type":"rawKeyDown","key":"Enter","code":"Enter","windowsVirtualKeyCode":13,"modifiers":2}, session_id=client.session_id)
            await client.send_cmd("Input.dispatchKeyEvent", {"type":"keyUp","key":"Enter","code":"Enter","windowsVirtualKeyCode":13,"modifiers":2}, session_id=client.session_id)
            await asyncio.sleep(0.5)
        if isinstance(modal_result, str) and modal_result.startswith('auto_allowed'):
            await asyncio.sleep(0.6)
            continue
        if isinstance(modal_result, str) and modal_result.startswith('clicked_save'):
            await asyncio.sleep(0.8)
            continue
        if modal_result == 'none':
            await asyncio.sleep(0.2)
            try:
                peek = await client.eval_js(modal_handler_js)
                if peek == 'none':
                    break
                else:
                    modal_result = peek
                    continue
            except Exception:
                break
        if modal_result == 'none':
            break
    try:
        await client.send_cmd("Input.dispatchKeyEvent", {"type":"rawKeyDown","key":"Escape","code":"Escape","windowsVirtualKeyCode":27}, session_id=client.session_id)
        await client.send_cmd("Input.dispatchKeyEvent", {"type":"keyUp","key":"Escape","code":"Escape","windowsVirtualKeyCode":27}, session_id=client.session_id)
    except Exception:
        pass
    await asyncio.sleep(4)
    # Check for compile errors
    check_errors_js = """(() => {
        if (!window._monaco || !window._monaco.editor) return [];
        const models = window._monaco.editor.getModels();
        const targetModel = models.find(m => m.uri.toString().includes('placement=dialog') && !m.uri.toString().includes('ORIGINAL')) || models.find(m => m.uri.toString().includes('.pine')) || models[0];
        if (!targetModel) return [];
        const markers = window._monaco.editor.getModelMarkers({ resource: targetModel.uri });
        return markers.filter(m => m.severity === 8).map(m => ({ line: m.startLineNumber, col: m.startColumn, message: m.message }));
    })()"""
    errors = await client.eval_js(check_errors_js)
    return {"click": label, "errors": errors}

async def open_pine_editor(client):
    open_pine_js = """(() => {
        const hasEditor = !!document.querySelector('.monaco-editor');
        if (!hasEditor) {
            const pineBtn = document.querySelector('[data-name="pine-dialog-button"]') || document.querySelector('button[aria-label="Pine"]');
            if (pineBtn) pineBtn.click();
        }
        return !!document.querySelector('.monaco-editor');
    })()"""
    await client.eval_js(open_pine_js)
    await asyncio.sleep(1.2)
    # handle read-only — updated for 2026 TradingView DOM (link-r4uFtjgt + restore)
    readonly_handler_js = """(() => {
        const dialog = document.querySelector('[class*="dialog"]') || document.querySelector('[data-name="pine-dialog"]');
        const text = dialog ? dialog.innerText : '';
        if (text.includes('This script is read-only') || text.includes('This is a historical version') || text.includes('restore this version')) {
            // New 2026 class: link-r4uFtjgt for restore
            const restoreLink = document.querySelector('a.link-r4uFtjgt') || Array.from(document.querySelectorAll('a')).find(a => /restore this version/i.test(a.innerText||''));
            if (restoreLink) { restoreLink.click(); return 'clicked_restore:' + (restoreLink.className||'').slice(0,30); }
            const copyLink = document.querySelector('a.link-i5xku525') || document.querySelector('a.link-r4uFtjgt');
            if (copyLink) { copyLink.click(); return 'clicked_copy'; }
            const fallback = Array.from(document.querySelectorAll('a, span, button')).find(el => {
                const t = (el.innerText||'').trim().toLowerCase();
                return t === 'make a copy.' || t === 'make a copy' || t.includes('make a copy') || /restore this version/i.test(t);
            });
            if (fallback) { fallback.click(); return 'clicked_copy_fallback:' + fallback.tagName + ':' + (fallback.innerText||'').slice(0,30); }
            const restoreBtn = Array.from(document.querySelectorAll('button, a')).find(b => /restore this version/i.test(b.innerText||''));
            if (restoreBtn) { restoreBtn.click(); return 'clicked_restore_btn:' + restoreBtn.tagName; }
            return 'readonly_no_link:' + text.slice(0,300);
        }
        // Also check if editor is in read-only per Monaco
        if (window._monaco && window._monaco.editor) {
            try {
                const ed = window._monaco.editor.getEditors()[0];
                if (ed && ed.getOption && ed.getOption(33) === false) { /* readOnly option */ }
            } catch(e){}
        }
        return 'writable';
    })()"""
    for _retry in range(5):
        try:
            ro_res = await client.eval_js(readonly_handler_js)
        except Exception as e:
            ro_res = f'error:{e}'
        if ro_res in ('clicked_copy','clicked_copy_fallback','clicked_copy_fallback:A','clicked_copy_fallback:SPAN'):
            await asyncio.sleep(2.8)
            await client.eval_js(open_pine_js)
            await asyncio.sleep(1.0)
            break
        if isinstance(ro_res, str) and ro_res.startswith('clicked_copy_fallback'):
            await asyncio.sleep(2.8)
            await client.eval_js(open_pine_js)
            await asyncio.sleep(1.0)
            break
        if ro_res == 'writable':
            break
        if isinstance(ro_res, str) and ro_res.startswith('clicked_restore'):
            await asyncio.sleep(2.0)
            continue
        await asyncio.sleep(0.6)
    return ro_res

async def clean_chart(client):
    # Remove all custom strategies/studies matching quant/swing/confluence/final/baseline/confluence_swing
    js = """(() => {
        let removed = [];
        let studyCountBefore = 0;
        let studyTitlesBefore = [];
        try {
            const coll = window._exposed_chartWidgetCollection;
            const model = coll && coll.activeChartWidget ? coll.activeChartWidget.value().model() : null;
            if (model) {
                let allSources = [];
                for (let p of model.panes()) {
                    for (let s of p.dataSources()) {
                        allSources.push(s);
                        try { studyTitlesBefore.push(s.title ? s.title() : ''); } catch(e){ studyTitlesBefore.push('?'); }
                    }
                }
                studyCountBefore = allSources.length;
                // Identify custom sources to remove
                let toRemove = [];
                for (let s of allSources) {
                    let title = '';
                    try { title = s.title ? s.title() : ''; } catch(e) {}
                    let isStrat = false;
                    try { isStrat = s.isStrategy ? s.isStrategy() : false; } catch(e) {}
                    // Remove if title matches custom patterns OR isStrategy true and title not base
                    if (/CONFLUENCE|SWING|FINAL|BASELINE|QUANT|strategy|STRATEGY/i.test(title) || (isStrat && !/SPY|QQQ|BTC|SPX|NDQ/i.test(title))) {
                        // Also catch duplicate long param titles
                        toRemove.push(s);
                    } else if (/\\(2\\.8, 3, 1\\.5|Unnamed|All-in-One/i.test(title)) {
                        toRemove.push(s);
                    }
                }
                // Deduplicate
                toRemove = [...new Set(toRemove)];
                for (let s of toRemove) {
                    try {
                        let t = s.title ? s.title() : 'unknown';
                        model.removeSource(s);
                        removed.push(t);
                    } catch(e) {}
                }
                // After removal, trigger Allow dialogs handling via later poller
            }
        } catch(e) { return {error: e.toString(), removed, studyCountBefore, studyTitlesBefore}; }
        return {removed, studyCountBefore, studyTitlesBefore};
    })()"""
    res = await client.eval_js(js)
    # Handle Allow dialogs that appear after removal
    modal_js = """(() => {
        const dialogs = Array.from(document.querySelectorAll('[class*="dialog"], [class*="modal"], [role="dialog"]'));
        const allowDialog = dialogs.find(d => /allow|remove.*debug|confirm.*remove|delete.*script|do you want to remove/i.test(d.innerText || ''));
        if (allowDialog) {
            const candidates = Array.from(allowDialog.querySelectorAll('button'));
            const allowBtn = candidates.find(b => /^allow$/i.test((b.innerText||'').trim())) || candidates.find(b => /^yes$/i.test((b.innerText||'').trim()));
            if (allowBtn) { allowBtn.click(); return 'auto_allowed'; }
        }
        const globalAllow = Array.from(document.querySelectorAll('button')).find(b => /^allow$/i.test((b.innerText||'').trim()) && b.offsetParent !== null);
        if (globalAllow) { globalAllow.click(); return 'auto_allowed_global'; }
        return 'none';
    })()"""
    for _ in range(8):
        await asyncio.sleep(0.6)
        try:
            m = await client.eval_js(modal_js)
            if m == 'none':
                break
        except Exception:
            break
    await asyncio.sleep(1.0)
    return res

async def verify_chart(client):
    js = """(() => {
        const coll = window._exposed_chartWidgetCollection;
        const model = coll && coll.activeChartWidget ? coll.activeChartWidget.value().model() : null;
        let sources = [];
        let isStrategyFlags = [];
        if (model) {
            for (let p of model.panes()) {
                for (let s of p.dataSources()) {
                    let t = s.title ? s.title() : '';
                    let isStrat = s.isStrategy ? s.isStrategy() : false;
                    sources.push(t);
                    isStrategyFlags.push(isStrat);
                }
            }
        }
        // Check Strategy Tester visibility
        const hasTester = !!document.querySelector('[class*="reportContainer"]') || document.body.innerText.includes('Strategy Tester');
        // Check pine editor model titles
        let pineTitles = [];
        if (window._monaco && window._monaco.editor) {
            try {
                const models = window._monaco.editor.getModels();
                pineTitles = models.map(m=>m.uri.toString().slice(0,120));
            } catch(e){}
        }
        return {sources, isStrategyFlags, hasTester, pineTitles, paneCount: model ? model.panes().length : 0};
    })()"""
    return await client.eval_js(js)

async def create_new_script(client, kind="Strategy"):
    """Create new blank script via Pine title menu -> Create new -> Indicator/Strategy"""
    print(f"    -> Creating new {kind} via title menu...")
    # Ensure title menu is closed first then open
    await client.eval_js("""(() => {
        const btn = document.querySelector('[data-qa-id="pine-script-title-button"]');
        if (btn && btn.getAttribute('aria-expanded')==='true') btn.click();
        return 'closed if open';
    })()""")
    await asyncio.sleep(0.5)
    # Open title menu
    await client.eval_js("""(() => {
        const btn = document.querySelector('[data-qa-id="pine-script-title-button"]');
        if (btn && btn.getAttribute('aria-expanded')==='false') btn.click();
        return 'opened';
    })()""")
    await asyncio.sleep(1.2)
    # Hover Create new to open submenu, then click kind
    js = f"""(() => {{
        // Find main menu
        const titleBtn = document.querySelector('[data-qa-id="pine-script-title-button"]');
        const controls = titleBtn ? titleBtn.getAttribute('aria-controls') : null;
        const menu = controls ? document.getElementById(controls) : document.querySelector('[id=":rni:"]');
        if (!menu) return 'no menu';
        const items = Array.from(menu.querySelectorAll('[role="menuitem"]'));
        const createNew = items.find(el=> /Create new/i.test(el.innerText||el.getAttribute('aria-label')||''));
        if (!createNew) return 'no Create new';
        createNew.dispatchEvent(new MouseEvent('mouseover', {{bubbles:true}}));
        // Small delay to let submenu appear
        return 'hovered Create new';
    }})()"""
    await client.eval_js(js)
    await asyncio.sleep(0.8)
    # Click the desired kind in submenu
    js2 = f"""(() => {{
        // Submenu should be visible with Indicator/Strategy
        const subMenus = Array.from(document.querySelectorAll('[role="menu"]'));
        const sub = subMenus.find(m=> /Indicator.*Strategy|Strategy.*Indicator/i.test(m.innerText||'') || (m.innerText.includes('Indicator') && m.innerText.includes('Strategy')));
        // Fallback find by id :rsq: or any menu containing Indicator
        let target = null;
        if (sub) {{
            const items = Array.from(sub.querySelectorAll('[role="menuitem"]'));
            target = items.find(el=> el.innerText.trim().startsWith('{kind}') || new RegExp('^{kind}', 'i').test(el.innerText));
        }}
        if (!target) {{
            // Global search
            const allItems = Array.from(document.querySelectorAll('[role="menuitem"]'));
            target = allItems.find(el=> el.innerText.trim().startsWith('{kind}') || el.innerText.includes('{kind}'));
        }}
        if (!target) {{
            const all = Array.from(document.querySelectorAll('[role="menuitem"]')).map(e=>e.innerText.slice(0,80)).join('|');
            return 'no {kind} item, found: ' + all;
        }}
        target.click();
        return 'clicked {kind}: ' + target.innerText.slice(0,100);
    }})()"""
    res = await client.eval_js(js2)
    print(f"        -> {res}")
    await asyncio.sleep(2.5)
    # Verify new script created
    check = await client.eval_js("""(() => {
        const titleBtn = document.querySelector('[data-qa-id="pine-script-title-button"]');
        const title = titleBtn ? titleBtn.innerText.slice(0,80) : 'no title';
        const hasAdd = !!document.querySelector('[title="Add to chart"]');
        const hasUpdate = !!document.querySelector('[title="Update on chart"]');
        return {title, hasAdd, hasUpdate};
    })()""")
    print(f"        -> after create {kind}: title={check.get('title')} hasAdd={check.get('hasAdd')} hasUpdate={check.get('hasUpdate')}")
    return check

async def main():
    start = time.time()
    print("=== DUAL INJECT START ===")
    # Load pine files
    with open(FINAL_PINE, 'r', encoding='utf-8') as f:
        final_code = f.read()
    with open(OVERLAY_PINE, 'r', encoding='utf-8') as f:
        overlay_code = f.read()
    print(f"Loaded FINAL {len(final_code)} bytes, OVERLAY {len(overlay_code)} bytes")
    ws_url = runner.get_ws_url()
    client = runner.CDPClient(ws_url)
    await client.connect()
    await client.find_tradingview_target()
    print(f"Connected to TradingView target {client.target_id}")
    # Grant permissions once
    try:
        await client.send_cmd("Browser.grantPermissions", {"permissions":["clipboardReadWrite","notifications"],"origin":"https://www.tradingview.com"})
    except Exception: pass
    # Step 1: Open pine editor and handle readonly before cleaning
    print("[1] Opening Pine Editor...")
    ro_state = await open_pine_editor(client)
    print(f"    -> ro_state={ro_state}")
    # Step 2: Clean existing chart
    print("[2] Cleaning existing chart...")
    clean_res = await clean_chart(client)
    print(f"    -> clean_res={json.dumps(clean_res, indent=2, ensure_ascii=False)}")
    await asyncio.sleep(1.5)
    # Verify clean
    verify1 = await verify_chart(client)
    print(f"    -> after clean: sources={json.dumps(verify1['sources'], ensure_ascii=False)}")
    # Step 3: Inject FINAL_OPTIMIZED_STRATEGY — create new Strategy blank first
    print("[3] Injecting FINAL_OPTIMIZED_STRATEGY.pine...")
    # Create new Strategy script
    await create_new_script(client, "Strategy")
    await open_pine_editor(client)
    res1 = await inject_pine(client, final_code, "FINAL_BASELINE", is_first=True)
    print(f"    -> inject FINAL result click={res1['click']} errors={res1['errors']}")
    if res1['errors']:
        print(f"    !! FINAL compile errors: {json.dumps(res1['errors'], indent=2)}")
    await asyncio.sleep(2)
    verify2 = await verify_chart(client)
    print(f"    -> after FINAL: sources={json.dumps(verify2['sources'], ensure_ascii=False)}")
    # Step 4: Inject CONFLUENCE_STUDY_OVERLAY — create new Indicator blank
    print("[4] Injecting CONFLUENCE_STUDY_OVERLAY.pine...")
    await create_new_script(client, "Indicator")
    await open_pine_editor(client)
    res2 = await inject_pine(client, overlay_code, "CONFLUENCE_STUDY", is_first=False)
    print(f"    -> inject OVERLAY result click={res2['click']} errors={res2['errors']}")
    if res2['errors']:
        print(f"    !! OVERLAY compile errors: {json.dumps(res2['errors'], indent=2)}")
    await asyncio.sleep(3)
    # Step 5: Verification
    print("[5] Final verification...")
    verify3 = await verify_chart(client)
    print(f"    -> final sources ({len(verify3['sources'])}): {json.dumps(verify3['sources'], ensure_ascii=False, indent=2)}")
    # Count custom indicators vs base
    base_titles = ["SPY", "NYSE Arca", "Ideas on chart", "Dividends", "Splits", "Earnings", "RollDatesCalculator", "FuturesContractExpiration", "LatestUpdatesSource", "Chart Events"]
    custom = [t for t in verify3['sources'] if any(k in t for k in ["FINAL", "BASELINE", "CONFLUENCE", "CONFLUENCE_STUDY", "CONFLUENCE_SWING"])]
    print(f"    -> custom count={len(custom)} titles={custom}")
    # Check for isStrategy flags? but overlay is indicator false, FINAL is strategy true
    print(f"    -> isStrategyFlags={verify3['isStrategyFlags']}")
    # Open strategy tester to verify FINAL_BASELINE metrics appear
    open_tester_js = """(() => {
        const testerBtn = Array.from(document.querySelectorAll('button, [role="button"], [data-name]')).find(b => /strategy tester/i.test(b.innerText || '') || /strategy tester/i.test(b.getAttribute('aria-label') || '') || b.getAttribute('data-name') === 'backtesting');
        if (testerBtn && !document.querySelector('[class*="reportContainer-"]')) { testerBtn.click(); return 'clicked_tester'; }
        return !!document.querySelector('[class*="reportContainer-"]') ? 'already_open' : 'no_btn';
    })()"""
    tester_res = await client.eval_js(open_tester_js)
    print(f"    -> tester: {tester_res}")
    await asyncio.sleep(2)
    scrape_js = """(() => {
        const report = document.querySelector('[class*="reportContainer-"]') || document.querySelector('[class*="wrapper-dmId9qUc"]') || document.querySelector('[class*="wrapper-yprR2JgA"]') || document.querySelector('[class*="reportContainer"]');
        if (!report) return { error: 'No report container found', bodySnippet: document.body.innerText.slice(0,800) };
        return { rawText: report.innerText.slice(0,6000) };
    })()"""
    report_data = await client.eval_js(scrape_js)
    if 'rawText' in report_data:
        raw = report_data['rawText']
        print(f"    -> report snippet: {raw[:1200]}")
        # Quick parse for key metrics
        has_final = "FINAL_BASELINE" in raw or "FINAL OPTIMIZED" in raw or "Net Profit" in raw
        print(f"    -> has FINAL_BASELINE in report? {has_final}")
    else:
        print(f"    -> report error: {report_data}")
    # Also capture screenshot via Page.captureScreenshot
    try:
        res = await client.send_cmd("Page.captureScreenshot", {"format":"png","captureBeyondViewport":False}, session_id=client.session_id)
        data = res.get('data','')
        if data:
            import base64
            out_path = os.path.join(ROOT, "metrics", "chart_screenshot.png")
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            with open(out_path, "wb") as f:
                f.write(base64.b64decode(data))
            print(f"    -> screenshot saved to {out_path} ({len(data)} b64)")
    except Exception as e:
        print(f"    -> screenshot failed: {e}")
    # DOM confirmation for total data sources = 12? base is 9-10, plus 2 = 11-12
    total_ok = len(custom) == 2
    print(f"=== DUAL INJECT SUMMARY ===")
    print(f"Cleaning removed: {clean_res.get('removed')}")
    print(f"FINAL injected: click={res1['click']} errors={len(res1['errors']) if res1['errors'] else 0}")
    print(f"OVERLAY injected: click={res2['click']} errors={len(res2['errors']) if res2['errors'] else 0}")
    print(f"Final custom count={len(custom)} (expected 2) -> {'PASS' if total_ok else 'FAIL'}")
    print(f"Free-tier compliance: {'PASS 2 slots occupied' if total_ok else 'FAIL'}")
    await client.close()
    elapsed = time.time() - start
    print(f"Elapsed {elapsed:.1f}s")
    return total_ok

if __name__ == '__main__':
    ok = asyncio.run(main())
    sys.exit(0 if ok else 1)
