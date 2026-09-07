import asyncio
import json
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import runner

async def check():
    ws_url = runner.get_ws_url()
    client = runner.CDPClient(ws_url)
    await client.connect()
    await client.find_tradingview_target()
    js = """(() => {
        const bottomTabs = Array.from(document.querySelectorAll('[class*="tab-"], button, [role="tab"], [data-name]'))
            .map(b => ({
                text: (b.innerText || '').trim(),
                ariaLabel: b.getAttribute('aria-label') || '',
                dataName: b.getAttribute('data-name') || '',
                role: b.getAttribute('role') || ''
            }))
            .filter(b => /strategy|tester|pine|editor|backtest/i.test(b.text + b.ariaLabel + b.dataName));
        const report = document.querySelector('[class*="reportContainer-"]') ||
                       document.querySelector('[class*="wrapper-dmId9qUc"]') ||
                       document.querySelector('[class*="wrapper-yprR2JgA"]');
        const editor = document.querySelector('.monaco-editor');
        const dialogs = Array.from(document.querySelectorAll('[class*="dialog"], [class*="modal"], [class*="toast"]')).map(d => (d.innerText || '').trim().replace(/\\n+/g, ' | ')).filter(Boolean);
        return {
            matchingButtons: bottomTabs.slice(0, 10),
            hasReport: !!report,
            reportSnippet: report ? report.innerText.slice(0, 300) : 'none',
            hasEditor: !!editor,
            dialogs: dialogs.slice(0, 5)
        };
    })()"""
    res = await client.eval_js(js)
    print(json.dumps(res, indent=2))
    await client.close()

if __name__ == '__main__':
    asyncio.run(check())
