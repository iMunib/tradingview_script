import asyncio, json, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import runner
sys.stdout.reconfigure(encoding='utf-8')
async def main():
    ws_url = runner.get_ws_url()
    client = runner.CDPClient(ws_url)
    await client.connect()
    await client.find_tradingview_target()
    js = """(() => {
        if (!window._monaco) return {err:'no monaco'};
        const models = window._monaco.editor.getModels();
        return {
            count: models.length,
            uris: models.map(m=>m.uri.toString()),
            valuesSnippet: models.map(m=>m.getValue().slice(0,200).replace(/\\n/g,' | ')),
            editors: window._monaco.editor.getEditors().length,
            editorModelUri: window._monaco.editor.getEditors()[0] ? window._monaco.editor.getEditors()[0].getModel().uri.toString() : null
        };
    })()"""
    res = await client.eval_js(js)
    print(json.dumps(res, indent=2, ensure_ascii=False))
    await client.close()
asyncio.run(main())
