import os
import sys
import asyncio
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT_DIR)
import runner

async def main():
    ws_url = runner.get_ws_url()
    client = runner.CDPClient(ws_url)
    await client.connect()
    await client.find_tradingview_target()
    res = await client.eval_js("""(() => {
        const coll = window._exposed_chartWidgetCollection;
        const model = coll.activeChartWidget.value().model();
        let toRemove = [];
        for (let p of model.panes()) {
            for (let s of p.dataSources()) {
                const title = s.title ? s.title() : '';
                if (/quant|strategy|qs_|swing/i.test(title)) {
                    toRemove.push(s);
                }
            }
        }
        toRemove.forEach(s => {
            try { model.removeSource(s); } catch(e) {}
        });
        const closeBtns = Array.from(document.querySelectorAll('[data-name="close"], button')).filter(b => (b.innerText || '').trim().toLowerCase() === 'close');
        closeBtns.forEach(b => b.click());
        return { removed: toRemove.map(s => s.title ? s.title() : 'unknown') };
    })()""")
    print("Clean result:", res)
    await client.close()

if __name__ == '__main__':
    asyncio.run(main())
