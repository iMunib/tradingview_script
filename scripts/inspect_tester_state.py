import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import asyncio
import json
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
        let studyErrors = [];
        if (model) {
            for (let p of model.panes()) {
                for (let s of p.dataSources()) {
                    try {
                        const title = s.title ? s.title() : '';
                        const err = s.error ? s.error() : null;
                        const status = s.status ? s.status() : null;
                        const hasErrors = s.hasErrors ? s.hasErrors() : null;
                        const metaInfo = s.metaInfo ? s.metaInfo() : null;
                        studyErrors.push({
                            title,
                            err,
                            status,
                            hasErrors,
                            description: metaInfo ? metaInfo.description : null
                        });
                    } catch(e) {
                        studyErrors.push({ err_ex: e.toString() });
                    }
                }
            }
        }
        
        // Also look for error icons and tooltips in DOM
        const errorElements = Array.from(document.querySelectorAll('[data-name*="error"], [class*="error-"], [class*="alert-"]'))
            .map(el => ({
                tag: el.tagName,
                dataName: el.getAttribute('data-name'),
                className: el.className,
                text: el.innerText,
                title: el.getAttribute('title') || el.getAttribute('aria-label')
            }));

        return { studyErrors, errorElements };
    })()"""

    res = await client.eval_js(js)
    print(json.dumps(res, indent=2))
    await client.close()

if __name__ == '__main__':
    asyncio.run(main())
