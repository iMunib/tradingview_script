"""
Single-Script Live Deployment — Master FINAL_BASELINE
- Clears chart via model.removeSource()
- Injects FINAL_OPTIMIZED_STRATEGY.pine (230 lines, minimalist 2-row HUD)
- Verifies exactly 1 custom strategy, screenshot to metrics/clean_chart_screenshot.png
"""
import asyncio, json, os, sys, time, pathlib, base64
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import runner
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
ROOT = pathlib.Path(__file__).resolve().parent.parent
FINAL_PINE = ROOT / "FINAL_OPTIMIZED_STRATEGY.pine"
SCREENSHOT = ROOT / "metrics" / "clean_chart_screenshot.png"

async def create_new_strategy(client):
    # Open title menu -> Create new -> Strategy
    await client.eval_js("""(() => {
        const btn = document.querySelector('[data-qa-id="pine-script-title-button"]');
        if (btn && btn.getAttribute('aria-expanded')==='false') btn.click();
        return 'opened if needed';
    })()""")
    await asyncio.sleep(1.0)
    await client.eval_js("""(() => {
        const titleBtn = document.querySelector('[data-qa-id="pine-script-title-button"]');
        const menu = titleBtn ? document.getElementById(titleBtn.getAttribute('aria-controls')) : null;
        const createNew = menu ? Array.from(menu.querySelectorAll('[role="menuitem"]')).find(el=>/Create new/i.test(el.innerText)) : null;
        if (createNew) createNew.dispatchEvent(new MouseEvent('mouseover',{bubbles:true}));
        return !!createNew;
    })()""")
    await asyncio.sleep(0.6)
    res = await client.eval_js("""(() => {
        const sub = Array.from(document.querySelectorAll('[role="menu"]')).find(m=> m.innerText.includes('Indicator') && m.innerText.includes('Strategy'));
        let target = null;
        if (sub) target = Array.from(sub.querySelectorAll('[role="menuitem"]')).find(el=> el.innerText.trim().startsWith('Strategy'));
        if (!target) target = Array.from(document.querySelectorAll('[role="menuitem"]')).find(el=> el.innerText.trim().startsWith('Strategy'));
        if (target) { target.click(); return 'clicked Strategy'; }
        return 'not found';
    })()""")
    print(f"  -> create Strategy: {res}")
    await asyncio.sleep(2.2)
    state = await client.eval_js("""(() => {
        const titleBtn = document.querySelector('[data-qa-id="pine-script-title-button"]');
        return {title: titleBtn?titleBtn.innerText.slice(0,60):'no title', hasAdd: !!document.querySelector('[title="Add to chart"]'), hasUpdate: !!document.querySelector('[title="Update on chart"]')};
    })()""")
    print(f"  -> after create: {state}")
    return state

