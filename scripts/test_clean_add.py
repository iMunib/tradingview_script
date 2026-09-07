import os
import sys
import asyncio
import json
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT_DIR)
import runner

async def main():
    ws_url = runner.get_ws_url()
    client = runner.CDPClient(ws_url)
    await client.connect()
    await client.find_tradingview_target()

    # Step 1: Remove any strategies from chart
    res_clean = await client.eval_js("""(() => {
        const coll = window._exposed_chartWidgetCollection;
        const model = coll.activeChartWidget.value().model();
        let toRemove = [];
        for (let p of model.panes()) {
            for (let s of p.dataSources()) {
                const title = s.title ? s.title() : '';
                if (/quant|strategy|oos|is/i.test(title)) {
                    toRemove.push(s);
                }
            }
        }
        toRemove.forEach(s => {
            try { model.removeSource(s); } catch(e) {}
        });
        const closeBtns = Array.from(document.querySelectorAll('[data-name="close"], button')).filter(b => (b.innerText || '').trim().toLowerCase() === 'close');
        closeBtns.forEach(b => b.click());
        return { removed: toRemove.length };
    })()""")
    print("Cleaned:", res_clean)
    await asyncio.sleep(1.0)

    # Step 2: Click 'Add to chart'
    res_add = await client.eval_js("""(() => {
        const addBtn = document.querySelector('[title="Add to chart"]') ||
                       Array.from(document.querySelectorAll('button')).find(b => /add to chart/i.test(b.innerText || '') || /add to chart/i.test(b.getAttribute('title') || ''));
        if (addBtn) {
            addBtn.click();
            return 'clicked add';
        }
        return 'no add btn';
    })()""")
    print("Add button:", res_add)

    # Step 3: Wait 8 seconds
    print("Waiting 8 seconds for calculation...")
    await asyncio.sleep(8.0)

    # Step 4: Scrape report
    report_data = await client.eval_js("""(() => {
        const report = document.querySelector('[class*="reportContainer-"]') ||
                       document.querySelector('[class*="wrapper-dmId9qUc"]');
        return report ? report.innerText : 'No report';
    })()""")
    print("REPORT TEXT:\n", report_data)
    await client.close()

if __name__ == '__main__':
    asyncio.run(main())
