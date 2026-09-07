import asyncio, json, sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import runner
sys.stdout.reconfigure(encoding='utf-8')
async def main():
    ws_url = runner.get_ws_url()
    client = runner.CDPClient(ws_url)
    await client.connect()
    await client.find_tradingview_target()
    for i in range(20):
        js = """(() => {
            const dlg = document.querySelector('[data-name="broker-login-dialog"]');
            if (!dlg) return JSON.stringify({noDlg:true});
            const btn = dlg.querySelector('button[name="broker-login-submit-button"]');
            if (!btn) return JSON.stringify({noBtn:true});
            return JSON.stringify({
                text: (btn.innerText||btn.textContent||'').trim().slice(0,40),
                aria: btn.getAttribute('aria-disabled'),
                disabled: btn.disabled,
                class: btn.className.slice(0,80),
                html: btn.outerHTML.slice(0,600)
            });
        })()"""
        res_str = await client.eval_js(js)
        res = json.loads(res_str)
        print(f"[{i}] {res}")
        if res.get('text') == 'Connect' and res.get('aria') != 'true':
            print("-> Clicking Connect now")
            await client.eval_js("""(() => {
                const btn = document.querySelector('[data-name="broker-login-dialog"] button[name="broker-login-submit-button"]');
                if (btn) btn.click();
                return 'clicked';
            })()""")
            break
        await asyncio.sleep(2)
    # After click, wait and check bottom
    await asyncio.sleep(4)
    js2 = """(() => {
        const dlg = document.querySelector('[data-name="broker-login-dialog"]');
        const sel = document.querySelector('[data-name="select-broker-dialog"]');
        const bottom = document.querySelector('.layout__area--bottom');
        return {
            brokerDlg: !!dlg,
            selectDlg: !!sel,
            bottomSnippet: bottom ? bottom.innerText.slice(0,1500) : 'no bottom',
            bodyHasPaper: document.body.innerText.includes('Paper Trading') ? 'yes' : 'no'
        };
    })()"""
    res2 = await client.eval_js(js2)
    print(json.dumps(res2, indent=2, ensure_ascii=False))
    await client.close()
asyncio.run(main())
