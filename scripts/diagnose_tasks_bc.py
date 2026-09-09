"""
Phase 0 diagnostics v4 - Tasks B, C.1, C.2, C.3.

Root-cause fixes (from live probing):
  1. ONE-PHASE REPORT LAG: after Add, TradingView recompiles asynchronously;
     naive scraping reads the PREVIOUS injection's numbers. FIX: poll until the
     parsed total_closed_trades STABILIZES (3 consecutive identical reads, 2s
     apart) AND, for BASE phases, equals the EXPECTED N from the authoritative
     baseline sweep (metrics/all_assets_evaluation.json). This is deterministic.
  2. GP/GL live in `.layout__area--bottom` ("Performance analysis" section).
  3. C.2 trades: enumerate the strategy data-source methods WHILE the strategy
     is on chart (isStrategy() only resolves during the live phase); capture any
     array-returning trade accessor.
  4. C.3 regime probe: indicator has no tester report; poll legend block with a
     long settle (compute 2500+ bars first).

BTCUSD regime values already captured in prior turn (IS_RV 5.1562 / OOS_RV 3.4257
/ IS_ABOVE 83.81 / OOS_ABOVE 82.66 / N 2557,617); v4 re-derives all 3 for a clean,
uniform pass but keeps them if the probe proves flaky.

Expected N map (authoritative baseline sweep):
  SPY IS 33, QQQ IS 31, BTCUSD IS 38; SPY OOS 7, QQQ OOS 7, BTCUSD OOS 6.
"""

import os, sys, json, re, time, asyncio

sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)
import runner

IS_PINE = os.path.join(ROOT_DIR, "strategy_is.pine")
OOS_PINE = os.path.join(ROOT_DIR, "strategy_oos.pine")
DIAG_DIR = os.path.join(ROOT_DIR, ".diag_tmp")
os.makedirs(DIAG_DIR, exist_ok=True)
NOFED_IS_PINE = os.path.join(DIAG_DIR, "strategy_is_nofed.pine")
NOFED_OOS_PINE = os.path.join(DIAG_DIR, "strategy_oos_nofed.pine")
REGIME_PROBE_PINE = os.path.join(DIAG_DIR, "diag_regime_probe.pine")
RESULTS_PATH = os.path.join(ROOT_DIR, "metrics", "diag_tasks_bc.json")

EXPECTED_N = {
    'SPY_1D_IS': 33, 'QQQ_1D_IS': 31, 'BTCUSD_1D_IS': 38,
    'SPY_1D_OOS': 7, 'QQQ_1D_OOS': 7, 'BTCUSD_1D_OOS': 6,
}

REGIME_PROBE_SRC = '''//@version=5
indicator("DIAG_PROBE_REGIME", overlay=false, precision=4)
atr = ta.atr(14)
rv = close > 0 ? atr / close * 100.0 : 0.0
wEma = request.security(syminfo.tickerid, "1W", ta.ema(close, 200)[1], lookahead=barmerge.lookahead_off)
above = not na(wEma) ? (close > wEma ? 1 : 0) : 0
var float sumRV_IS = 0.0
var int   nIS = 0
var int   sumAbove_IS = 0
var float sumRV_OOS = 0.0
var int   nOOS = 0
var int   sumAbove_OOS = 0
inIS  = time >= timestamp(2018, 1, 1, 0, 0) and time <= timestamp(2024, 12, 31, 23, 59)
inOOS = time >= timestamp(2025, 1, 1, 0, 0) and time <= timestamp(2026, 12, 31, 23, 59)
if inIS
    sumRV_IS += rv
    nIS += 1
    sumAbove_IS += above
if inOOS
    sumRV_OOS += rv
    nOOS += 1
    sumAbove_OOS += above
plot(nIS > 0 ? sumRV_IS / nIS : na, title="IS_RV")
plot(nOOS > 0 ? sumRV_OOS / nOOS : na, title="OOS_RV")
plot(nIS > 0 ? 100.0 * sumAbove_IS / nIS : na, title="IS_ABOVE_PCT")
plot(nOOS > 0 ? 100.0 * sumAbove_OOS / nOOS : na, title="OOS_ABOVE_PCT")
plot(nIS / 1000.0, title="IS_NK")
plot(nOOS / 1000.0, title="OOS_NK")
'''

