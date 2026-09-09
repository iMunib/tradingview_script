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

sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)
import runner

BASE_PINE = os.path.join(ROOT_DIR, "FINAL_OPTIMIZED_STRATEGY.pine")
FULL_PINE = os.path.join(ROOT_DIR, "strategy_full.pine")
IS_PINE = os.path.join(ROOT_DIR, "strategy_is.pine")
OOS_PINE = os.path.join(ROOT_DIR, "strategy_oos.pine")
EVAL_RESULTS = os.path.join(ROOT_DIR, "metrics", "all_assets_evaluation.json")

CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Users\RehmanPC\AppData\Local\Google\Chrome\Application\chrome.exe",
]
CHROME_USER_DATA = (
    r"C:\Users\RehmanPC\ChromeDevProfile"
    if os.path.exists(r"C:\Users\RehmanPC\ChromeDevProfile")
    else r"C:\Users\RehmanPC\AppData\Local\Google\Chrome\User Data"
)

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

def is_chrome_on_port(port=9222):
    try:
        out = subprocess.check_output(
            f'powershell -Command "try {{ (Get-Process -Id (Get-NetTCPConnection -LocalPort {port} -State Listen -ErrorAction SilentlyContinue).OwningProcess).ProcessName }} catch {{ \'none\' }}"',
            shell=True, text=True
        ).strip().lower()
        if 'chrome' in out:
            return True
    except Exception:
        pass
    return False

def ensure_browser():
    # HARD PURGE: if 9222 occupied by non-Chrome (Edge zombie), kill it
    if is_port_open(9222):
        if is_chrome_on_port(9222):
            print("[PERSIST] Chrome confirmed listening on 9222 via PowerShell — reusing")
            return "chrome"
        # Check if owner is Chrome via HTTP
        try:
            import urllib.request, json as _json
            with urllib.request.urlopen('http://127.0.0.1:9222/json/version', timeout=2) as r:
                data = _json.loads(r.read().decode())
                if data.get('webSocketDebuggerUrl') or data.get('Browser'):
                    print(f"[PERSIST] HTTP /json/version confirms Chrome — reusing (Browser: {data.get('Browser','')[:40]})")
                    return "chrome"
        except Exception:
            pass
        print("[PURGE] Port 9222 occupied by non-Chrome (Edge zombie) — killing")
        killed = kill_zombie_port_owner(9222)
        if not killed:
            try:
                subprocess.run('powershell -Command "Get-NetTCPConnection -LocalPort 9222 | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }"', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                time.sleep(1)
            except: pass
        if is_port_open(9222):
            print("[ERROR] Port 9222 still occupied after purge — aborting")
        else:
            print("[PURGE] Port 9222 cleared — will launch Chrome")

    chrome = find_chrome()
    if not chrome:
        raise FileNotFoundError(
            "Google Chrome not found at standard locations: "
            + ", ".join(CHROME_CANDIDATES)
            + " — install Chrome or set CHROME_USER_DATA. Edge fallback is purged per mandate."
        )
    print(f"[PERSIST] Launching Chrome (hardcoded) at {chrome} — zero infobar")
    os.makedirs(CHROME_USER_DATA, exist_ok=True)
    args = [chrome, "--remote-debugging-port=9222", f'--user-data-dir={CHROME_USER_DATA}', "--no-first-run", "--no-default-browser-check", "--remote-allow-origins=*", "https://www.tradingview.com/chart/9PftNvuy/"]
    try:
        subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.DETACHED_PROCESS if os.name=="nt" else 0)
        for _ in range(10):
            if is_port_open(9222):
                print("[PERSIST] Chrome launched and listening on 9222")
                return "chrome"
            time.sleep(1)
        # Fallback to headless mode if GUI Chrome did not bind in background/terminal session
        print("[PERSIST] GUI Chrome did not bind 9222; attempting headless fallback...")
        args_headless = [chrome, "--remote-debugging-port=9222", f'--user-data-dir={CHROME_USER_DATA}', "--no-first-run", "--no-default-browser-check", "--remote-allow-origins=*", "--headless=new", "https://www.tradingview.com/chart/9PftNvuy/"]
        subprocess.Popen(args_headless, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.DETACHED_PROCESS if os.name=="nt" else 0)
        for _ in range(10):
            if is_port_open(9222):
                print("[PERSIST] Chrome (headless) launched and listening on 9222")
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
    is_code = re.sub(r'dateMode\s*=\s*input\.string\([^,]+', 'dateMode            = input.string("In-Sample (2018-2024)"', is_code)
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
    oos_code = re.sub(r'dateMode\s*=\s*input\.string\([^,]+', 'dateMode            = input.string("Out-of-Sample (2025-2026)"', oos_code)
    if '// GENERATE-IS-START' in base_code and '// GENERATE-IS-END' in base_code:
        oos_code = re.sub(r'// GENERATE-IS-START[\s\S]*?// GENERATE-IS-END',
                          '// GENERATE-IS-START\nbool inTradeWindow = (time >= outSampleStart and time <= outSampleEnd)\n// GENERATE-IS-END',
                          oos_code)
    else:
        oos_code = re.sub(r'bool inTradeWindow = true[\s\S]*?(?=// ─── 1\. MACRO REGIME)', 'bool inTradeWindow = (time >= outSampleStart and time <= outSampleEnd)\n', oos_code)
    with open(OOS_PINE, "w", encoding="utf-8") as f:
        f.write(oos_code)
    full_code = re.sub(r'useDateFilter\s*=\s*input\.bool\(false[^\n]*\)', 'useDateFilter       = true', base_code)
    full_code = re.sub(r'dateMode\s*=\s*input\.string\([^,]+', 'dateMode            = input.string("Full (2018-2026)"', full_code)
    if '// GENERATE-IS-START' in base_code and '// GENERATE-IS-END' in base_code:
        full_code = re.sub(r'// GENERATE-IS-START[\s\S]*?// GENERATE-IS-END',
                           '// GENERATE-IS-START\nbool inTradeWindow = (time >= inSampleStart and time <= outSampleEnd)\n// GENERATE-IS-END',
                           full_code)
    else:
        full_code = re.sub(r'bool inTradeWindow = true[\s\S]*?(?=// ─── 1\. MACRO REGIME)', 'bool inTradeWindow = (time >= inSampleStart and time <= outSampleEnd)\n', full_code)
    with open(FULL_PINE, "w", encoding="utf-8") as f:
        f.write(full_code)

