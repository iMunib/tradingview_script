import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
final_path = os.path.join(ROOT, 'FINAL_OPTIMIZED_STRATEGY.pine')

with open(final_path, 'r', encoding='utf-8') as f:
    code = f.read()

# 1. In-Sample Variant (2018-2024)
code_is = re.sub(r'useDateFilter\s*=\s*input\.bool\(false[^\n]*\)', 'useDateFilter       = true', code)
code_is = re.sub(r'dateMode\s*=\s*input\.string\("All"[^\n]*\)', 'dateMode            = "In-Sample (2018-2024)"', code_is)
if '// GENERATE-IS-START' in code and '// GENERATE-IS-END' in code:
    code_is = re.sub(
        r'// GENERATE-IS-START[\s\S]*?// GENERATE-IS-END',
        '// GENERATE-IS-START\nbool inTradeWindow = (time >= inSampleStart and time <= inSampleEnd)\n// GENERATE-IS-END',
        code_is
    )
else:
    code_is = re.sub(
        r'bool inTradeWindow = true[\s\S]*?(?=// ─── 1\. MACRO REGIME)',
        'bool inTradeWindow = (time >= inSampleStart and time <= inSampleEnd)\n',
        code_is
    )

# 2. Out-of-Sample Variant (2025-2026)
code_oos = re.sub(r'useDateFilter\s*=\s*input\.bool\(false[^\n]*\)', 'useDateFilter       = true', code)
code_oos = re.sub(r'dateMode\s*=\s*input\.string\("All"[^\n]*\)', 'dateMode            = "Out-of-Sample (2025-2026)"', code_oos)
if '// GENERATE-IS-START' in code and '// GENERATE-IS-END' in code:
    code_oos = re.sub(
        r'// GENERATE-IS-START[\s\S]*?// GENERATE-IS-END',
        '// GENERATE-IS-START\nbool inTradeWindow = (time >= outSampleStart and time <= outSampleEnd)\n// GENERATE-IS-END',
        code_oos
    )
else:
    code_oos = re.sub(
        r'bool inTradeWindow = true[\s\S]*?(?=// ─── 1\. MACRO REGIME)',
        'bool inTradeWindow = (time >= outSampleStart and time <= outSampleEnd)\n',
        code_oos
    )

with open(os.path.join(ROOT, 'strategy_is.pine'), 'w', encoding='utf-8') as f:
    f.write(code_is)

with open(os.path.join(ROOT, 'strategy_oos.pine'), 'w', encoding='utf-8') as f:
    f.write(code_oos)

print("Generated clean strategy_is.pine and strategy_oos.pine without duplicate definitions!")