SETTLE_JS = """(() => { try { const c=window._exposed_chartWidgetCollection; const w=c&&c.activeChartWidget?c.activeChartWidget.value():null; if(!w||!w.hasModel())return{ready:false,why:'no model'}; const m=w.model(); const s=m.mainSeries(); if(!s)return{ready:false,why:'no series'}; let sym=''; try{sym=s.symbol();}catch(e){return{ready:false,why:'no symbol'};} return {ready:true,symbol:sym,interval:s.interval()}; } catch(e){ return {ready:false,why:String(e)}; } })()"""
SWITCH_JS = """(() => { const c=window._exposed_chartWidgetCollection; const w=c&&c.activeChartWidget?c.activeChartWidget.value():null; if(!w||!w.hasModel())return{success:false}; const m=w.model(); const s=m.mainSeries(); if('{sym}')m.setSymbol(s,'{sym}'); if('{res}')m.setResolution(s,'{res}'); return{success:true,symbol:s.symbol(),interval:s.interval()}; })()"""
DISMISS_JS = """(() => { const ds=Array.from(document.querySelectorAll('[class*="dialog"], [class*="modal"], [class*="popup"], [role="dialog"]')); for(let d of ds){ if(d.querySelector('.monaco-editor')||(d.getAttribute('data-dialog-name')||'').includes('pine'))continue; const b=Array.from(d.querySelectorAll('button, [data-name="close"], [aria-label="Close"]')).find(b=>/close|ok|got it|dismiss|cancel/i.test(b.innerText||'')||b.getAttribute('data-name')==='close'||b.getAttribute('aria-label')==='Close'); if(b)b.click(); } })()"""
OPEN_PINE_JS = """(() => { const e=document.querySelector('.monaco-editor'); const vis=e&&e.offsetParent!==null; if(!vis){ const b=document.querySelector('[data-name="pine-dialog-button"]')||document.querySelector('button[aria-label="Pine"]')||Array.from(document.querySelectorAll('button, [role="tab"], [role="button"]')).find(b=>/pine editor/i.test((b.innerText||'').trim())||/^pine$/i.test((b.getAttribute('aria-label')||'').trim())); if(b){b.click();return'clicked_pine_btn';} return'no_pine_btn'; } return'already_visible'; })()"""
VISIBLE_JS = """(() => { const e=document.querySelector('.monaco-editor'); return e&&e.offsetParent!==null; })()"""
EXPOSE_JS = """(() => { if(!window._monaco){ try{ window.webpackChunktradingview.push([['mf_'+Date.now()],{},(require)=>{for(let id of Object.keys(require.m)){try{let m=require(id);if(m&&m.editor&&typeof m.editor.getModels==='function'){window._monaco=m;break}}catch(e){}}}]); }catch(e){} } const med=window._monaco?window._monaco.editor:null; const eds=med?med.getEditors():[]; const e=document.querySelector('.monaco-editor'); return {ready:!!(med&&eds.length>0&&e&&e.offsetParent!==null), nEditors:eds.length}; })()"""
PURGE_JS = """(() => { const c=window._exposed_chartWidgetCollection; const w=c&&c.activeChartWidget?c.activeChartWidget.value():null; const m=w&&w.hasModel()?w.model():null; if(!m)return{found:false}; const s=m.selection(); s.clear(); let a=[]; for(let p of m.panes())for(let d of p.dataSources()){const t=d.title?d.title():(d.name?d.name():''); if(/FINAL|Swing|strategy|DIAG_PROBE/i.test(t)){s.add(d);a.push(t);}} if(a.length){try{w.removeSelectedSources();return{found:true,removed:a};}catch(e){return{found:true,error:e.toString()};}} return{found:false}; })()"""
CLICK_ADD_JS = """(() => { const all=Array.from(document.querySelectorAll('button')); const a=document.querySelector('[title="Add to chart"]')||all.find(b=>/add to chart/i.test(b.innerText||'')||/add to chart/i.test(b.getAttribute('title')||'')); const u=document.querySelector('[title="Update on chart"]')||all.find(b=>/update on chart/i.test(b.innerText||'')||/update on chart/i.test(b.getAttribute('title')||'')); if(u&&!u.disabled){u.click();return'clicked_update';} if(a&&!a.disabled){a.click();return'clicked_add';} if(u){u.click();return'clicked_update_forced';} if(a){a.click();return'clicked_add_forced';} return'none:add='+!!a+',upd='+!!u; })()"""
ERRORS_JS = """(() => { if(!window._monaco||!window._monaco.editor)return[]; const ms=window._monaco.editor.getModelMarkers?window._monaco.editor.getModelMarkers({}):[]; return ms.filter(m=>m.severity===8).map(m=>({line:m.startLineNumber,col:m.startColumn,message:m.message})); })()"""
OPEN_TESTER_JS = """(() => { const b=Array.from(document.querySelectorAll('button, [role="button"], [role="tab"], [data-name]')).find(b=>/strategy tester/i.test((b.innerText||'').trim())||b.getAttribute('data-name')==='backtesting'); if(b)b.click(); return true; })()"""
BOTTOM_TEXT_JS = """(() => { const bottom=document.querySelector('.layout__area--bottom'); const report=document.querySelector('[class*="reportContainer-"]'); const c=window._exposed_chartWidgetCollection; const a=c&&c.activeChartWidget?c.activeChartWidget.value():null; const m=a&&a.hasModel()?a.model():null; return {symbol:m?m.mainSeries().symbol():'', interval:m?m.mainSeries().interval():'', text: bottom?bottom.innerText:(report?report.innerText:'')}; })()"""
TRADES_ENUM_JS = """(() => {
    const c=window._exposed_chartWidgetCollection; const w=c&&c.activeChartWidget?c.activeChartWidget.value():null; const m=w&&w.hasModel()?w.model():null;
    if(!m)return{error:'no model'};
    let strat=null, titles=[];
    for(let p of m.panes()){ for(let s of p.dataSources()){ let t=''; try{t=s.title?s.title():''}catch(e){} titles.push(t); let isSt=false; try{isSt=!!(s.isStrategy&&s.isStrategy());}catch(e){} if(isSt)strat=s; } }
    if(!strat){
        // fallback: match by title
        for(let p of m.panes()){ for(let s of p.dataSources()){ let t=''; try{t=s.title?s.title():''}catch(e){} if(/FINAL|BASELINE/i.test(t)) strat=s; } }
    }
    if(!strat)return{error:'no strategy', titles:titles};
    const names=new Set(); let pp=strat; while(pp&&pp!==Object.prototype){Object.getOwnPropertyNames(pp).forEach(n=>names.add(n)); pp=Object.getPrototypeOf(pp);}
    const found=[];
    for(const n of names){
        if(/^(constructor|__proto__)$/.test(n))continue;
        if(/set|remove|add|insert|update|clear|reset|destroy|create|delete|move|open|close|show|hide|subscribe|unsubscribe|apply|setSymbol|setResolution/i.test(n))continue;
        let f; try{f=strat[n];}catch(e){continue;}
        if(typeof f!=='function')continue;
        let v; try{v=strat[n]();}catch(e){continue;}
        if(v===undefined||v===null)continue;
        if(Array.isArray(v)&&v.length>0) found.push({method:n,isArray:true,len:v.length,sample:JSON.stringify(v[0]).slice(0,400)});
        else if(typeof v==='object') found.push({method:n,isObj:true,keys:Object.keys(v).slice(0,30)});
        else if(typeof v==='number'||typeof v==='string'||typeof v==='boolean') found.push({method:n,scalar:String(v).slice(0,60)});
    }
    return {title: strat.title?strat.title():'', found:found.slice(0,80), titles:titles};
})()"""
LEGEND_JS = """(() => { const out=[]; const walk=(el,d)=>{ if(!el||d>12)return; const t=(el.innerText||''); if(t.includes('DIAG_PROBE')&&t.length<500){out.push(t);return;} for(let c of el.children||[])walk(c,d+1); }; walk(document.querySelector('.layout__area--center')||document.body,0); return {blocks:Array.from(new Set(out)).slice(0,10)}; })()"""


