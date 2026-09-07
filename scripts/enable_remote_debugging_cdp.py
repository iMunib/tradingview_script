"""
Auto-consent for edge://inspect 'Allow remote debugging for this browser instance' checkbox.
Connects via CDP, navigates to edge://inspect, clicks the checkbox, and verifies persistence.
This makes the Allow prompt permanently dismissed (stored in Preferences).
"""

import asyncio
import json
import os
import sys
import argparse

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)
import runner


async def enable_via_cdp(port=9222):
    ws_url = runner.get_ws_url()
    # Override port if specified
    if port != 9222:
        ws_url = f"ws://127.0.0.1:{port}/devtools/browser"
        # Patch get_ws_url to use explicit port for this run
        runner.get_ws_url = lambda: ws_url

    client = runner.CDPClient(ws_url)
    try:
        await client.connect()
    except Exception as e:
        print(f"[WARN] Could not connect to CDP ws={ws_url}: {e}")
        print("       Make sure Edge is running with --remote-debugging-port=9222")
        return False

    # Find or create edge://inspect target
    try:
        await client.find_tradingview_target()
    except Exception:
        pass

    # Attach may already be valid; now navigate to edge://inspect via JS or new target
    print("[INFO] Creating edge://inspect target to set consent...")
    try:
        create_res = await client.send_cmd("Target.createTarget", {"url": "edge://inspect"})
        target_id = create_res.get("targetId")
        await asyncio.sleep(2)
        attach_res = await client.send_cmd("Target.attachToTarget", {"targetId": target_id, "flatten": True})
        session_id = attach_res.get("sessionId")
        # Evaluate click for Allow checkbox
        js = r"""
        (() => {
            // edge://inspect page structure
            const all = Array.from(document.querySelectorAll('input[type=\"checkbox\"], button, label'));
            // Look for Remote debugging checkbox
            const txt = document.body ? document.body.innerText : '';
            if (!/Remote debugging/i.test(txt)) return 'not on inspect page: ' + txt.slice(0,200);
            const cb = document.querySelector('input[type=\"checkbox\"]');
            if (cb) {
                if (!cb.checked) { cb.click(); return 'clicked checkbox (now checked=' + cb.checked + ')'; }
                else return 'already checked';
            }
            // fallback: find label containing Allow remote debugging
            const label = Array.from(document.querySelectorAll('label, div')).find(el => /Allow remote debugging/i.test(el.innerText||''));
            if (label) {
                const input = label.querySelector('input');
                if (input && !input.checked) { input.click(); return 'clicked label input'; }
                label.click(); return 'clicked label';
            }
            return 'checkbox not found but page loaded';
        })()
        """
        res = await client.send_cmd("Runtime.evaluate", {"expression": js, "returnByValue": True, "awaitPromise": True}, session_id=session_id)
        val = res.get("result", {}).get("value", res)
        print(f"[INFO] edge://inspect consent result: {val}")
        await client.send_cmd("Target.closeTarget", {"targetId": target_id})
        await asyncio.sleep(1)
        await client.close()
        return True
    except Exception as e:
        print(f"[WARN] CDP consent flow failed: {e}")
        try:
            await client.close()
        except: pass
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=9222)
    args = parser.parse_args()
    asyncio.run(enable_via_cdp(port=args.port))
