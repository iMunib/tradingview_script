"""Probe 3: substring search for tester tabs + panel structure."""
import asyncio
import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)
import runner


async def main():
    client = runner.CDPClient(runner.get_ws_url())
    await client.connect()
    await client.find_tradingview_target()
    info = await client.eval_js("""(() => {
        const out = {};
        const needles = ['List of Trades', 'Performance Summary', 'Strategy Tester', 'Total PnL', 'Profit factor'];
        out.found = {};
        for (const n of needles) {
            const els = Array.from(document.querySelectorAll('*')).filter(e =>
                e.children.length === 0 && (e.textContent||'').trim() === n);
            out.found[n] = els.slice(0,4).map(e => ({tag: e.tagName,
                cls: (e.className||'').toString().slice(0,80),
                parent: e.parentElement ? e.parentElement.tagName + '.' +
                    (e.parentElement.className||'').toString().slice(0,60) : ''}));
        }
        // tester bottom panel: look for known class fragments
        out.panelHtml = '';
        const cand = document.querySelector('[class*="backtesting"], [class*="strategy-tester"], [class*="tester"]');
        out.panelCls = cand ? cand.className.toString().slice(0,120) : 'NONE';
        return out;
    })()""")
    import json
    print(json.dumps(info, indent=1)[:5000])
    await client.close()


asyncio.run(main())