def _num(s):
    if s is None:
        return None
    s = str(s).replace('+','').replace('\u2212','-').replace(',','').replace('USD','').replace('$','').replace('%','').replace('\u00a0','').strip()
    try:
        return float(s)
    except Exception:
        return None


def parse_full_text(text, symbol, interval):
    m = {'symbol': symbol, 'interval': interval, 'total_pnl_usd': None, 'gross_profit': None, 'gross_loss': None,
         'profit_factor': None, 'max_drawdown_pct': None, 'win_rate_pct': None, 'winning_trades': None,
         'total_closed_trades': None}
    if not text:
        m['status'] = 'no_report'
        return m
    g = lambda pat: (lambda mm: _num(mm.group(1)) if mm else None)(re.search(pat, text))
    m['gross_profit'] = abs(g(r'Gross profit\s*\n?\s*([+\-\u2212]?[\d,]+(?:\.\d+)?)')) if g(r'Gross profit\s*\n?\s*([+\-\u2212]?[\d,]+(?:\.\d+)?)') is not None else None
    m['gross_loss'] = abs(g(r'Gross loss\s*\n?\s*([+\-\u2212]?[\d,]+(?:\.\d+)?)')) if g(r'Gross loss\s*\n?\s*([+\-\u2212]?[\d,]+(?:\.\d+)?)') is not None else None
    m['profit_factor'] = g(r'Profit factor\s*\n?\s*([\d,.]+)')
    m['total_pnl_usd'] = g(r'Total PnL\s*\n?\s*([+\-\u2212]?[\d,]+(?:\.\d+)?)')
    wm = re.search(r'Profitable trades\s*\n?\s*([\d,.]+)\s*%\s*([\d]+)\s*\/\s*([\d]+)', text)
    if wm:
        m['win_rate_pct'] = _num(wm.group(1))
        m['winning_trades'] = int(wm.group(2))
        m['total_closed_trades'] = int(wm.group(3))
    ddm = re.search(r'Max drawdown\s*\n?\s*([\d,.]+(?:USD[\d,.]+)?)\s*%', text)
    if ddm:
        dd = re.findall(r'([\d,.]+)', ddm.group(1))
        m['max_drawdown_pct'] = _num(dd[-1]) if dd else None
    m['status'] = 'ok'
    gp, gl, pf = m['gross_profit'], m['gross_loss'], m['profit_factor']
    if gp and gl and pf:
        m['pf_crosscheck_ok'] = abs(round(gp/gl, 3) - pf) / pf < 0.03
    return m


