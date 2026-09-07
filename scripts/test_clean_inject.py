import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import asyncio
import json
import websockets
import runner

sys.stdout.reconfigure(encoding='utf-8')

async def test_clean_inject(pine_file="FINAL_OPTIMIZED_STRATEGY.pine", symbol="BATS:SPY", interval="1D"):
    pine_path = os.path.join(runner.ROOT_DIR, pine_file)
    with open(pine_path, 'r', encoding='utf-8') as f:
        pine_code = f.read()

    ws_url = runner.get_ws_url()
    client = runner.CDPClient(ws_url)
    await client.connect()
    await client.find_tradingview_target()
    print("Connected to TV target:", client.target_id)

    # 1. Switch symbol & interval
    switch_js = f"""(() => {{
        const coll = window._exposed_chartWidgetCollection;
        if (!coll) return 'no coll';
        if ('{symbol}') coll.setSymbol('{symbol}');
        if ('{interval}') coll.setResolution('{interval}');
        const active = coll.activeChartWidget ? coll.activeChartWidget.value() : null;
        return {{
            symbol: active ? active.model().mainSeries().symbol() : null,
            interval: active ? active.model().mainSeries().interval() : null
        }};
    }})()"""
    sym_res = await client.eval_js(switch_js)
    print("Symbol switch result:", sym_res)
    await asyncio.sleep(2)

    # 2. Dismiss any open modals/dialogs
    dismiss_js = """(() => {
        const closeBtns = Array.from(document.querySelectorAll('[data-name="close"], button')).filter(b => (b.innerText || '').trim().toLowerCase() === 'close');
        closeBtns.forEach(b => b.click());
        return closeBtns.length;
    })()"""
    d_res = await client.eval_js(dismiss_js)
    print("Dismissed dialogs:", d_res)

    # 3. Remove existing strategies
    clean_js = """(() => {
        const coll = window._exposed_chartWidgetCollection;
        const model = coll && coll.activeChartWidget ? coll.activeChartWidget.value().model() : null;
        let removed = [];
        if (model) {
            for (let p of model.panes()) {
                for (let s of p.dataSources()) {
                    const title = s.title ? s.title() : '';
                    if ((s.isStrategy && s.isStrategy()) || /strategy|quant/i.test(title)) {
                        model.removeSource(s);
                        removed.push(title);
                    }
                }
            }
        }
        return removed;
    })()"""
    rem_res = await client.eval_js(clean_js)
    print("Removed existing strategy sources:", rem_res)
    await asyncio.sleep(1)

    # 4. Open Pine Editor if needed
    open_pine_js = """(() => {
        const hasEditor = !!document.querySelector('.monaco-editor');
        if (!hasEditor) {
            const pineBtn = document.querySelector('[data-name="pine-dialog-button"]') ||
                            document.querySelector('button[aria-label="Pine"]');
            if (pineBtn) pineBtn.click();
        }
        return !!document.querySelector('.monaco-editor');
    })()"""
    await client.eval_js(open_pine_js)
    await asyncio.sleep(1)

    # 5. Inject code into Monaco
    code_json = json.dumps(pine_code)
    inject_js = f"""(() => {{
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
        editor.executeEdits('clean_inject', [{{
            range: targetModel.getFullModelRange(),
            text: {code_json},
            forceMoveMarkers: true
        }}]);
        editor.pushUndoStop();
        editor.focus();

        return {{ success: true, lineCount: targetModel.getLineCount() }};
    }})()"""
    inj_res = await client.eval_js(inject_js)
    print("Injected into Monaco:", inj_res)

    # 6. Click 'Add to chart'
    click_js = """(() => {
        const btn = document.querySelector('[title="Add to chart"]') || 
                    document.querySelector('[title="Update on chart"]') ||
                    Array.from(document.querySelectorAll('button')).find(b => /add to chart/i.test(b.innerText || ''));
        if (btn) {
            btn.click();
            return { clicked: true, title: btn.getAttribute('title') || btn.innerText };
        }
        return { clicked: false };
    })()"""
    click_res = await client.eval_js(click_js)
    print("Clicked button:", click_res)

    # 7. Also dispatch Ctrl+Enter just in case
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

    print("Waiting 6 seconds for compilation...")
    await asyncio.sleep(6)

    # 8. Check errors
    check_errors_js = """(() => {
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
    })()"""
    errors = await client.eval_js(check_errors_js)
    print("Monaco errors:", errors)

    # 9. Check Strategy Tester
    open_tester_js = """(() => {
        const testerBtn = Array.from(document.querySelectorAll('button, [role="button"], [data-name]'))
            .find(b => /strategy tester/i.test(b.innerText || '') || /strategy tester/i.test(b.getAttribute('aria-label') || '') || b.getAttribute('data-name') === 'backtesting');
        if (testerBtn && !document.querySelector('[class*="reportContainer-"]')) {
            testerBtn.click();
        }
        return !!document.querySelector('[class*="reportContainer-"]');
    })()"""
    await client.eval_js(open_tester_js)

    scrape_js = """(() => {
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
    })()"""

    for _ in range(10):
        await asyncio.sleep(1)
        rdata = await client.eval_js(scrape_js)
        raw = rdata.get('rawText', '')
        if 'Total PnL' in raw:
            print("Found Strategy Tester report text snippet:")
            print(raw[:500])
            break

    await client.close()

if __name__ == '__main__':
    asyncio.run(test_clean_inject())
