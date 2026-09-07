import sys, os, asyncio, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import runner

async def main():
    ws_url = runner.get_ws_url()
    client = runner.CDPClient(ws_url)
    await client.connect()
    await client.find_tradingview_target()
    
    js_code = """
    (() => {
        // 1. Close any modal dialogs
        const closeBtns = Array.from(document.querySelectorAll('[data-name="close"], button, [aria-label="Close"]'))
            .filter(b => (b.innerText || '').trim().toLowerCase() === 'close' || b.getAttribute('aria-label') === 'Close' || b.getAttribute('data-name') === 'close');
        closeBtns.forEach(b => b.click());

        // 2. Remove duplicate studies/strategies
        const coll = window._exposed_chartWidgetCollection;
        if (!coll || !coll.activeChartWidget) return { removed: [], error: 'no chart' };
        const model = coll.activeChartWidget.value().model();
        const allPanes = model.panes();
        let removed = [];
        let kept = 0;
        for (let p of allPanes) {
            for (let s of p.dataSources()) {
                const title = s.title ? s.title() : '';
                if (/quant|strategy/i.test(title) || (s.isStrategy && s.isStrategy())) {
                    if (kept >= 1) {
                        model.removeSource(s);
                        removed.push(title);
                    } else {
                        kept += 1;
                    }
                }
            }
        }
        return { kept, removed };
    })()
    """
    res = await client.eval_js(js_code)
    print("Clean result:", json.dumps(res, indent=2))
    await client.close()

if __name__ == "__main__":
    asyncio.run(main())