def make_variants():
    for src, dst in ((IS_PINE, NOFED_IS_PINE), (OOS_PINE, NOFED_OOS_PINE)):
        code = open(src, encoding='utf-8').read()
        code2 = re.sub(r'useFedFundsFilter\s*=\s*input\.bool\(true', 'useFedFundsFilter = input.bool(false', code)
        if code2 == code:
            raise RuntimeError('useFedFundsFilter pattern not found')
        open(dst, 'w', encoding='utf-8').write(code2)
    open(REGIME_PROBE_PINE, 'w', encoding='utf-8').write(REGIME_PROBE_SRC)


async def settle(client, timeout_s=90):
    for _ in range(int(timeout_s * 2)):
        st = await client.eval_js(SETTLE_JS)
        if st and st.get('ready'):
            return st
        await asyncio.sleep(0.5)
    raise RuntimeError('page never settled')


async def switch_and_prep(client, symbol, interval):
    sw = await client.eval_js(SWITCH_JS.replace('{sym}', symbol).replace('{res}', interval))
    await asyncio.sleep(2.0)
    await client.eval_js(DISMISS_JS)
    for _ in range(5):
        p = await client.eval_js(PURGE_JS)
        if not p or not p.get('found'):
            break
        await asyncio.sleep(0.4)
    toggle = await client.eval_js(OPEN_PINE_JS)
    if toggle == 'clicked_pine_btn':
        for _ in range(20):
            await asyncio.sleep(0.5)
            if await client.eval_js(VISIBLE_JS):
                break
    for _ in range(20):
        st = await client.eval_js(EXPOSE_JS)
        if st and st.get('ready'):
            break
        await asyncio.sleep(0.5)
    errs = await client.eval_js(ERRORS_JS)
    if errs:
        raise RuntimeError('compile_error: %r' % (errs[:3],))
    return sw


