"""Diag3: find Add/Update buttons, click, verify study plot count changes."""
import asyncio
import os
import sys
import json as _json

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)
import runner


async def main():
    client = runner.CDPClient(runner.get_ws_url())
    await client.connect()
    await client.find_tradingview_target()
    info = await client.eval_js("""(() => {
        const out = {btns: []};
        for (const b of document.querySelectorAll('button')) {
            const t = (b.innerText||'').trim();
            if (/add to chart|update on chart/i.test(t) || /add to chart|update on chart/i.test(b.getAttribute('title')||'')) {
                out.btns.push({text: t.slice(0,30), title: b.getAttribute('title')||'',
                    disabled: !!b.disabled, visible: b.offsetParent !== null,
                    cls: (b.className||'').toString().slice(0,60)});
            }
        }
        return out;
    })()""")
    print(_json.dumps(info, indent=1)[:2000], flush=True)
    # click first visible enabled add/update
    clk = await client.eval_js("""(() => {
        for (const b of document.querySelectorAll('button')) {
            const t = (b.innerText||'').trim();
            if ((/add to chart/i.test(t) || /update on chart/i.test(t)) && !b.disabled && b.offsetParent !== null) {
                b.click(); return 'clicked:' + t.slice(0,30);
            }
        }
        return 'none-clicked';
    })()""")
    print("CLICK:", clk, flush=True)
    await asyncio.sleep(10)
    chk = await client.eval_js("""(() => {
        const out = {studies: []};
        const coll = window._exposed_chartWidgetCollection;
        const model = coll.activeChartWidget.value().model();
        for (const p of model.panes()) for (const s of p.dataSources()) {
            let t = '';
            try { t = s.title ? s.title() : ''; } catch(e) {}
            if (String(t).includes('FINAL')) {
                let n = 0;
                try { n = s.metaInfo().plots.length; } catch(e) {}
                out.studies.push({title: String(t).slice(0,40), nplots: n});
            }
        }
        const r = document.querySelector('[class*="reportContainer-"]');
        out.reportHead = r ? r.innerText.slice(0, 200) : 'NOREPORT';
        return out;
    })()""")
    print(_json.dumps(chk, indent=1)[:1500], flush=True)
    await client.close()


asyncio.run(main())