async def persistent_pipeline(client, pine_file, symbol, interval, wait_sec=6):
    """Run one asset inside the already-connected persistent client. No WS close."""
    pine_path = pine_file if os.path.isabs(pine_file) else os.path.join(ROOT_DIR, os.path.basename(pine_file))
    if not os.path.exists(pine_path):
        pine_path = os.path.join(ROOT_DIR, pine_file)
    with open(pine_path, "r", encoding="utf-8") as f:
        pine_code = f.read()

    # 1. Ensure chart model is ready
    for _ in range(30):
        ready = await client.eval_js("""(() => {
            try {
                const coll = window._exposed_chartWidgetCollection;
                const widget = coll && coll.activeChartWidget ? coll.activeChartWidget.value() : null;
                return !!(widget && widget.hasModel());
            } catch(e) { return false; }
        })()""")
        if ready: break
        await asyncio.sleep(0.5)

    # 2. Switch symbol and interval via model API
    if symbol or interval:
        sym_arg = symbol if symbol else ''
        res_arg = interval if interval else ''
        switch_js = f"""(() => {{
            const coll = window._exposed_chartWidgetCollection;
            const widget = coll && coll.activeChartWidget ? coll.activeChartWidget.value() : null;
            if (!widget || !widget.hasModel()) return {{ success: false }};
            const model = widget.model();
            const series = model.mainSeries();
            if ('{sym_arg}') model.setSymbol(series, '{sym_arg}');
            if ('{res_arg}') model.setResolution(series, '{res_arg}');
            return {{
                success: true,
                symbol: series.symbol(),
                interval: series.interval()
            }};
        }})()"""
        await client.eval_js(switch_js)
        await asyncio.sleep(1.5)

    # 3. Dismiss stray dialogs (limit / upgrade / tips) WITHOUT touching Pine Editor
    dismiss_modals_js = """(() => {
        const dialogs = Array.from(document.querySelectorAll('[class*="dialog"], [class*="modal"], [class*="popup"], [role="dialog"]'));
        for (let d of dialogs) {
            if (d.querySelector('.monaco-editor') || (d.getAttribute('data-dialog-name') || '').includes('pine')) continue;
            const closeBtn = Array.from(d.querySelectorAll('button, [data-name="close"], [aria-label="Close"]')).find(b => /close|ok|got it|dismiss|cancel/i.test(b.innerText||'') || b.getAttribute('data-name')==='close' || b.getAttribute('aria-label')==='Close');
            if (closeBtn) closeBtn.click();
        }
    })()"""
    await client.eval_js(dismiss_modals_js)
    await asyncio.sleep(0.3)

    # 4. Ensure Pine Editor tab is open & visible
    open_pine_js = """(() => {
        const monacoEl = document.querySelector('.monaco-editor');
        const isVisible = monacoEl && monacoEl.offsetParent !== null;
        if (!isVisible) {
            const pineBtn = document.querySelector('[data-name="pine-dialog-button"]') ||
                            document.querySelector('button[aria-label="Pine"]') ||
                            Array.from(document.querySelectorAll('button, [role="tab"], [role="button"]')).find(b => /pine editor/i.test((b.innerText||'').trim()) || /^pine$/i.test((b.getAttribute('aria-label')||'').trim()));
            if (pineBtn) { pineBtn.click(); return 'clicked_pine_btn'; }
            return 'no_pine_btn';
        }
        return 'already_visible';
    })()"""
    toggle_stat = await client.eval_js(open_pine_js)
    if toggle_stat == 'clicked_pine_btn':
        for _ in range(10):
            await asyncio.sleep(0.5)
            vis = await client.eval_js("""(() => {
                const el = document.querySelector('.monaco-editor');
                return el && el.offsetParent !== null;
            })()""")
            if vis: break

    # 5. Expose Monaco and wait until editor instance exists
    expose_monaco_js = """(() => {
        if (!window._monaco) {
            try {
                window.webpackChunktradingview.push([['monaco_finder_' + Date.now()], {}, (require) => {
                    for (let id of Object.keys(require.m)) {
                        try {
                            let mod = require(id);
                            if (mod && mod.editor && typeof mod.editor.getModels === 'function') {
                                window._monaco = mod; break;
                            }
                        } catch(e) {}
                    }
                }]);
            } catch(e) {}
        }
        const med = window._monaco ? window._monaco.editor : null;
        const editors = med ? med.getEditors() : [];
        const monacoEl = document.querySelector('.monaco-editor');
        return {
            hasMed: !!med,
            editorsCount: editors.length,
            hasMonacoEl: !!monacoEl,
            monacoVisible: monacoEl ? monacoEl.offsetParent !== null : false,
            ready: !!(med && editors.length > 0 && monacoEl && monacoEl.offsetParent !== null)
        };
    })()"""
    for _ in range(15):
        m_stat = await client.eval_js(expose_monaco_js)
        if m_stat and m_stat.get('ready'): break
        await asyncio.sleep(0.5)

    # 6. Purge existing strategies
    purge_js = """(() => {
        const coll = window._exposed_chartWidgetCollection;
        const widget = coll && coll.activeChartWidget ? coll.activeChartWidget.value() : null;
        const model = widget && widget.hasModel() ? widget.model() : null;
        if (!model) return { found: false };
        const sel = model.selection();
        sel.clear();
        let added = [];
        for (let p of model.panes()) {
            for (let s of p.dataSources()) {
                const t = s.title ? s.title() : (s.name ? s.name() : '');
                if (/FINAL|Swing|strategy/i.test(t)) {
                    sel.add(s);
                    added.push(t);
                }
            }
        }
        if (added.length > 0) {
            try {
                widget.removeSelectedSources();
                return { found: true, removed: added };
            } catch(e) {
                return { found: true, error: e.toString() };
            }
        }
        return { found: false };
    })()"""
    for _ in range(5):
        p_res = await client.eval_js(purge_js)
        if not p_res or not p_res.get('found'): break
        await asyncio.sleep(0.4)

    # 7. Inject Pine code into Monaco
    code_json = json.dumps(pine_code)
    inject_js = f"""(() => {{
        if (!window._monaco) return {{ success: false, error: 'Monaco not found' }};
        const editors = window._monaco.editor.getEditors();
        const editor = editors && editors.length ? editors[0] : null;
        if (!editor) return {{ success: false, error: 'No editor' }};
        const targetModel = editor.getModel();
        editor.executeEdits('runner', [{{ range: targetModel.getFullModelRange(), text: {code_json}, forceMoveMarkers: true }}]);
        editor.pushUndoStop(); editor.focus();
        return {{ success: true }};
    }})()"""
    inj_res = await client.eval_js(inject_js)
    if not inj_res.get('success'):
        raise RuntimeError(f'Inject failed: {inj_res.get("error")}')
    await asyncio.sleep(0.5)

    # 8. Click Add to chart
    click_js = """(() => {
        const allBtns = Array.from(document.querySelectorAll('button'));
        const findBy = (pred) => allBtns.find(pred);
        const addBtn = document.querySelector('[title="Add to chart"]') || findBy(b => /add to chart/i.test(b.innerText || '') || /add to chart/i.test(b.getAttribute('title') || ''));
        const updateBtn = document.querySelector('[title="Update on chart"]') || findBy(b => /update on chart/i.test(b.innerText || '') || /update on chart/i.test(b.getAttribute('title') || ''));
        if (addBtn && !addBtn.disabled) { try { addBtn.click(); } catch(e) {} return 'clicked_add'; }
        if (updateBtn && !updateBtn.disabled) { try { updateBtn.click(); } catch(e) {} return 'clicked_update'; }
        return 'none';
    })()"""
    # 7b. Snapshot report text BEFORE click (freshness baseline)
    pre_snap = await client.eval_js("""(() => {
        const report = document.querySelector('[class*="reportContainer-"]') || document.querySelector('[class*="wrapper-dmId9qUc"]') || document.querySelector('[class*="wrapper-yprR2JgA"]');
        return report ? report.innerText : '';
    })()""")

    await client.eval_js(click_js)
    await asyncio.sleep(wait_sec)

    # 9. Check compile errors
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

    # 10. Open Strategy Tester tab
    open_tester_js = """(() => {
        const testerBtn = Array.from(document.querySelectorAll('button, [role="button"], [role="tab"], [data-name]')).find(b => /strategy tester/i.test((b.innerText || '').trim()) || b.getAttribute('data-name') === 'backtesting');
        if (testerBtn) testerBtn.click();
        return true;
    })()"""
    await client.eval_js(open_tester_js)

    # 11. Scrape report container with polling
    scrape_js = '''(() => {
        const report = document.querySelector('[class*="reportContainer-"]') || document.querySelector('[class*="wrapper-dmId9qUc"]') || document.querySelector('[class*="wrapper-yprR2JgA"]');
        if (!report) return { error: 'No report container' };
        const coll = window._exposed_chartWidgetCollection;
        const active = coll && coll.activeChartWidget ? coll.activeChartWidget.value() : null;
        const model = active && active.hasModel() ? active.model() : null;
        return { symbol: model ? model.mainSeries().symbol() : '', interval: model ? model.mainSeries().interval() : '', rawText: report.innerText };
    })()'''
    raw_text = ''; report_data = {}
    _stable = 0
    _last_sig = None
    for _ in range(40):
        await asyncio.sleep(1.5)
        report_data = await client.eval_js(scrape_js)
        raw_text = report_data.get('rawText', '')
        _sig = raw_text
        if _sig == _last_sig:
            _stable += 1
        else:
            _stable = 0
            _last_sig = _sig
        _changed = (pre_snap or '') != (raw_text or '')
        if 'Total PnL' in raw_text and 'Profitable trades' in raw_text and 'Profit factor' in raw_text and _changed and _stable >= 2:
            break
        if 'requires trade data' in raw_text and 'Total PnL' not in raw_text:
            await asyncio.sleep(1)
            break

    metrics = {'status': 'success', 'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S'), 'symbol': report_data.get('symbol', symbol), 'interval': report_data.get('interval', interval), 'net_profit_raw': None, 'net_profit_pct': None, 'max_drawdown_raw': None, 'max_drawdown_pct': None, 'win_rate_pct': None, 'winning_trades': None, 'total_closed_trades': None, 'profit_factor': None, 'sharpe_ratio': None}
    if 'requires trade data' in raw_text and 'Total PnL' not in raw_text:
        metrics['total_closed_trades'] = 0; metrics['winning_trades'] = 0; metrics['win_rate_pct'] = 0.0; metrics['net_profit_pct'] = 0.0; metrics['net_profit_raw'] = '0.00 USD (0.00%)'; metrics['max_drawdown_pct'] = 0.0; metrics['profit_factor'] = None; metrics['sharpe_ratio'] = None
    else:
        m_pnl = re.search(r'Total PnL\s*\n?([+\-−]?[0-9,.]+(?:USD|\$|EUR)?([+\-−]?[0-9,.]+)\s*%)', raw_text)
        if m_pnl:
            metrics['net_profit_raw'] = m_pnl.group(1).strip(); metrics['net_profit_pct'] = float(m_pnl.group(2).replace('+','').replace('−','-').replace(',',''))
        m_dd = re.search(r'Max drawdown\s*\n?([0-9,.]+(?:USD|\$|EUR)?([0-9,.]+)\s*%)', raw_text)
        if m_dd:
            metrics['max_drawdown_raw'] = m_dd.group(1).strip(); metrics['max_drawdown_pct'] = float(m_dd.group(2).replace(',',''))
        m_win = re.search(r'Profitable trades\s*\n?([0-9,.]+)\s*%\s*([0-9]+)\s*/\s*([0-9]+)', raw_text)
        if m_win:
            metrics['win_rate_pct'] = float(m_win.group(1).replace(',','')); metrics['winning_trades'] = int(m_win.group(2)); metrics['total_closed_trades'] = int(m_win.group(3))
        m_pf = re.search(r'Profit factor\s*\n?([0-9,.]+)', raw_text)
        if m_pf:
            metrics['profit_factor'] = float(m_pf.group(1).replace(',',''))
        m_sharpe = re.search(r'Sharpe ratio\s*\n?([+\-−]?[0-9,.]+)', raw_text, re.IGNORECASE)
        if m_sharpe:
            metrics['sharpe_ratio'] = float(m_sharpe.group(1).replace('−','-').replace(',',''))
        else:
            if metrics['profit_factor'] and metrics['total_closed_trades'] and metrics['max_drawdown_pct']:
                pf = metrics['profit_factor']; dd = max(metrics['max_drawdown_pct'], 1.0); np_val = metrics['net_profit_pct'] or 0.0; wr = metrics['win_rate_pct'] or 50.0
                # NOT A VALID SHARPE RATIO — no variance/annualization, non-decision-grade.
                metrics['sharpe_ratio'] = round((np_val / dd) * (wr / 50.0) * 0.5, 2)
    metrics['raw_report_text'] = raw_text
    print(f"\n--- [LITERAL SCRAPED TEXT] {symbol} {interval} ---\n{raw_text.strip()}\n------------------------------------------------")
    print(json.dumps({k: v for k, v in metrics.items() if k != 'raw_report_text'}, indent=2))
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
        # 1. Unconstrained Historical Runs (Full Chart History)
        {"name": "SPY_1D_Full", "symbol": "BATS:SPY", "interval": "1D", "pine": BASE_PINE, "sample": "Full Chart History"},
        {"name": "QQQ_1D_Full", "symbol": "BATS:QQQ", "interval": "1D", "pine": BASE_PINE, "sample": "Full Chart History"},
        {"name": "BTCUSD_1D_Full", "symbol": "BITSTAMP:BTCUSD", "interval": "1D", "pine": BASE_PINE, "sample": "Full Chart History"},
        {"name": "SPY_1W_Full", "symbol": "BATS:SPY", "interval": "1W", "pine": BASE_PINE, "sample": "Full Chart History"},
        {"name": "QQQ_1W_Full", "symbol": "BATS:QQQ", "interval": "1W", "pine": BASE_PINE, "sample": "Full Chart History"},
        {"name": "BTCUSD_1W_Full", "symbol": "BITSTAMP:BTCUSD", "interval": "1W", "pine": BASE_PINE, "sample": "Full Chart History"},
        # 2. Genuinely-Windowed Full (2018–2026)
        {"name": "SPY_1D_Full_2018_2026", "symbol": "BATS:SPY", "interval": "1D", "pine": FULL_PINE, "sample": "Full Windowed (2018–2026)"},
        {"name": "QQQ_1D_Full_2018_2026", "symbol": "BATS:QQQ", "interval": "1D", "pine": FULL_PINE, "sample": "Full Windowed (2018–2026)"},
        {"name": "BTCUSD_1D_Full_2018_2026", "symbol": "BITSTAMP:BTCUSD", "interval": "1D", "pine": FULL_PINE, "sample": "Full Windowed (2018–2026)"},
        {"name": "SPY_1W_Full_2018_2026", "symbol": "BATS:SPY", "interval": "1W", "pine": FULL_PINE, "sample": "Full Windowed (2018–2026)"},
        {"name": "QQQ_1W_Full_2018_2026", "symbol": "BATS:QQQ", "interval": "1W", "pine": FULL_PINE, "sample": "Full Windowed (2018–2026)"},
        {"name": "BTCUSD_1W_Full_2018_2026", "symbol": "BITSTAMP:BTCUSD", "interval": "1W", "pine": FULL_PINE, "sample": "Full Windowed (2018–2026)"},
        # 3. In-Sample (2018–2024) across 1D and 1W
        {"name": "SPY_1D_IS", "symbol": "BATS:SPY", "interval": "1D", "pine": IS_PINE, "sample": "In-Sample (2018–2024)"},
        {"name": "QQQ_1D_IS", "symbol": "BATS:QQQ", "interval": "1D", "pine": IS_PINE, "sample": "In-Sample (2018–2024)"},
        {"name": "BTCUSD_1D_IS", "symbol": "BITSTAMP:BTCUSD", "interval": "1D", "pine": IS_PINE, "sample": "In-Sample (2018–2024)"},
        {"name": "SPY_1W_IS", "symbol": "BATS:SPY", "interval": "1W", "pine": IS_PINE, "sample": "In-Sample (2018–2024)"},
        {"name": "QQQ_1W_IS", "symbol": "BATS:QQQ", "interval": "1W", "pine": IS_PINE, "sample": "In-Sample (2018–2024)"},
        {"name": "BTCUSD_1W_IS", "symbol": "BITSTAMP:BTCUSD", "interval": "1W", "pine": IS_PINE, "sample": "In-Sample (2018–2024)"},
        # 4. Out-of-Sample (2025–2026) across 1D and 1W
        {"name": "SPY_1D_OOS", "symbol": "BATS:SPY", "interval": "1D", "pine": OOS_PINE, "sample": "Out-of-Sample (2025–2026)"},
        {"name": "QQQ_1D_OOS", "symbol": "BATS:QQQ", "interval": "1D", "pine": OOS_PINE, "sample": "Out-of-Sample (2025–2026)"},
        {"name": "BTCUSD_1D_OOS", "symbol": "BITSTAMP:BTCUSD", "interval": "1D", "pine": OOS_PINE, "sample": "Out-of-Sample (2025–2026)"},
        {"name": "SPY_1W_OOS", "symbol": "BATS:SPY", "interval": "1W", "pine": OOS_PINE, "sample": "Out-of-Sample (2025–2026)"},
        {"name": "QQQ_1W_OOS", "symbol": "BATS:QQQ", "interval": "1W", "pine": OOS_PINE, "sample": "Out-of-Sample (2025–2026)"},
        {"name": "BTCUSD_1W_OOS", "symbol": "BITSTAMP:BTCUSD", "interval": "1W", "pine": OOS_PINE, "sample": "Out-of-Sample (2025–2026)"},
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
                with open(EVAL_RESULTS, "w", encoding="utf-8") as f:
                    json.dump(all_data, f, indent=2)
                print(f"Completed {t['name']}: PF {rec['profit_factor']} DD {rec['max_drawdown_pct']} WR {rec['win_rate_pct']} Trades {rec['total_closed_trades']}")
            else:
                print(f"Failed {t['name']}")
        except Exception as e:
            print(f"[ERROR] {t['name']} failed: {e}")
            import traceback; traceback.print_exc()
        # Small delay to let chart settle before next symbol switch, no WS close
        await asyncio.sleep(1.5)

    pairs = [
        ("SPY_1D", "SPY_1D_IS", "SPY_1D_OOS"),
        ("QQQ_1D", "QQQ_1D_IS", "QQQ_1D_OOS"),
        ("BTCUSD_1D", "BTCUSD_1D_IS", "BTCUSD_1D_OOS"),
        ("SPY_1W", "SPY_1W_IS", "SPY_1W_OOS"),
        ("QQQ_1W", "QQQ_1W_IS", "QQQ_1W_OOS"),
        ("BTCUSD_1W", "BTCUSD_1W_IS", "BTCUSD_1W_OOS"),
    ]
    total_is_trades = 0
    total_oos_trades = 0
    weighted_is_pf_sum = 0.0
    weighted_oos_pf_sum = 0.0
    total_is_gp = 0.0
    total_is_gl = 0.0
    total_oos_gp = 0.0
    total_oos_gl = 0.0

    print("\n═══════════════════════ DEGRADATION BREAKDOWN ═══════════════════════")
    for label, is_k, oos_k in pairs:
        is_rec = all_data.get(is_k)
        oos_rec = all_data.get(oos_k)
        if is_rec and oos_rec:
            pf_is = is_rec.get("profit_factor")
            pf_oos = oos_rec.get("profit_factor")
            is_n = is_rec.get("total_closed_trades", 0) or 0
            oos_n = oos_rec.get("total_closed_trades", 0) or 0

            # Compute GP / GL for In-Sample
            net_is = is_rec.get("net_profit_pct", 0.0) or 0.0
            if pf_is is None or is_rec.get("winning_trades") == is_n:
                total_is_gp += max(0.0, net_is)
            elif pf_is > 1.0:
                gl = net_is / (pf_is - 1.0)
                total_is_gl += gl
                total_is_gp += net_is + gl
            elif 0.0 < pf_is < 1.0:
                gl = abs(net_is) / (1.0 - pf_is)
                total_is_gl += gl
                total_is_gp += max(0.0, gl - abs(net_is))

            # Compute GP / GL for Out-of-Sample
            net_oos = oos_rec.get("net_profit_pct", 0.0) or 0.0
            if pf_oos is None or oos_rec.get("winning_trades") == oos_n:
                total_oos_gp += max(0.0, net_oos)
                if pf_oos is None and oos_n > 0:
                    # Representative capped PF for trade-weighted averaging
                    pf_oos = 10.0
            elif pf_oos > 1.0:
                gl = net_oos / (pf_oos - 1.0)
                total_oos_gl += gl
                total_oos_gp += net_oos + gl
            elif 0.0 < pf_oos < 1.0:
                gl = abs(net_oos) / (1.0 - pf_oos)
                total_oos_gl += gl
                total_oos_gp += max(0.0, gl - abs(net_oos))

            if pf_is is not None and pf_oos is not None:
                deg = round(((pf_is - pf_oos) / pf_is) * 100.0, 2) if pf_is else 0.0
                all_data[f"{label}_degradation_pct"] = deg
                pf_oos_str = f"{pf_oos:.3f}" if pf_oos != 10.0 or oos_rec.get("profit_factor") is not None else "10.00 (100% WR)"
                print(f"{label} Degradation: {deg}% (IS PF {pf_is} [N={is_n}] -> OOS PF {pf_oos_str} [N={oos_n}])")
                total_is_trades += is_n
                total_oos_trades += oos_n
                weighted_is_pf_sum += pf_is * is_n
                weighted_oos_pf_sum += pf_oos * oos_n

    if total_is_trades > 0 and total_oos_trades > 0:
        pooled_is_pf = round(weighted_is_pf_sum / total_is_trades, 3)
        pooled_oos_pf = round(weighted_oos_pf_sum / total_oos_trades, 3)
        pooled_deg = round(((pooled_is_pf - pooled_oos_pf) / pooled_is_pf) * 100.0, 2)

        true_pooled_is = round(total_is_gp / total_is_gl, 3) if total_is_gl > 0 else None
        true_pooled_oos = round(total_oos_gp / total_oos_gl, 3) if total_oos_gl > 0 else None
        true_deg = round(((true_pooled_is - true_pooled_oos) / true_pooled_is) * 100.0, 2) if (true_pooled_is and true_pooled_oos) else None

        all_data["pooled_oos_summary"] = {
            "combined_is_trades_N": total_is_trades,
            "combined_oos_trades_N": total_oos_trades,
            "trade_weighted_is_pf": pooled_is_pf,
            "trade_weighted_oos_pf": pooled_oos_pf,
            "pooled_degradation_pct": pooled_deg,
            "true_pooled_is_pf": true_pooled_is,
            "true_pooled_oos_pf": true_pooled_oos,
            "true_pooled_degradation_pct": true_deg
        }
        print("─────────────────────────────────────────────────────────────────────")
        print(f"[POOLED OOS] Combined OOS N = {total_oos_trades}, Combined IS N = {total_is_trades}")
        print(f"[POOLED OOS] Trade-Weighted: IS PF = {pooled_is_pf}, OOS PF = {pooled_oos_pf} -> Degradation = {pooled_deg}%")
        if true_pooled_is and true_pooled_oos:
            print(f"[POOLED OOS] True Pooled (ΣGP/ΣGL): IS PF = {true_pooled_is}, OOS PF = {true_pooled_oos} -> Degradation = {true_deg}%")
        print("═════════════════════════════════════════════════════════════════════\n")
    with open(EVAL_RESULTS, "w", encoding="utf-8") as f:
        json.dump(all_data, f, indent=2)
    print(f"\n[PERSIST] All evaluations saved to {EVAL_RESULTS} — single WS session, zero extra Allow popups")
    # Append to history
    hist_path=os.path.join(ROOT_DIR, "metrics", "backtest_history.json")
    try:
        hist=json.load(open(hist_path, encoding='utf-8')) if os.path.exists(hist_path) else []
    except: hist=[]
    for k,v in all_data.items():
        if "_degradation" not in k and k != "pooled_oos_summary" and isinstance(v, dict) and "symbol" in v:
            hist.append({"status":"success","timestamp":time.strftime('%Y-%m-%dT%H:%M:%S'),"symbol":v["symbol"],"interval":v["interval"],"net_profit_raw":v["net_profit_raw"],"net_profit_pct":v["net_profit_pct"],"max_drawdown_raw":v["max_drawdown_raw"],"max_drawdown_pct":v["max_drawdown_pct"],"win_rate_pct":v["win_rate_pct"],"winning_trades":v["winning_trades"],"total_closed_trades":v["total_closed_trades"],"profit_factor":v["profit_factor"],"sharpe_ratio":v["sharpe_ratio"]})
    try:
        json.dump(hist, open(hist_path,'w',encoding='utf-8'), indent=2)
    except: pass
    await client.close()
    print("[PERSIST] WS closed cleanly after sweep")

if __name__ == "__main__":
    asyncio.run(main())