async def main():
    print("=== SINGLE DEPLOY START ===")
    with open(FINAL_PINE, 'r', encoding='utf-8') as f:
        pine_code = f.read()
    print(f"Loaded FINAL {len(pine_code)} bytes, {len(pine_code.splitlines())} lines")
    ws_url = runner.get_ws_url()
    client = runner.CDPClient(ws_url)
    await client.connect()
    await client.find_tradingview_target()
    print(f"Connected {client.target_id}")
    try:
        await client.send_cmd("Browser.grantPermissions", {"permissions":["clipboardReadWrite","notifications"],"origin":"https://www.tradingview.com"})
    except: pass

    # Open pine editor and handle readonly
    open_js = """(() => {
        const hasEditor = !!document.querySelector('.monaco-editor');
        if (!hasEditor) {
            const pineBtn = document.querySelector('[data-name="pine-dialog-button"]') || document.querySelector('button[aria-label="Pine"]');
            if (pineBtn) pineBtn.click();
        }
        return !!document.querySelector('.monaco-editor');
    })()"""
    await client.eval_js(open_js)
    await asyncio.sleep(1.2)
    # Handle historical version
    ro_js = """(() => {
        const dlg = document.querySelector('[data-name="pine-dialog"]');
        const text = dlg ? dlg.innerText : '';
        if (text.includes('This is a historical version') || text.includes('restore this version')) {
            const link = document.querySelector('a.link-r4uFtjgt') || Array.from(document.querySelectorAll('a')).find(a=>/restore this version/i.test(a.innerText));
            if (link) { link.click(); return 'clicked restore'; }
        }
        return 'writable';
    })()"""
    for _ in range(5):
        r = await client.eval_js(ro_js)
        if r.startswith('clicked'): 
            await asyncio.sleep(2.5)
            break
        if r=='writable': break
        await asyncio.sleep(0.6)
    print(f"Editor ready: {r}")

    # Clear chart
    print("[1] Clearing chart...")
    clean_js = """(() => {
        let removed=[];
        try {
            const coll = window._exposed_chartWidgetCollection;
            const model = coll && coll.activeChartWidget ? coll.activeChartWidget.value().model() : null;
            if (model) {
                let all=[];
                for (let p of model.panes()) for (let s of p.dataSources()) all.push(s);
                let toRemove=[];
                for (let s of all) {
                    let t=''; try{t=s.title?s.title():''}catch(e){}
                    if (/FINAL|BASELINE|CONFLUENCE|SWING|QUANT|strategy/i.test(t) || /\\(14, 2\\.8|\\(2\\.8,/.test(t)) {
                        toRemove.push(s);
                    }
                }
                for (let s of toRemove) {
                    try { let t=s.title?s.title():''; model.removeSource(s); removed.push(t); } catch(e){}
                }
            }
        } catch(e){ return {error:e.toString(), removed} }
        return {removed, count: removed.length};
    })()"""
    clean_res = await client.eval_js(clean_js)
    print(f"  -> clean: {json.dumps(clean_res, ensure_ascii=False)}")
    # Handle Allow dialogs
    for _ in range(6):
        allow_js = """(() => {
            const dlg = Array.from(document.querySelectorAll('[class*="dialog"],[role="dialog"]')).find(d=>/allow|remove.*debug/i.test(d.innerText));
            if (dlg) {
                const btn = Array.from(dlg.querySelectorAll('button')).find(b=>/^allow$/i.test(b.innerText.trim()));
                if (btn) { btn.click(); return 'allowed'; }
            }
            const global = Array.from(document.querySelectorAll('button')).find(b=>/^allow$/i.test(b.innerText.trim()) && b.offsetParent!==null);
            if (global) { global.click(); return 'allowed global'; }
            return 'none';
        })()"""
        m = await client.eval_js(allow_js)
        if m=='none': break
        await asyncio.sleep(0.8)
    await asyncio.sleep(1.5)

    # Verify clean
    verify_js = """(() => {
        const coll = window._exposed_chartWidgetCollection;
        const model = coll.activeChartWidget.value().model();
        let sources=[];
        for (let p of model.panes()) for (let s of p.dataSources()) sources.push(s.title?s.title():'');
        return sources;
    })()"""
    after_clean = await client.eval_js(verify_js)
    print(f"  -> after clean sources ({len(after_clean)}): {after_clean}")

    # Create new Strategy blank
    print("[2] Creating new Strategy blank...")
    await create_new_strategy(client)
    await client.eval_js(open_js)
    await asyncio.sleep(1.0)

    # Inject pine
    print("[3] Injecting FINAL...")
    code_json = json.dumps(pine_code)
    inject_js = f"""(async () => {{
        if (!window._monaco) {{
            try {{
                window.webpackChunktradingview.push([['cdp_monaco_finder'],{{}},(require)=>{{
                    for(let id of Object.keys(require.m)){{ try{{ let mod=require(id); if(mod&&mod.editor&&typeof mod.editor.getModels==='function'){{window._monaco=mod; break;}} }}catch(e){{}} }}
                }}]);
            }}catch(e){{}}
        }}
        const editor = window._monaco.editor.getEditors()[0];
        if (!editor) return {{success:false, error:'no editor'}};
        const model = editor.getModel();
        editor.executeEdits('deploy', [{{range: model.getFullModelRange(), text: {code_json}, forceMoveMarkers:true}}]);
        editor.pushUndoStop(); editor.focus();
        return {{success:true}};
    }})()"""
    inj = await client.eval_js(inject_js)
    print(f"  -> inject: {inj}")
    await asyncio.sleep(1.2)

    # Click Add to Chart (force Add)
    click_js = """(() => {
        const addBtn = document.querySelector('[title="Add to chart"]');
        const updBtn = document.querySelector('[title="Update on chart"]');
        if (addBtn && !addBtn.disabled) { addBtn.click(); return 'clicked_add'; }
        if (updBtn && !updBtn.disabled) { updBtn.click(); return 'clicked_update'; }
        return 'none';
    })()"""
    click_res = await client.eval_js(click_js)
    print(f"  -> click: {click_res}")
    if click_res=='none':
        await client.send_cmd("Input.dispatchKeyEvent", {"type":"rawKeyDown","key":"Enter","code":"Enter","windowsVirtualKeyCode":13,"modifiers":2}, session_id=client.session_id)
        await client.send_cmd("Input.dispatchKeyEvent", {"type":"keyUp","key":"Enter","code":"Enter","windowsVirtualKeyCode":13,"modifiers":2}, session_id=client.session_id)
        await asyncio.sleep(0.6)
    await asyncio.sleep(1.0)

    # Handle dialogs (Save, Allow, limit) within 500ms poller
    modal_js = """(() => {
        const dialogs = Array.from(document.querySelectorAll('[class*="dialog"],[role="dialog"]'));
        const saveDlg = dialogs.find(d=>/save this script|overwrite/i.test(d.innerText));
        if (saveDlg) {
            const btn = Array.from(saveDlg.querySelectorAll('button')).find(b=>/^save$/i.test(b.innerText.trim()) || /overwrite/i.test(b.innerText));
            if (btn) { btn.click(); return 'save'; }
        }
        const allowDlg = dialogs.find(d=>/allow/i.test(d.innerText));
        if (allowDlg) {
            const btn = Array.from(allowDlg.querySelectorAll('button')).find(b=>/^allow$/i.test(b.innerText.trim()));
            if (btn) { btn.click(); return 'allow'; }
        }
        const limitDlg = dialogs.find(d=>/limit reached|upgrade/i.test(d.innerText));
        if (limitDlg) {
            const btn = limitDlg.querySelector('button');
            if (btn) btn.click();
            return 'limit';
        }
        return 'none';
    })()"""
    for _ in range(16):
        await asyncio.sleep(0.5)
        r = await client.eval_js(modal_js)
        if r!='none':
            print(f"  -> modal {r}")
            await asyncio.sleep(0.8)
        else:
            # check if no dialogs remain
            peek = await client.eval_js(modal_js)
            if peek=='none': break
    try:
        await client.send_cmd("Input.dispatchKeyEvent", {"type":"rawKeyDown","key":"Escape","code":"Escape","windowsVirtualKeyCode":27}, session_id=client.session_id)
        await client.send_cmd("Input.dispatchKeyEvent", {"type":"keyUp","key":"Escape","code":"Escape","windowsVirtualKeyCode":27}, session_id=client.session_id)
    except: pass
    await asyncio.sleep(4)

    # Check compile errors
    err_js = """(() => {
        if (!window._monaco) return [];
        const models = window._monaco.editor.getModels();
        const m = models.find(x=>x.uri.toString().includes('placement=dialog')) || models[0];
        const markers = window._monaco.editor.getModelMarkers({resource: m.uri});
        return markers.filter(x=>x.severity===8).map(x=>({line:x.startLineNumber, msg:x.message}));
    })()"""
    errs = await client.eval_js(err_js)
    print(f"  -> compile errors: {errs}")

    # Verify
    print("[4] Verifying...")
    verify = await client.eval_js("""(() => {
        const coll = window._exposed_chartWidgetCollection;
        const model = coll.activeChartWidget.value().model();
        let sources=[];
        for(let p of model.panes()) for(let s of p.dataSources()) sources.push({title:s.title?s.title():'', isStrat: s.isStrategy?s.isStrategy():false});
        return sources;
    })()""")
    print(f"  -> sources: {json.dumps(verify, indent=2, ensure_ascii=False)}")
    custom = [s for s in verify if any(k in s['title'] for k in ['FINAL','BASELINE'])]
    print(f"  -> custom count {len(custom)}: {[c['title'] for c in custom]}")
    # Check Strategy Tester metrics
    await client.eval_js("""(() => {
        const btn = Array.from(document.querySelectorAll('button')).find(b=>/strategy tester/i.test(b.innerText||b.getAttribute('aria-label')||''));
        if (btn && !document.querySelector('[class*="reportContainer"]')) btn.click();
        return 'tester check';
    })()""")
    await asyncio.sleep(2.5)
    report = await client.eval_js("""(() => {
        const rep = document.querySelector('[class*="reportContainer"]') || document.querySelector('.layout__area--bottom');
        return rep ? rep.innerText.slice(0,3000) : 'no report';
    })()""")
    print(f"  -> report snippet: {report[:1200]}")
    has_metrics = 'Total PnL' in report and 'Profit factor' in report
    print(f"  -> has metrics: {has_metrics}")

    # Screenshot
    try:
        res = await client.send_cmd("Page.captureScreenshot", {"format":"png","captureBeyondViewport":False}, session_id=client.session_id)
        import base64
        data = res.get('data','')
        if data:
            SCREENSHOT.write_bytes(base64.b64decode(data))
            print(f"  -> screenshot saved to {SCREENSHOT} ({len(data)} b64)")
    except Exception as e:
        print(f"  -> screenshot fail {e}")

    # HUD check: ensure only 2-row HUD exists, no oscillator plots
    hud_check = await client.eval_js("""(() => {
        const bottom = document.querySelector('.layout__area--bottom');
        const hasBuy = document.body.innerText.includes('BUY');
        const hasExit = document.body.innerText.includes('EXIT');
        // Look for HUD table
        const hud = document.body.innerText.includes('MARKET REGIME') && document.body.innerText.includes('CURRENT STATUS');
        return {hasBuy, hasExit, hud, bottomSnippet: bottom?bottom.innerText.slice(0,800):'no bottom'};
    })()""")
    print(f"  -> HUD check: {hud_check}")

    ok = len(custom)==1 and has_metrics
    print(f"=== SINGLE DEPLOY {'PASS' if ok else 'FAIL'} ===")
    print(f"  Custom 1: {len(custom)==1} Metrics: {has_metrics} Errors: {errs}")
    await client.close()
    return ok

if __name__ == '__main__':
    ok = asyncio.run(main())
    sys.exit(0 if ok else 1)
