"""Probe Strategy Tester DOM: export buttons, tabs, trades-list structure."""
import asyncio
import json
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
        const btns = Array.from(document.querySelectorAll('button'));
        out.allButtons = btns.map(b => ({
            t: (b.innerText||'').slice(0,40), dn: b.getAttribute('data-name'),
            title: b.getAttribute('title'), aria: b.getAttribute('aria-label')
        })).filter(b => b.t || b.dn || b.title || b.aria).slice(0, 120);
        const tabs = Array.from(document.querySelectorAll('[role="tab"], [data-name*="tab"]'));
        out.tabs = tabs.map(t => (t.innerText||'').slice(0,40)).filter(Boolean).slice(0,20);
        // strategy tester deep tables
        const tables = Array.from(document.querySelectorAll('table'));
        out.tables = tables.map(tb => {
            const hdrs = Array.from(tb.querySelectorAll('th')).map(h => (h.innerText||'').slice(0,24));
            return {headers: hdrs, rows: tb.querySelectorAll('tr').length};
        }).slice(0, 10);
        return out;
    })()""")
    print("TABS:" + json.dumps(info.get('tabs', []))[:2000])
    print("TABLES:" + json.dumps(info.get('tables', []))[:3000])
    hits = [b for b in info.get('allButtons', [])
            if any(k in json.dumps(b).lower() for k in
                   ['export', 'download', 'csv', 'trade', 'list', 'performance', 'overview'])]
    print("BTNHITS:" + json.dumps(hits)[:3000])
    print("NBTN:" + str(len(info.get('allButtons', []))))
    await client.close()


asyncio.run(main())
