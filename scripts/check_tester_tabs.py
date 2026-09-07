import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import asyncio
import json
import runner

sys.stdout.reconfigure(encoding='utf-8')

async def main():
    ws_url = runner.get_ws_url()
    client = runner.CDPClient(ws_url)
    await client.connect()
    await client.find_tradingview_target()

    js = """(() => {
        const tabs = Array.from(document.querySelectorAll('[role="tab"], button, [data-name]'))
            .filter(el => /overview|performance|trades|analysis|benchmarking|list of trades/i.test((el.innerText || '').trim()))
            .map(el => ({ text: el.innerText.trim(), role: el.getAttribute('role'), dataName: el.getAttribute('data-name') }));
        return tabs;
    })()"""

    res = await client.eval_js(js)
    print(json.dumps(res, indent=2))
    await client.close()

if __name__ == '__main__':
    asyncio.run(main())
