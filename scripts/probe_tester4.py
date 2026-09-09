"""Probe 4: dump bottom backtesting panel tab strip + clickable children."""
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
        const panel = document.querySelector('.bottom-widgetbar-content.backtesting');
        if (!panel) return {err: 'no panel'};
        const bar = panel.parentElement;
        out.panelParentText = (bar.innerText||'').slice(0, 400);
        // sibling tab buttons (Overview / ... ) usually sit above the panel
        const btns = Array.from(bar.querySelectorAll('button, [role="tab"]'))
            .map(b => ((b.innerText||'').trim().slice(0,30) || b.getAttribute('data-name') || b.getAttribute('aria-label')||'').slice(0,40));
        out.btns = btns.slice(0, 30);
        // whole bottom widgetbar
        const wb = document.querySelector('[class*="widgetbar"]');
        out.wbText = wb ? (wb.innerText||'').slice(0, 800) : 'NONE';
        return out;
    })()""")
    import json
    print(json.dumps(info, indent=1)[:4000])
    await client.close()


asyncio.run(main())