async def inject_code(client, pine_path):
    code = open(pine_path, encoding='utf-8').read()
    code_json = json.dumps(code)
    inj = await client.eval_js("""(() => { if(!window._monaco)return{success:false,error:'Monaco not found'}; const eds=window._monaco.editor.getEditors(); const ed=eds&&eds.length?eds[0]:null; if(!ed)return{success:false,error:'No editor'}; const m=ed.getModel(); ed.executeEdits('d',[{range:m.getFullModelRange(),text:%s,forceMoveMarkers:true}]); ed.pushUndoStop(); ed.focus(); return{success:true}; })()""" % code_json)
    if not inj or not inj.get('success'):
        raise RuntimeError('Inject failed: %r' % (inj,))
    await asyncio.sleep(0.6)


async def ctrl_enter(client):
    """Pine Editor 'compile & add to chart' shortcut (Ctrl+Enter) — used when the
    Update-on-chart button is disabled (TV's change-detection misses programmatic
    executeEdits). Focus the monaco editor first, then dispatch Ctrl+Enter."""
    await client.eval_js("""(() => { try { const eds=window._monaco.editor.getEditors(); if(eds&&eds.length) eds[0].focus(); } catch(e){} })()""")
    await asyncio.sleep(0.3)
    for key, code, vk, mod in (
        ('keyDown', 'Enter', 13, 2), ('keyUp', 'Enter', 13, 2)):
        try:
            await client.send_cmd('Input.dispatchKeyEvent', {'type': key, 'key': 'Enter', 'code': 'Enter', 'windowsVirtualKeyCode': 13, 'modifiers': 2}, session_id=client.session_id)
        except Exception:
            pass
        await asyncio.sleep(0.2)


async def click_add(client):
    """Return click result; if the button path is dead (disabled), fall back to Ctrl+Enter."""
    r = await client.eval_js(CLICK_ADD_JS)
    if isinstance(r, str) and ('none' in r or 'forced' in r):
        await ctrl_enter(client)
        return 'ctrl_enter_after_' + r
    return r


async def wait_stable_n(client, expected_n, require_exact, timeout_s=60):
    """Poll bottom text until total_closed_trades stabilizes. Return (metrics, text)."""
    last_n = None
    stable = 0
    text = ''
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        await asyncio.sleep(2.0)
        snap = await client.eval_js(BOTTOM_TEXT_JS)
        text = snap.get('text', '') if isinstance(snap, dict) else ''
        m = parse_full_text(text, '', '')
        n = m.get('total_closed_trades')
        if n is not None and n == last_n:
            stable += 1
        else:
            stable = 0
            last_n = n
        if stable >= 2:
            if require_exact:
                if n == expected_n:
                    return m, text
                else:
                    stable = 0  # wrong N, keep waiting (report may still be updating)
            else:
                return m, text
    return None, text


async def phase_strategy(client, key, pine_path, symbol, interval, expected_n, want_trades):
    t0 = time.time()
    await switch_and_prep(client, symbol, interval)
    await inject_code(client, pine_path)
    click = await click_add(client)
    print('  [%s] click=%s' % (key, click))
    m, text = await wait_stable_n(client, expected_n, require_exact=(expected_n is not None), timeout_s=60)
    if m is None:
        print('  [%s] first pass unstable, retrying inject...' % key)
        await switch_and_prep(client, symbol, interval)
        await inject_code(client, pine_path)
        click2 = await click_add(client)
        print('  [%s] retry click=%s' % (key, click2))
        m, text = await wait_stable_n(client, expected_n, require_exact=(expected_n is not None), timeout_s=60)
    if m is None:
        return {'phase': key, 'status': 'unstable', 'symbol': symbol}
    m['phase'] = key
    m['symbol'] = symbol
    m['interval'] = interval
    m['elapsed_sec'] = round(time.time() - t0, 1)
    print('\n===== [%s] (%s %s) N=%s PF=%s =====' % (key, symbol, interval, m.get('total_closed_trades'), m.get('profit_factor')))
    print('--- PARSED ---')
    print(json.dumps({k: v for k, v in m.items()}, indent=2))
    if want_trades:
        tr = await client.eval_js(TRADES_ENUM_JS)
        m['trades_enum'] = tr if isinstance(tr, dict) else {}
        print('--- STRATEGY METHOD ENUM ---')
        print(json.dumps(tr, indent=2, default=str)[:8000])
    m['raw_report_text'] = text
    return m


