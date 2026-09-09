import asyncio
import os
import sys
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)
import runner

async def main():
    ws_url = runner.get_ws_url()
    client = runner.CDPClient(ws_url)
    await client.connect()
    await client.find_tradingview_target()
    
    js = """(() => {
        const coll = window._exposed_chartWidgetCollection;
        const widget = coll && coll.activeChartWidget ? coll.activeChartWidget.value() : null;
        const model = widget && widget.hasModel() ? widget.model() : null;
        if (!model) return { error: 'no model' };
        
        const series = model.mainSeries();
        const bars = series.bars();
        const n = bars.size();
        
        const start2025 = 1735689600; // Jan 1 2025 in seconds
        const bars2025 = [];
        for (let i = 0; i < n; i++) {
            const b = bars.valueAt(i);
            if (b && b[0] >= start2025) {
                bars2025.push({
                    idx: i,
                    date: new Date(b[0] * 1000).toISOString().slice(0, 10),
                    o: b[1], h: b[2], l: b[3], c: b[4], v: b[5]
                });
            }
        }
        return { count: bars2025.length, bars: bars2025 };
    })()"""
    
    res = await client.eval_js(js)
    print(f"Total weekly bars in 2025-2026: {res.get('count')}")
    for b in res.get('bars', []):
        print(f"{b['date']}: O={b['o']} H={b['h']} L={b['l']} C={b['c']}")
    await client.close()

if __name__ == "__main__":
    asyncio.run(main())
