import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import asyncio
import json
import websockets
import runner

sys.stdout.reconfigure(encoding='utf-8')

async def main():
    ws_url = runner.get_ws_url()
    client = runner.CDPClient(ws_url)
    await client.connect()
    await client.find_tradingview_target()
    
    js = """(() => {
        const coll = window._exposed_chartWidgetCollection;
        const model = coll && coll.activeChartWidget ? coll.activeChartWidget.value().model() : null;
        const sources = [];
        if (model) {
            for (let p of model.panes()) {
                for (let s of p.dataSources()) {
                    sources.push({
                        title: s.title ? s.title() : '',
                        isStrategy: s.isStrategy ? s.isStrategy() : false
                    });
                }
            }
        }
        const updateBtn = document.querySelector('[title="Update on chart"]');
        const addBtn = document.querySelector('[title="Add to chart"]');
        const saveBtn = document.querySelector('[title="Save"]');
        
        let editorTitle = '';
        if (window._monaco && window._monaco.editor) {
            const models = window._monaco.editor.getModels();
            if (models.length) {
                editorTitle = models[0].getValue().slice(0, 100);
            }
        }
        
        return {
            sources,
            hasUpdateBtn: !!updateBtn,
            hasAddBtn: !!addBtn,
            hasSaveBtn: !!saveBtn,
            editorFirst100: editorTitle
        };
    })()"""
    
    res = await client.eval_js(js)
    print(json.dumps(res, indent=2))
    await client.close()

if __name__ == '__main__':
    asyncio.run(main())
