import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
final_path = os.path.join(ROOT, 'FINAL_OPTIMIZED_STRATEGY.pine')

with open(final_path, 'r', encoding='utf-8') as f:
    code = f.read()

# 1. In-Sample Variant (2018-2024)
code_is = re.sub(r'useDateFilter\s*=\s*input\.bool\(false[^\n]*\)', 'useDateFilter       = true', code)
code_is = re.sub(r'dateMode\s*=\s*input\.string\([^,]+', 'dateMode            = input.string("In-Sample (2018-2024)"', code_is)
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
code_oos = re.sub(r'dateMode\s*=\s*input\.string\([^,]+', 'dateMode            = input.string("Out-of-Sample (2025-2026)"', code_oos)
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

# 3. Full Windowed Variant (2018-2026)
code_full = re.sub(r'useDateFilter\s*=\s*input\.bool\(false[^\n]*\)', 'useDateFilter       = true', code)
code_full = re.sub(r'dateMode\s*=\s*input\.string\([^,]+', 'dateMode            = input.string("Full (2018-2026)"', code_full)
if '// GENERATE-IS-START' in code and '// GENERATE-IS-END' in code:
    code_full = re.sub(
        r'// GENERATE-IS-START[\s\S]*?// GENERATE-IS-END',
        '// GENERATE-IS-START\nbool inTradeWindow = (time >= inSampleStart and time <= outSampleEnd)\n// GENERATE-IS-END',
        code_full
    )
else:
    code_full = re.sub(
        r'bool inTradeWindow = true[\s\S]*?(?=// ─── 1\. MACRO REGIME)',
        'bool inTradeWindow = (time >= inSampleStart and time <= outSampleEnd)\n',
        code_full
    )

with open(os.path.join(ROOT, 'strategy_is.pine'), 'w', encoding='utf-8') as f:
    f.write(code_is)

with open(os.path.join(ROOT, 'strategy_oos.pine'), 'w', encoding='utf-8') as f:
    f.write(code_oos)

with open(os.path.join(ROOT, 'strategy_full.pine'), 'w', encoding='utf-8') as f:
    f.write(code_full)

print("Generated clean strategy_is.pine, strategy_oos.pine, and strategy_full.pine without duplicate definitions!")
