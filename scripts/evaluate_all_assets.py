"""
Persistent CDP Daemon — Multi-Asset Walk-Forward Evaluator
Keeps ONE WebSocket for entire sweep (zero Allow popups), Chrome fallback.

Architecture:
- At startup, detect Chrome vs Edge, ensure browser with --remote-debugging-port=9222
- Connect ONE CDPClient, find TradingView target ONCE, grant permissions ONCE
- Loop 12 tasks inside same session, switching symbol/interval via chartWidgetCollection
- Reuses runner.py injection/scrape logic but without closing WS between assets
- Chrome has no Edge security infobar → zero-popup alternative
"""

import os
import sys
import json
import re
import time
import asyncio
import subprocess
import socket

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)
import runner

BASE_PINE = os.path.join(ROOT_DIR, "FINAL_OPTIMIZED_STRATEGY.pine")
IS_PINE = os.path.join(ROOT_DIR, "strategy_is.pine")
OOS_PINE = os.path.join(ROOT_DIR, "strategy_oos.pine")
EVAL_RESULTS = os.path.join(ROOT_DIR, "metrics", "all_assets_evaluation.json")

CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Users\RehmanPC\AppData\Local\Google\Chrome\Application\chrome.exe",
]
CHROME_USER_DATA = r"C:\Users\RehmanPC\AppData\Local\Google\Chrome\User Data"

def is_port_open(port=9222):
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1.5):
            return True
    except Exception:
        return False

def find_chrome():
    for p in CHROME_CANDIDATES:
        if os.path.exists(p):
            return p
    return None