async def phase_probe(client, key, symbol):
    t0 = time.time()
    await switch_and_prep(client, symbol, '1D')
    await inject_code(client, REGIME_PROBE_PINE)
    click = await click_add(client)
    print('  [%s] click=%s' % (key, click))
    blocks = []
    for _ in range(30):
        await asyncio.sleep(2.0)
        leg = await client.eval_js(LEGEND_JS)
        if isinstance(leg, dict):
            blocks = leg.get('blocks', [])
        if any('DIAG_PROBE' in b and re.search(r'\d', b) for b in blocks):
            break
    text_leg = '\n---\n'.join(blocks)
    def grab(label, s):
        mm = re.search(label + r'\s*\n?\s*(-?[\d]+\.?[\d]*)', s)
        return _num(mm.group(1)) if mm else None
    res = {'phase': key, 'symbol': symbol,
           'IS_RV': grab('IS_RV', text_leg), 'OOS_RV': grab('OOS_RV', text_leg),
           'IS_ABOVE_PCT': grab('IS_ABOVE_PCT', text_leg), 'OOS_ABOVE_PCT': grab('OOS_ABOVE_PCT', text_leg),
           'IS_N_x1000': grab('IS_NK', text_leg), 'OOS_N_x1000': grab('OOS_NK', text_leg),
           'elapsed_sec': round(time.time() - t0, 1), 'raw_blocks': blocks}
    print('\n===== [%s] PROBE LEGEND =====' % key)
    print(text_leg.strip()[:1200] if text_leg.strip() else '(no DIAG_PROBE block)')
    print(json.dumps({k: v for k, v in res.items() if k != 'raw_blocks'}, indent=2))
    return res


def print_final_tables(results):
    print('\n\n######################## FINAL DIAGNOSTIC TABLES ########################')
    assets = ['SPY', 'QQQ', 'BTCUSD']
    # C.1
    print('\n=== C.1 FED SHOCK GATE COUNTER ===')
    print('| Window | Asset | N fed=true | N fed=false | Entry events blocked by shock veto |')
    print('|---|---|---|---|---|')
    for win in ('IS', 'OOS'):
        for a in assets:
            b = results.get('%s_1D_%s_BASE' % (a, win), {})
            nf = results.get('%s_1D_%s_NOFED' % (a, win), {})
            n1 = b.get('total_closed_trades'); n2 = nf.get('total_closed_trades')
            delta = (n2 - n1) if (n1 is not None and n2 is not None) else None
            print('| %s | %s | %s | %s | %s |' % (win, a, n1, n2, delta))
    # B
    is_gp = sum(results.get('%s_1D_IS_BASE' % a, {}).get('gross_profit') or 0 for a in assets)
    is_gl = sum(results.get('%s_1D_IS_BASE' % a, {}).get('gross_loss') or 0 for a in assets)
    oos_gp = sum(results.get('%s_1D_OOS_BASE' % a, {}).get('gross_profit') or 0 for a in assets)
    oos_gl = sum(results.get('%s_1D_OOS_BASE' % a, {}).get('gross_loss') or 0 for a in assets)
    is_pf = round(is_gp / is_gl, 3) if is_gl else None
    oos_pf = round(oos_gp / oos_gl, 3) if oos_gl else None
    wn = wd = 0.0
    for a in assets:
        for r in (results.get('%s_1D_IS_BASE' % a, {}), results.get('%s_1D_OOS_BASE' % a, {})):
            if r.get('profit_factor') and r.get('total_closed_trades'):
                wn += r['profit_factor'] * r['total_closed_trades']; wd += r['total_closed_trades']
    w_pf = round(wn / wd, 3) if wd else None
    print('\n=== TASK B: TRUE POOLED PF (1D) ===')
    print('| Method | IS PF | OOS PF | Degradation % |')
    print('|---|---|---|---|')
    print('| Old trade-weighted avg PF (INVALID) | %s | %s | %s |' % (w_pf, None, None))
    deg = round((is_pf - oos_pf) / is_pf * 100, 2) if (is_pf and oos_pf) else None
    print('| TRUE pooled GP/GL | %s | %s | %s |' % (is_pf, oos_pf, deg))
    print('Inputs: IS GP=%.2f GL=%.2f | OOS GP=%.2f GL=%.2f' % (is_gp, is_gl, oos_gp, oos_gl))
    # C.3
    print('\n=== C.3 REGIME SHIFT MATRIX (1D bars) ===')
    print('| Asset | IS Avg ATR14/Close %% | OOS Avg ATR14/Close %% | IS %%Bars>W200EMA | OOS %%Bars>W200EMA | IS N | OOS N |')
    print('|---|---|---|---|---|---|---|')
    for a in assets:
        r = results.get('%s_REGIME' % a, {})
        print('| %s | %s | %s | %s | %s | %s | %s |' % (
            a, r.get('IS_RV'), r.get('OOS_RV'), r.get('IS_ABOVE_PCT'), r.get('OOS_ABOVE_PCT'),
            int(r['IS_N_x1000'] * 1000) if r.get('IS_N_x1000') else None,
            int(r['OOS_N_x1000'] * 1000) if r.get('OOS_N_x1000') else None))
    print('#########################################################################')


