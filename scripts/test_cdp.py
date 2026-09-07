import os
import sys

os.environ['DEBUG'] = 'pw:browser*,pw:protocol*'

from playwright.sync_api import sync_playwright

print("Starting playwright...")
with sync_playwright() as p:
    print("Connecting over CDP to ws://127.0.0.1:9222/devtools/browser/f4211e06-b384-4568-9e42-fab8126bb7a9 ...")
    try:
        browser = p.chromium.connect_over_cdp("ws://127.0.0.1:9222/devtools/browser/f4211e06-b384-4568-9e42-fab8126bb7a9", timeout=15000)
        print("Connected via ws endpoint!")
        for ctx in browser.contexts:
            for page in ctx.pages:
                print("Page:", page.url, page.title())
    except Exception as e:
        print("WS failed:", e)
