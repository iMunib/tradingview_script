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
        const coll = window._exposed_chartWidgetCollection;
        if (coll) {
            coll.setSymbol('BATS:SPY');
            coll.setResolution('1D');
        }
        const active = coll.activeChartWidget.value();
        return {sym: active.model().mainSeries().symbol(), interval: active.model().mainSeries().interval()};
    })()"""
    res = await client.eval_js(js)
    print(res)
    await asyncio.sleep(4)
    js2 = """(() => {
        const rep = document.querySelector('[class*="reportContainer"]') || document.querySelector('.layout__area--bottom');
        return rep ? rep.innerText.slice(0,3000) : 'no report';
    })()"""
    res2 = await client.eval_js(js2)
    print(res2[:2500])
    await client.close()
asyncio.run(main())
