import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
final_path = os.path.join(ROOT, 'FINAL_OPTIMIZED_STRATEGY.pine')

with open(final_path, 'r', encoding='utf-8') as f:
    code = f.read()

# 1. In-Sample Variant (2018-2024)
code_is = code.replace(
    'strategy("FINAL OPTIMIZED QUANT MULTI-FACTOR SWING STRATEGY",',
    'strategy("FINAL QUANT STRATEGY - IN SAMPLE", shorttitle="QUANT_IS",'
)
# Remove the input declarations for date window to avoid re-declaration
code_is = re.sub(r'group_dates\s*=\s*"Walk-Forward Validation Window"[\s\S]*?(?=group_ui\s*=\s*"Visual Interface & HUD")', '', code_is)
code_is = re.sub(
    r'bool inTradeWindow = true[\s\S]*?(?=// ═══════════════════════════════════════════════════════════════════════════════\r?\n// 3\. ZERO-LOOKAHEAD)',
    'bool inTradeWindow = (time >= inSampleStart and time <= inSampleEnd)\nbool useDateFilter = true\n\n',
    code_is
)

# 2. Out-of-Sample Variant (2025-2026)
code_oos = code.replace(
    'strategy("FINAL OPTIMIZED QUANT MULTI-FACTOR SWING STRATEGY",',
    'strategy("FINAL QUANT STRATEGY - OUT OF SAMPLE", shorttitle="QUANT_OOS",'
)
code_oos = re.sub(r'group_dates\s*=\s*"Walk-Forward Validation Window"[\s\S]*?(?=group_ui\s*=\s*"Visual Interface & HUD")', '', code_oos)
code_oos = re.sub(
    r'bool inTradeWindow = true[\s\S]*?(?=// ═══════════════════════════════════════════════════════════════════════════════\r?\n// 3\. ZERO-LOOKAHEAD)',
    'bool inTradeWindow = (time >= outSampleStart and time <= outSampleEnd)\nbool useDateFilter = true\n\n',
    code_oos
)

with open(os.path.join(ROOT, 'strategy_is.pine'), 'w', encoding='utf-8') as f:
    f.write(code_is)

with open(os.path.join(ROOT, 'strategy_oos.pine'), 'w', encoding='utf-8') as f:
    f.write(code_oos)

print("Generated clean strategy_is.pine and strategy_oos.pine without duplicate definitions!")
