"""Diag2: verify editor content after inject."""
import asyncio
import os
import sys
import json as _json

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)
import runner
from scripts.export_trade_logs import build_emitter, VARIANTS


async def main():
    client = runner.CDPClient(runner.get_ws_url())
    await client.connect()
    await client.find_tradingview_target()
    epath = build_emitter(VARIANTS["OOS"], "DIAG2")
    code = open(epath, encoding="utf-8").read()
    print("source len:", len(code), "has xCode:", ("xCode" in code), flush=True)
    info = await client.eval_js("""(() => {
        const out = {};
        try {
            out.hasMonaco = !!window._monaco;
            const eds = window._monaco ? window._monaco.editor.getEditors() : [];
            out.nEditors = eds.length;
            out.models = window._monaco.editor.getModels().map(m => ({
                uri: m.uri.toString().slice(-60), len: m.getValueLength()}));
        } catch(e) { out.err = String(e).slice(0,200); }
        return out;
    })()""")
    print(_json.dumps(info, indent=1)[:1500], flush=True)
    await client.close()


asyncio.run(main())