async def main():
    make_variants()
    print('[SETTLE] ...')
    client = runner.CDPClient(runner.get_ws_url())
    await client.connect()
    await client.find_tradingview_target()
    try:
        await client.send_cmd('Browser.grantPermissions', {'permissions': ['clipboardReadWrite', 'notifications'], 'origin': 'https://www.tradingview.com'})
    except Exception:
        pass
    st = await settle(client, 90)
    print('[SETTLE] ready %s' % json.dumps(st))
    await asyncio.sleep(5)

    results = {}
    phases = [
        ('SPY_1D_IS_BASE', IS_PINE, 'BATS:SPY', '1D', 33, True),
        ('QQQ_1D_IS_BASE', IS_PINE, 'BATS:QQQ', '1D', 31, True),
        ('BTCUSD_1D_IS_BASE', IS_PINE, 'BITSTAMP:BTCUSD', '1D', 38, True),
        ('SPY_1D_OOS_BASE', OOS_PINE, 'BATS:SPY', '1D', 7, True),
        ('QQQ_1D_OOS_BASE', OOS_PINE, 'BATS:QQQ', '1D', 7, True),
        ('BTCUSD_1D_OOS_BASE', OOS_PINE, 'BITSTAMP:BTCUSD', '1D', 6, True),
        ('SPY_1D_IS_NOFED', NOFED_IS_PINE, 'BATS:SPY', '1D', None, False),
        ('QQQ_1D_IS_NOFED', NOFED_IS_PINE, 'BATS:QQQ', '1D', None, False),
        ('BTCUSD_1D_IS_NOFED', NOFED_IS_PINE, 'BITSTAMP:BTCUSD', '1D', None, False),
        ('SPY_1D_OOS_NOFED', NOFED_OOS_PINE, 'BATS:SPY', '1D', None, False),
        ('QQQ_1D_OOS_NOFED', NOFED_OOS_PINE, 'BATS:QQQ', '1D', None, False),
        ('BTCUSD_1D_OOS_NOFED', NOFED_OOS_PINE, 'BITSTAMP:BTCUSD', '1D', None, False),
    ]
    for key, pine, symbol, interval, expected_n, want_trades in phases:
        try:
            print('\n>>>>>>>>>> PHASE %s <<<<<<<<<<' % key)
            results[key] = await phase_strategy(client, key, pine, symbol, interval, expected_n, want_trades)
        except Exception as e:
            results[key] = {'phase': key, 'status': 'failed', 'error': repr(e)}
            print('[FAIL] %s -> %r' % (key, e))
        with open(RESULTS_PATH, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, default=str)
        await asyncio.sleep(1.5)

    for key, symbol in (('SPY_REGIME', 'BATS:SPY'), ('QQQ_REGIME', 'BATS:QQQ'), ('BTCUSD_REGIME', 'BITSTAMP:BTCUSD')):
        try:
            print('\n>>>>>>>>>> PHASE %s <<<<<<<<<<' % key)
            results[key] = await phase_probe(client, key, symbol)
        except Exception as e:
            results[key] = {'phase': key, 'status': 'failed', 'error': repr(e)}
            print('[FAIL] %s -> %r' % (key, e))
        with open(RESULTS_PATH, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, default=str)
        await asyncio.sleep(1.5)

    print_final_tables(results)
    with open(RESULTS_PATH, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, default=str)
    print('\n[DONE] %s' % RESULTS_PATH)
    await client.close()


if __name__ == '__main__':
    asyncio.run(main())
