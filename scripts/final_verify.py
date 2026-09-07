import asyncio, json, sys, os, base64, pathlib
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import runner
sys.stdout.reconfigure(encoding='utf-8')
ROOT = pathlib.Path(__file__).resolve().parent.parent
async def main():
    ws_url = runner.get_ws_url()
    client = runner.CDPClient(ws_url)
    await client.connect()
    await client.find_tradingview_target()
    # Ensure SPY
    await client.eval_js("""(() => {
        const coll = window._exposed_chartWidgetCollection;
        coll.setSymbol('BATS:SPY');
        coll.setResolution('1D');
        return 'set';
    })()""")
    await asyncio.sleep(4)
    # Verify sources
    sources = await client.eval_js("""(() => {
        const coll = window._exposed_chartWidgetCollection;
        const model = coll.activeChartWidget.value().model();
        let out=[];
        for(let p of model.panes()) for(let s of p.dataSources()) out.push(s.title?s.title():'');
        return out;
    })()""")
    print("Sources:", json.dumps(sources, indent=2, ensure_ascii=False))
    custom = [s for s in sources if 'FINAL' in s or 'BASELINE' in s]
    print("Custom count:", len(custom), custom)
    # Metrics
    report = await client.eval_js("""(() => {
        const rep = document.querySelector('[class*="reportContainer"]') || document.querySelector('.layout__area--bottom');
        return rep ? rep.innerText.slice(0,2500) : 'no report';
    })()""")
    print(report[:1500])
    # Screenshot
    try:
        res = await client.send_cmd("Page.captureScreenshot", {"format":"png","captureBeyondViewport":False}, session_id=client.session_id)
        data = res.get('data','')
        if data:
            out = ROOT / "metrics" / "clean_chart_screenshot.png"
            out.write_bytes(base64.b64decode(data))
            print(f"Screenshot saved to {out}")
    except Exception as e:
        print(f"Screenshot fail {e}")
    await client.close()
asyncio.run(main())
