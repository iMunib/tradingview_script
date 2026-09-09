"""Verify visuals v2: strict numeric-nonzero counts per plot index 0..8."""
import asyncio
import os
import sys
from collections import Counter

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)
import runner


async def main():
    client = runner.CDPClient(runner.get_ws_url())
    await client.connect()
    await client.find_tradingview_target()
    data = await client.eval_js("""(() => {
        const out = {counts: {}, nplots: 0, nbars: 0, maxlen: 0};
        try {
            const coll = window._exposed_chartWidgetCollection;
            const model = coll.activeChartWidget.value().model();
            let study = null, best = -1;
            for (const p of model.panes()) for (const s of p.dataSources()) {
                let t = '';
                try { t = s.title ? s.title() : ''; } catch(e) {}
                if (String(t).includes('FINAL_UCSv3')) {
                    let n = 0;
                    try { n = s.metaInfo().plots.length; } catch(e) {}
                    if (n > best) { best = n; study = s; }
                }
            }
            out.nplots = best;
            study._data.each((i, v) => {
                if (!v || typeof v === 'number') return;
                out.nbars += 1;
                if (v.length > out.maxlen) out.maxlen = v.length;
                for (let k = 1; k <= 9; k++) {
                    const val = v[k];
                    if (typeof val === 'number' && val !== 0) {
                        const kk = 'p' + (k - 1);
                        out.counts[kk] = (out.counts[kk] || 0) + 1;
                    }
                }
            });
        } catch(e) { out.err = String(e).slice(0,200); }
        return out;
    })()""")
    import json
    print(json.dumps(data), flush=True)
    with open(os.path.join(ROOT_DIR, "metrics", "trade_log_SPY_1D_Full.csv"), encoding="utf-8") as f:
        import csv
        rows = list(csv.DictReader(f))
    print("csv N:", len(rows), "reasons:", dict(Counter(r["exit_reason"] for r in rows)), flush=True)
    await client.close()


asyncio.run(main())
