import asyncio
import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)
import scripts.quick_test as qt

# Let's test with dEma200
code = open(os.path.join(ROOT_DIR, "test_strategy.pine"), "r", encoding="utf-8").read()

# Replace macro filter to require close > dEma200 on daily
old_macro = 'macroEma = isWeekly ? weeklyMacro : (not na(wEma200) ? wEma200 : dEma200)'
new_macro = 'macroEma = isWeekly ? weeklyMacro : dEma200'

code_d200 = code.replace(old_macro, new_macro)
with open(os.path.join(ROOT_DIR, ".diag_tmp", "test_d200.pine"), "w", encoding="utf-8") as f:
    f.write(code_d200)

async def test():
    await qt.run_single("BITSTAMP:BTCUSD", "1D", os.path.join(ROOT_DIR, ".diag_tmp", "test_d200.pine"), "Out-of-Sample (2025-2026)")

asyncio.run(test())
