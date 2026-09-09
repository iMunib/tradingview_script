"""Probe 2: big table content + tester tab labels."""
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
        const tables = Array.from(document.querySelectorAll('table'));
        let big = null, bigN = 0;
        for (const tb of tables) {
            const n = tb.querySelectorAll('tr').length;
            if (n > bigN) { bigN = n; big = tb; }
        }
        out.bigRows = bigN;
        if (big) {
            const rows = Array.from(big.querySelectorAll('tr')).slice(0, 6);
            out.head = rows.map(tr => Array.from(tr.querySelectorAll('th,td'))
                .map(c => (c.innerText||'').slice(0,28)).join(' | '));
        }
        // find tester tab strip: elements whose text is exactly Overview / List of Trades etc.
        const hits = [];
        const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_ELEMENT);
        let el;
        while (el = walker.nextNode()) {
            const t = (el.innerText||'').trim();
            if (['Overview','Performance Summary','List of Trades','Orders'].includes(t) && el.children.length <= 1) {
                hits.push({tag: el.tagName, cls: (el.className||'').toString().slice(0,60),
                           id: el.id||'', dn: el.getAttribute('data-name')||''});
                if (hits.length > 12) break;
            }
        }
        out.tabHits = hits;
        return out;
    })()""")
    import json
    print(json.dumps(info, indent=1)[:4000])
    await client.close()


asyncio.run(main())