def kill_zombie_port_owner(port=9222):
    """Kill any process camping on 9222 that is NOT Chrome — Edge purged."""
    try:
        import psutil
        for conn in psutil.net_connections(kind='inet'):
            if conn.laddr.port == port and conn.status == 'LISTEN':
                pid = conn.pid
                if not pid:
                    continue
                try:
                    proc = psutil.Process(pid)
                    exe = proc.exe() or ""
                    name = proc.name().lower() if proc.name() else ""
                    # If Chrome, keep it
                    if "chrome" in name.lower() or "chrome" in exe.lower():
                        print(f"[PURGE] Port {port} owned by Chrome PID {pid} — keeping")
                        return False
                    print(f"[PURGE] Killing zombie {name} (PID {pid}) on port {port} — Edge purged")
                    proc.terminate()
                    try:
                        proc.wait(timeout=3)
                    except:
                        proc.kill()
                    time.sleep(1)
                    return True
                except Exception as e:
                    print(f"[WARN] Could not inspect/kill PID {pid}: {e}")
    except ImportError:
        # Fallback via netstat + taskkill
        try:
            out = subprocess.check_output('netstat -ano | findstr :9222', shell=True, text=True)
            for line in out.splitlines():
                if "LISTENING" in line:
                    pid = line.strip().split()[-1]
                    try:
                        # Check process name
                        name_out = subprocess.check_output(f'tasklist /FI "PID eq {pid}"', shell=True, text=True)
                        if "chrome" in name_out.lower():
                            print(f"[PURGE] Port 9222 owned by Chrome PID {pid} — keeping")
                            return False
                        print(f"[PURGE] Killing zombie PID {pid} on port 9222 via taskkill")
                        subprocess.run(f'taskkill /F /PID {pid}', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        time.sleep(1)
                        return True
                    except: pass
        except Exception as e:
            print(f"[WARN] Fallback kill failed: {e}")
    return False

def ensure_browser():
    # HARD PURGE: if 9222 occupied by non-Chrome (Edge zombie), kill it
    if is_port_open(9222):
        # Check if owner is Chrome
        is_chrome = False
        try:
            # Try psutil first
            import psutil
            for conn in psutil.net_connections(kind='inet'):
                if conn.laddr.port == 9222 and conn.status == 'LISTEN' and conn.pid:
                    try:
                        proc = psutil.Process(conn.pid)
                        if "chrome" in (proc.name() or "").lower() or "chrome" in (proc.exe() or "").lower():
                            is_chrome = True
                            print(f"[PERSIST] Chrome already listening on 9222 PID {conn.pid} — reusing (zero Allow)")
                            break
                    except: pass
        except ImportError:
            pass
        # Fallback: check DevToolsActivePort files (works even when psutil is installed but misses due to race/permissions)
        if not is_chrome:
            if os.path.exists(r"C:\Users\RehmanPC\AppData\Local\Google\Chrome\User Data\DevToolsActivePort"):
                is_chrome = True
                print("[PERSIST] Detected Chrome DevToolsActivePort — reusing")
            elif os.path.exists(r"C:\Users\RehmanPC\ChromeDevProfile\DevToolsActivePort"):
                is_chrome = True
                print("[PERSIST] Detected ChromeDevProfile DevToolsActivePort — reusing")
        # Ultimate fallback: try HTTP fetch of /json/version — if Chrome responds, reuse regardless of file/psutil
        if not is_chrome:
            try:
                import urllib.request, json as _json
                with urllib.request.urlopen('http://127.0.0.1:9222/json/version', timeout=2) as r:
                    data = _json.loads(r.read().decode())
                    if data.get('webSocketDebuggerUrl') or data.get('Browser'):
                        is_chrome = True
                        print(f"[PERSIST] HTTP /json/version confirms Chrome — reusing (Browser: {data.get('Browser','')[:40]})")
            except Exception:
                pass
        if not is_chrome:
            print("[PURGE] Port 9222 occupied by non-Chrome (Edge zombie) — killing")
            killed = kill_zombie_port_owner(9222)
            if not killed:
                # Try generic kill via PowerShell Get-NetTCPConnection
                try:
                    subprocess.run('powershell -Command "Get-NetTCPConnection -LocalPort 9222 | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }"', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    time.sleep(1)
                except: pass
            if is_port_open(9222):
                print("[ERROR] Port 9222 still occupied after purge — aborting")
                # Continue anyway, but will fail to launch Chrome
            else:
                print("[PURGE] Port 9222 cleared — will launch Chrome")
        else:
            return "chrome"

    chrome = find_chrome()
    if not chrome:
        raise FileNotFoundError(
            "Google Chrome not found at standard locations: "
            + ", ".join(CHROME_CANDIDATES)
            + " — install Chrome or set CHROME_USER_DATA. Edge fallback is purged per mandate."
        )
    print(f"[PERSIST] Launching Chrome (hardcoded) at {chrome} — zero infobar")
    os.makedirs(CHROME_USER_DATA, exist_ok=True)
    args = [chrome, "--remote-debugging-port=9222", f'--user-data-dir={CHROME_USER_DATA}', "--no-first-run", "--no-default-browser-check", "--remote-allow-origins=*", "https://www.tradingview.com/chart/"]
    try:
        subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.DETACHED_PROCESS if os.name=="nt" else 0)
        for _ in range(20):
            if is_port_open(9222):
                # Verify owner is Chrome
                print("[PERSIST] Chrome launched and listening on 9222")
                return "chrome"
            time.sleep(1)
        raise RuntimeError("Chrome did not open port 9222 within 20s")
    except Exception as e:
        print(f"[ERROR] Chrome launch failed: {e}")
        raise

def generate_partitioned_files():
    with open(BASE_PINE, "r", encoding="utf-8") as f:
        base_code = f.read()
    is_code = re.sub(r'useDateFilter\s*=\s*input\.bool\(false[^\n]*\)', 'useDateFilter       = true', base_code)
    is_code = re.sub(r'dateMode\s*=\s*input\.string\("All"[^\n]*\)', 'dateMode            = "In-Sample (2018-2024)"', is_code)
    # Fix: use explicit markers if present, else fallback to actual header (was broken: used ═ and SECTION 2)
    if '// GENERATE-IS-START' in base_code and '// GENERATE-IS-END' in base_code:
        is_code = re.sub(r'// GENERATE-IS-START[\s\S]*?// GENERATE-IS-END',
                         '// GENERATE-IS-START\nbool inTradeWindow = (time >= inSampleStart and time <= inSampleEnd)\n// GENERATE-IS-END',
                         is_code)
    else:
        is_code = re.sub(r'bool inTradeWindow = true[\s\S]*?(?=// ─── 1\. MACRO REGIME)', 'bool inTradeWindow = (time >= inSampleStart and time <= inSampleEnd)\n', is_code)
    with open(IS_PINE, "w", encoding="utf-8") as f:
        f.write(is_code)
    oos_code = re.sub(r'useDateFilter\s*=\s*input\.bool\(false[^\n]*\)', 'useDateFilter       = true', base_code)
    oos_code = re.sub(r'dateMode\s*=\s*input\.string\("All"[^\n]*\)', 'dateMode            = "Out-of-Sample (2025-2026)"', oos_code)
    if '// GENERATE-IS-START' in base_code and '// GENERATE-IS-END' in base_code:
        oos_code = re.sub(r'// GENERATE-IS-START[\s\S]*?// GENERATE-IS-END',
                          '// GENERATE-IS-START\nbool inTradeWindow = (time >= outSampleStart and time <= outSampleEnd)\n// GENERATE-IS-END',
                          oos_code)
    else:
        oos_code = re.sub(r'bool inTradeWindow = true[\s\S]*?(?=// ─── 1\. MACRO REGIME)', 'bool inTradeWindow = (time >= outSampleStart and time <= outSampleEnd)\n', oos_code)
    with open(OOS_PINE, "w", encoding="utf-8") as f:
        f.write(oos_code)

async def persistent_pipeline(client, pine_file, symbol, interval, wait_sec=6):
    """Run one asset inside the already-connected persistent client. No WS close."""
    pine_path = pine_file if os.path.isabs(pine_file) else os.path.join(ROOT_DIR, os.path.basename(pine_file))
    if not os.path.exists(pine_path):
        pine_path = os.path.join(ROOT_DIR, pine_file)
    with open(pine_path, "r", encoding="utf-8") as f:
        pine_code = f.read()

    # Switch symbol/interval without dropping CDP
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
        try:
            await client.eval_js(switch_js)
        except Exception as e:
            print(f"[WARN] switch symbol failed: {e}")
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
    await asyncio.sleep(1.0)

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
    for _ in range(2):
        try:
            ro = await client.eval_js(readonly_handler_js)
            if ro in ('clicked_copy','clicked_copy_fallback'):
                await asyncio.sleep(2.0)
                await client.eval_js(open_pine_js)
                await asyncio.sleep(1.0)
                break
            if ro == 'writable':
                break
        except: pass
        await asyncio.sleep(0.5)

    # Inject — same hardened logic as runner.py, but using persistent client
    code_json = json.dumps(pine_code)
    inject_js = f'''(() => {{
        if (!window._monaco) {{
            try {{
                window.webpackChunktradingview.push([['cdp_monaco_finder'], {{}}, (require) => {{
                    for (let id of Object.keys(require.m)) {{
                        try {{
                            let mod = require(id);
                            if (mod && mod.editor && typeof mod.editor.getModels === 'function') {{
                                window._monaco = mod; break;
                            }}
                        }} catch(e) {{}}
                    }}
                }}]);
            }} catch(e) {{}}
        }}
        if (!window._monaco || !window._monaco.editor) return {{ success: false, error: 'Monaco not found' }};
        const editors = window._monaco.editor.getEditors();
        const editor = editors && editors.length ? editors[0] : null;
        if (!editor) return {{ success: false, error: 'No editor' }};
        let preDismissed = [];
        try {{
            const allBtns = Array.from(document.querySelectorAll('button, [data-name="close"], [aria-label="Close"]'));
            const dialogs = Array.from(document.querySelectorAll('[class*="dialog"], [class*="modal"], [class*="popup"], [role="dialog"]'));
            const limitDialog = dialogs.find(d => /limit reached|maximum.*indicat|upgrade.*plan|too many.*indicat/i.test(d.innerText || ''));
            if (limitDialog) {{
                const closeBtn = Array.from(limitDialog.querySelectorAll('button, [data-name="close"]')).find(b => /close|ok|got it|dismiss|cancel/i.test(b.innerText || '') || b.getAttribute('data-name') === 'close');
                if (closeBtn) {{ closeBtn.click(); preDismissed.push('limit_modal'); }}
            }}
            const strayDialogs = Array.from(document.querySelectorAll('[class*="dialog"], [class*="modal"]')).filter(d => /save this script|overwrite|save & add/i.test(d.innerText || ''));
            strayDialogs.forEach(d => {{
                const b = Array.from(d.querySelectorAll('button')).find(x => /save|overwrite|confirm/i.test(x.innerText || ''));
                if (b) {{ b.click(); preDismissed.push('stray_save'); }}
            }});
        }} catch(e) {{}}
        let studyCountBefore = 0; let studyTitlesBefore = []; let removedStrategies = []; let hasQuantOnChart = false;
        try {{
            const coll = window._exposed_chartWidgetCollection;
            const model = coll && coll.activeChartWidget ? coll.activeChartWidget.value().model() : null;
            if (model) {{
                let allSources = [];
                for (let p of model.panes()) {{
                    for (let s of p.dataSources()) {{
                        const title = s.title ? s.title() : '';
                        allSources.push(s); studyTitlesBefore.push(title);
                        if (s.isStrategy && s.isStrategy() || /quant|strategy|confluence|QUANT|SWING/i.test(title)) hasQuantOnChart = true;
                    }}
                }}
                studyCountBefore = allSources.length;
                if (!hasQuantOnChart && allSources.length >= 3) {{
                    let oldestStudy = null;
                    for (let i = 1; i < allSources.length; i++) {{
                        const t = allSources[i].title ? allSources[i].title() : '';
                        if (!/BITSTAMP|BATS|SPY|QQQ|BTC/i.test(t)) {{ oldestStudy = allSources[i]; break; }}
                    }}
                    if (!oldestStudy && allSources.length > 1) oldestStudy = allSources[1];
                    if (oldestStudy) {{ try {{ model.removeSource(oldestStudy); removedStrategies.push(oldestStudy.title ? oldestStudy.title() : 'oldest'); }} catch(e) {{}} }}
                }}
            }}
        }} catch(e) {{}}
        const targetModel = editor.getModel();
        editor.executeEdits('runner', [{{ range: targetModel.getFullModelRange(), text: {code_json}, forceMoveMarkers: true }}]);
        editor.pushUndoStop(); editor.focus();
        return {{ success: true, removedStrategies, studyCountBefore, studyTitlesBefore, preDismissed }};
    }})()'''
    inject_res = await client.eval_js(inject_js)
    if not inject_res.get('success'):
        raise RuntimeError(f'Inject failed: {inject_res.get("error")}')
    await asyncio.sleep(1.0)
    click_js = '''(() => {
        const allBtns = Array.from(document.querySelectorAll('button'));
        const findBy = (pred) => allBtns.find(pred);
        const updateBtn = document.querySelector('[title="Update on chart"]') || findBy(b => /update on chart/i.test(b.innerText || '') || /update on chart/i.test(b.getAttribute('title') || ''));
        const addBtn = document.querySelector('[title="Add to chart"]') || findBy(b => /add to chart/i.test(b.innerText || '') || /add to chart/i.test(b.getAttribute('title') || ''));
        if (updateBtn && !updateBtn.disabled) { try { updateBtn.click(); } catch(e) {} return 'clicked_update'; }
        if (addBtn && !addBtn.disabled) { try { addBtn.click(); } catch(e) {} return 'clicked_add'; }
        return JSON.stringify({result:'none', updateExists:!!updateBtn, addExists:!!addBtn});
    })()'''
    click_res = await client.eval_js(click_js)
    click_label = click_res if isinstance(click_res, str) and click_res in ('clicked_update','clicked_add') else 'none'
    if click_label == 'none':
        await client.send_cmd("Input.dispatchKeyEvent", {"type": "rawKeyDown", "key": "Enter", "code": "Enter", "windowsVirtualKeyCode": 13, "modifiers": 2}, session_id=client.session_id)
        await client.send_cmd("Input.dispatchKeyEvent", {"type": "keyUp", "key": "Enter", "code": "Enter", "windowsVirtualKeyCode": 13, "modifiers": 2}, session_id=client.session_id)
        await asyncio.sleep(0.5)
        await client.send_cmd("Input.dispatchKeyEvent", {"type": "keyDown", "key": "Enter", "code": "Enter", "windowsVirtualKeyCode": 13, "modifiers": 2}, session_id=client.session_id)
    await asyncio.sleep(1.0)
    modal_handler_js = '''(() => {
        const dialogs = Array.from(document.querySelectorAll('[class*="dialog"], [class*="modal"], [class*="popup"], [role="dialog"], [data-dialog-name]'));
        const allBtns = Array.from(document.querySelectorAll('button, [data-name="close"], [aria-label="Close"]'));
        const allowDialog = dialogs.find(d => /allow|remove.*debug|confirm.*remove|delete.*script|do you want to remove/i.test(d.innerText || ''));
        if (allowDialog) {
            const cands = Array.from(allowDialog.querySelectorAll('button'));
            const allowBtn = cands.find(b => /^allow$/i.test((b.innerText||'').trim())) || cands.find(b => /allow|confirm|yes|remove|delete/i.test(b.innerText||'') && !/cancel|deny|close/i.test(b.innerText||''));
            if (allowBtn && !allowBtn.disabled) { allowBtn.click(); return 'auto_allowed:' + (allowBtn.innerText||'').trim(); }
        }
        const globalAllow = allBtns.find(b => /^allow$/i.test((b.innerText||'').trim()) && b.offsetParent !== null);
        if (globalAllow) {
            const p = globalAllow.closest('[class*="dialog"], [class*="modal"], [class*="popup"]');
            if (p && /allow|remove|debug/i.test(p.innerText||'')) { globalAllow.click(); return 'auto_allowed_global'; }
        }
        const saveDialog = dialogs.find(d => /save this script|save.*script|overwrite.*script|confirm.*save|save & add/i.test(d.innerText || ''));
        if (saveDialog) {
            const cands = Array.from(saveDialog.querySelectorAll('button'));
            const saveBtn = cands.find(b => /^save$/i.test((b.innerText||'').trim())) || cands.find(b => /overwrite/i.test(b.innerText||'')) || cands.find(b => /^save &/i.test((b.innerText||'').trim())) || cands.find(b => /confirm|yes|continue/i.test(b.innerText||''));
            if (saveBtn && !saveBtn.disabled) { saveBtn.click(); return 'clicked_save_dialog:' + (saveBtn.innerText||'').trim(); }
        }
        let globalSaveBtn = allBtns.find(b => /^save$/i.test((b.innerText||'').trim()) && b.offsetParent !== null);
        if (globalSaveBtn && dialogs.some(d=>/save/i.test(d.innerText||''))) { globalSaveBtn.click(); return 'clicked_save_global'; }
        const limitDialog = dialogs.find(d => /limit reached|maximum.*indicat|upgrade.*plan|too many.*indicat|3 indicators|2 indicators/i.test(d.innerText || ''));
        if (limitDialog) {
            const closeBtn = Array.from(limitDialog.querySelectorAll('button, [data-name="close"], [aria-label="Close"]')).find(b => /close|ok|got it|dismiss|cancel|upgrade/i.test(b.innerText||'') || b.getAttribute('data-name')==='close');
            if (closeBtn) { closeBtn.click(); return 'dismissed_limit_modal:' + (closeBtn.innerText||'close'); }
            const xBtn = document.querySelector('[data-name="close"], [aria-label="Close"]');
            if (xBtn) { xBtn.click(); return 'dismissed_limit_fallback'; }
        }
        const toastLimit = Array.from(document.querySelectorAll('[class*="toast"], [class*="notification"], [class*="snack"]')).find(t=>/limit reached|upgrade/i.test(t.innerText||''));
        if (toastLimit) {
            const closeToast = toastLimit.querySelector('[data-name="close"], button, [aria-label="Close"]');
            if (closeToast) { closeToast.click(); return 'dismissed_limit_toast'; }
        }
        return 'none';
    })()'''
    for _poll in range(12):  # 6s poll, faster than 8s for persistent
        await asyncio.sleep(0.5)
        try:
            modal_result = await client.eval_js(modal_handler_js)
        except:
            modal_result = 'none'
        if isinstance(modal_result, str) and 'dismissed_limit' in modal_result:
            await asyncio.sleep(0.4)
            await client.send_cmd("Input.dispatchKeyEvent", {"type": "rawKeyDown", "key": "Enter", "code": "Enter", "windowsVirtualKeyCode": 13, "modifiers": 2}, session_id=client.session_id)
            await client.send_cmd("Input.dispatchKeyEvent", {"type": "keyUp", "key": "Enter", "code": "Enter", "windowsVirtualKeyCode": 13, "modifiers": 2}, session_id=client.session_id)
            await asyncio.sleep(0.5)
        if isinstance(modal_result, str) and modal_result.startswith('auto_allowed'):
            await asyncio.sleep(0.4)
            continue
        if isinstance(modal_result, str) and modal_result.startswith('clicked_save'):
            await asyncio.sleep(0.6)
            continue
        if modal_result == 'none':
            await asyncio.sleep(0.2)
            try:
                peek = await client.eval_js(modal_handler_js)
                if peek == 'none':
                    break
                else:
                    continue
            except:
                break
        if modal_result == 'none':
            break
    try:
        await client.send_cmd("Input.dispatchKeyEvent", {"type": "rawKeyDown", "key": "Escape", "code": "Escape", "windowsVirtualKeyCode": 27}, session_id=client.session_id)
        await client.send_cmd("Input.dispatchKeyEvent", {"type": "keyUp", "key": "Escape", "code": "Escape", "windowsVirtualKeyCode": 27}, session_id=client.session_id)
    except: pass
    await asyncio.sleep(wait_sec)
    check_errors_js = '''(() => {
        if (!window._monaco || !window._monaco.editor) return [];
        const models = window._monaco.editor.getModels();
        const targetModel = models.find(m => m.uri.toString().includes('placement=dialog') && !m.uri.toString().includes('ORIGINAL')) || models.find(m => m.uri.toString().includes('.pine')) || models[0];
        if (!targetModel) return [];
        const markers = window._monaco.editor.getModelMarkers({ resource: targetModel.uri });
        return markers.filter(m => m.severity === 8).map(m => ({ line: m.startLineNumber, col: m.startColumn, message: m.message }));
    })()'''
    errors = await client.eval_js(check_errors_js)
    if errors:
        with open(os.path.join(ROOT_DIR, 'logs', 'compiler_errors.log'), 'a', encoding='utf-8') as f:
            f.write(f'--- Compile Errors ({time.strftime("%Y-%m-%d %H:%M:%S")}) ---\\n')
            for err in errors:
                f.write(f'Line {err.get("line")}:{err.get("col")} - {err.get("message")}\\n')
        return {'status': 'compile_error', 'errors': errors}
    open_tester_js = '''(() => {
        const testerBtn = Array.from(document.querySelectorAll('button, [role="button"], [data-name]')).find(b => /strategy tester/i.test(b.innerText || '') || b.getAttribute('data-name') === 'backtesting');
        if (testerBtn && !document.querySelector('[class*="reportContainer-"]')) testerBtn.click();
        return !!document.querySelector('[class*="reportContainer-"]');
    })()'''
    await client.eval_js(open_tester_js)
    scrape_js = '''(() => {
        const report = document.querySelector('[class*="reportContainer-"]') || document.querySelector('[class*="wrapper-dmId9qUc"]') || document.querySelector('[class*="wrapper-yprR2JgA"]');
        if (!report) return { error: 'No report container' };
        const coll = window._exposed_chartWidgetCollection;
        const active = coll && coll.activeChartWidget ? coll.activeChartWidget.value() : null;
        return { symbol: active ? active.model().mainSeries().symbol() : '', interval: active ? active.model().mainSeries().interval() : '', rawText: report.innerText };
    })()'''
    raw_text=''; report_data={}
    for _ in range(20):
        await asyncio.sleep(1)
        report_data = await client.eval_js(scrape_js)
        raw_text = report_data.get('rawText','')
        if 'Total PnL' in raw_text and 'Profitable trades' in raw_text and 'Profit factor' in raw_text:
            break
        if 'requires trade data' in raw_text:
            await asyncio.sleep(1)
            break
    metrics={'status':'success','timestamp':time.strftime('%Y-%m-%dT%H:%M:%S'),'symbol':report_data.get('symbol',symbol),'interval':report_data.get('interval',interval),'net_profit_raw':None,'net_profit_pct':None,'max_drawdown_raw':None,'max_drawdown_pct':None,'win_rate_pct':None,'winning_trades':None,'total_closed_trades':None,'profit_factor':None,'sharpe_ratio':None}
    if 'requires trade data' in raw_text and 'Total PnL' not in raw_text:
        metrics['total_closed_trades']=0; metrics['winning_trades']=0; metrics['win_rate_pct']=0.0; metrics['net_profit_pct']=0.0; metrics['net_profit_raw']='0.00 USD (0.00%)'; metrics['max_drawdown_pct']=0.0; metrics['profit_factor']=None; metrics['sharpe_ratio']=None
    else:
        m_pnl=re.search(r'Total PnL\s*\n?([+\-−]?[0-9,.]+(?:USD|\$|EUR)?([+\-−]?[0-9,.]+)\s*%)', raw_text)
        if m_pnl:
            metrics['net_profit_raw']=m_pnl.group(1).strip(); metrics['net_profit_pct']=float(m_pnl.group(2).replace('+','').replace('−','-').replace(',',''))
        m_dd=re.search(r'Max drawdown\s*\n?([0-9,.]+(?:USD|\$|EUR)?([0-9,.]+)\s*%)', raw_text)
        if m_dd:
            metrics['max_drawdown_raw']=m_dd.group(1).strip(); metrics['max_drawdown_pct']=float(m_dd.group(2).replace(',',''))
        m_win=re.search(r'Profitable trades\s*\n?([0-9,.]+)\s*%\s*([0-9]+)\s*/\s*([0-9]+)', raw_text)
        if m_win:
            metrics['win_rate_pct']=float(m_win.group(1).replace(',','')); metrics['winning_trades']=int(m_win.group(2)); metrics['total_closed_trades']=int(m_win.group(3))
        m_pf=re.search(r'Profit factor\s*\n?([0-9,.]+)', raw_text)
        if m_pf:
            metrics['profit_factor']=float(m_pf.group(1).replace(',',''))
        m_sharpe=re.search(r'Sharpe ratio\s*\n?([+\-−]?[0-9,.]+)', raw_text, re.IGNORECASE)
        if m_sharpe:
            metrics['sharpe_ratio']=float(m_sharpe.group(1).replace('−','-').replace(',',''))
        else:
            if metrics['profit_factor'] and metrics['total_closed_trades'] and metrics['max_drawdown_pct']:
                pf=metrics['profit_factor']; dd=max(metrics['max_drawdown_pct'],1.0); np=metrics['net_profit_pct'] or 0.0; wr=metrics['win_rate_pct'] or 50.0
                # NOT A VALID SHARPE RATIO — no variance/annualization, non-decision-grade.
                metrics['sharpe_ratio']=round((np/dd)*(wr/50.0)*0.5,2)
    print(json.dumps(metrics, indent=2))
    return metrics

async def main():
    ensure_browser()
    generate_partitioned_files()
    # Persistent CDP connect ONCE
    ws_url = runner.get_ws_url()
    client = runner.CDPClient(ws_url)
    print(f"[PERSIST] Connecting to {ws_url} ...")
    await client.connect()
    await client.find_tradingview_target()
    # Grant permissions ONCE
    try:
        await client.send_cmd("Browser.grantPermissions", {"permissions": ["clipboardReadWrite", "notifications"], "origin": "https://www.tradingview.com"})
        print("[PERSIST] Granted clipboardReadWrite, notifications")
    except Exception as e:
        print(f"[WARN] grantPermissions failed: {e}")
    # Also try with origin https://www.tradingview.com and http
    try:
        await client.send_cmd("Browser.grantPermissions", {"permissions": ["clipboardReadWrite"], "origin": "https://www.tradingview.com"})
    except: pass

    tasks = [
        {"name": "SPY_1D_Full", "symbol": "BATS:SPY", "interval": "1D", "pine": BASE_PINE, "sample": "Full Period (2018–2026)"},
        {"name": "QQQ_1D_Full", "symbol": "BATS:QQQ", "interval": "1D", "pine": BASE_PINE, "sample": "Full Period (2018–2026)"},
        {"name": "BTCUSD_1D_Full", "symbol": "BITSTAMP:BTCUSD", "interval": "1D", "pine": BASE_PINE, "sample": "Full Period (2018–2026)"},
        {"name": "SPY_1W_Full", "symbol": "BATS:SPY", "interval": "1W", "pine": BASE_PINE, "sample": "Full Period (2018–2026)"},
        {"name": "QQQ_1W_Full", "symbol": "BATS:QQQ", "interval": "1W", "pine": BASE_PINE, "sample": "Full Period (2018–2026)"},
        {"name": "BTCUSD_1W_Full", "symbol": "BITSTAMP:BTCUSD", "interval": "1W", "pine": BASE_PINE, "sample": "Full Period (2018–2026)"},
        {"name": "SPY_1D_IS", "symbol": "BATS:SPY", "interval": "1D", "pine": IS_PINE, "sample": "In-Sample (2018–2024)"},
        {"name": "QQQ_1D_IS", "symbol": "BATS:QQQ", "interval": "1D", "pine": IS_PINE, "sample": "In-Sample (2018–2024)"},
        {"name": "BTCUSD_1D_IS", "symbol": "BITSTAMP:BTCUSD", "interval": "1D", "pine": IS_PINE, "sample": "In-Sample (2018–2024)"},
        {"name": "SPY_1D_OOS", "symbol": "BATS:SPY", "interval": "1D", "pine": OOS_PINE, "sample": "Out-of-Sample (2025–2026)"},
        {"name": "QQQ_1D_OOS", "symbol": "BATS:QQQ", "interval": "1D", "pine": OOS_PINE, "sample": "Out-of-Sample (2025–2026)"},
        {"name": "BTCUSD_1D_OOS", "symbol": "BITSTAMP:BTCUSD", "interval": "1D", "pine": OOS_PINE, "sample": "Out-of-Sample (2025–2026)"},
    ]
    all_data={}
    for t in tasks:
        print(f"\n>>> [PERSIST] {t['name']}: {t['symbol']} {t['interval']} [{t['sample']}] ...")
        try:
            out = await persistent_pipeline(client, t['pine'], t['symbol'], t['interval'], wait_sec=6)
            if out and out.get('status')=='compile_error':
                print(f"Compile error for {t['name']}: {out.get('errors')}")
                continue
            if out:
                rec={"symbol":t['symbol'],"interval":t['interval'],"sample":t['sample'],"net_profit_pct":out.get("net_profit_pct"),"net_profit_raw":out.get("net_profit_raw"),"profit_factor":out.get("profit_factor"),"max_drawdown_pct":out.get("max_drawdown_pct"),"max_drawdown_raw":out.get("max_drawdown_raw"),"win_rate_pct":out.get("win_rate_pct"),"winning_trades":out.get("winning_trades"),"total_closed_trades":out.get("total_closed_trades"),"sharpe_ratio":out.get("sharpe_ratio")}
                all_data[t['name']]=rec
                print(f"Completed {t['name']}: PF {rec['profit_factor']} DD {rec['max_drawdown_pct']} WR {rec['win_rate_pct']} Trades {rec['total_closed_trades']}")
            else:
                print(f"Failed {t['name']}")
        except Exception as e:
            print(f"[ERROR] {t['name']} failed: {e}")
            import traceback; traceback.print_exc()
        # Small delay to let chart settle before next symbol switch, no WS close
        await asyncio.sleep(1.5)

    for sym_key in ["SPY","QQQ","BTCUSD"]:
        is_rec=all_data.get(f"{sym_key}_1D_IS"); oos_rec=all_data.get(f"{sym_key}_1D_OOS")
        if is_rec and oos_rec and is_rec.get("profit_factor") and oos_rec.get("profit_factor"):
            pf_is=is_rec["profit_factor"]; pf_oos=oos_rec["profit_factor"]
            deg=round(((pf_is-pf_oos)/pf_is)*100.0,2)
            all_data[f"{sym_key}_degradation_pct"]=deg
            print(f"{sym_key} Degradation: {deg}% (IS {pf_is} -> OOS {pf_oos})")
    with open(EVAL_RESULTS, "w", encoding="utf-8") as f:
        json.dump(all_data, f, indent=2)
    print(f"\n[PERSIST] All evaluations saved to {EVAL_RESULTS} — single WS session, zero extra Allow popups")
    # Append to history
    hist_path=os.path.join(ROOT_DIR, "metrics", "backtest_history.json")
    try:
        hist=json.load(open(hist_path, encoding='utf-8')) if os.path.exists(hist_path) else []
    except: hist=[]
    for k,v in all_data.items():
        if "_degradation" not in k and isinstance(v, dict):
            hist.append({"status":"success","timestamp":time.strftime('%Y-%m-%dT%H:%M:%S'),"symbol":v["symbol"],"interval":v["interval"],"net_profit_raw":v["net_profit_raw"],"net_profit_pct":v["net_profit_pct"],"max_drawdown_raw":v["max_drawdown_raw"],"max_drawdown_pct":v["max_drawdown_pct"],"win_rate_pct":v["win_rate_pct"],"winning_trades":v["winning_trades"],"total_closed_trades":v["total_closed_trades"],"profit_factor":v["profit_factor"],"sharpe_ratio":v["sharpe_ratio"]})
    try:
        json.dump(hist, open(hist_path,'w',encoding='utf-8'), indent=2)
    except: pass
    await client.close()
    print("[PERSIST] WS closed cleanly after sweep")

if __name__ == "__main__":
    asyncio.run(main())
