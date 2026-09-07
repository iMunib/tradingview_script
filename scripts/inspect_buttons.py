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
    res = await client.eval_js("""(() => {
        const updateBtn = document.querySelector('[title="Update on chart"]');
        const addBtn = document.querySelector('[title="Add to chart"]');
        const allBtns = Array.from(document.querySelectorAll('button')).filter(b => 
            /chart/i.test(b.innerText || '') || /chart/i.test(b.getAttribute('title') || '')
        );
        return {
            hasUpdate: !!updateBtn,
            updateDisabled: updateBtn ? updateBtn.disabled : null,
            hasAdd: !!addBtn,
            addDisabled: addBtn ? addBtn.disabled : null,
            allChartBtns: allBtns.map(b => ({
                text: b.innerText,
                title: b.getAttribute('title'),
                disabled: b.disabled,
                className: b.className
            }))
        };
    })()""")
    print("Button inspection:", json.dumps(res, indent=2))
    await client.close()

if __name__ == '__main__':
    asyncio.run(main())
