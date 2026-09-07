import asyncio, json, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import runner
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
async def main():
    ws_url = runner.get_ws_url()
    client = runner.CDPClient(ws_url)
    await client.connect()
    await client.find_tradingview_target()
    # Check current state
    with open(os.path.join(ROOT, "FINAL_OPTIMIZED_STRATEGY.pine"),'r',encoding='utf-8') as f:
        final_code = f.read()
    code_json = json.dumps(final_code)
    js = f"""(async () => {{
        if (!window._monaco) return {{err:'no monaco'}};
        const monaco = window._monaco;
        const editor = monaco.editor.getEditors()[0];
        if (!editor) return {{err:'no editor'}};
        // Create new model for FINAL
        const uri = monaco.Uri.parse('inmemory://model/final_' + Date.now() + '.pine');
        const model = monaco.editor.createModel({code_json}, 'pine', uri);
        editor.setModel(model);
        editor.focus();
        await new Promise(r=>setTimeout(r,600));
        const hasAdd = !!document.querySelector('[title="Add to chart"]');
        const hasUpdate = !!document.querySelector('[title="Update on chart"]');
        const titleBtn = document.querySelector('[data-qa-id="pine-script-title-button"]');
        const titleText = titleBtn ? titleBtn.innerText.slice(0,120) : 'no title';
        return {{hasAdd, hasUpdate, titleText, modelUri: model.uri.toString(), modelCount: monaco.editor.getModels().length}};
    }})()"""
    res = await client.eval_js(js)
    print(json.dumps(res, indent=2, ensure_ascii=False))
    await asyncio.sleep(2)
    # Now try clicking Add
    js2 = """(() => {
        const addBtn = document.querySelector('[title="Add to chart"]');
        const updBtn = document.querySelector('[title="Update on chart"]');
        if (addBtn && !addBtn.disabled) { addBtn.click(); return 'clicked_add'; }
        if (updBtn && !updBtn.disabled) { updBtn.click(); return 'clicked_update'; }
        return 'none';
    })()"""
    res2 = await client.eval_js(js2)
    print("click result:", res2)
    await asyncio.sleep(4)
    # Check chart sources
    js3 = """(() => {
        const coll = window._exposed_chartWidgetCollection;
        const model = coll.activeChartWidget.value().model();
        let sources=[];
        for (let p of model.panes()) for (let s of p.dataSources()) sources.push(s.title?s.title():'');
        return sources;
    })()"""
    res3 = await client.eval_js(js3)
    print("sources after new model Add:", json.dumps(res3, indent=2, ensure_ascii=False))
    await client.close()
asyncio.run(main())
