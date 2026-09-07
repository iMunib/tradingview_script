"""
Optimized generate_variant implementation with direct window compilation
"""
import os
import re

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STRATEGY_TEMPLATE = os.path.join(ROOT_DIR, "strategy.pine")
TEMP_PINE = os.path.join(ROOT_DIR, "strategy_variant.pine")

def generate_variant(rsi_len=14, atr_mult=2.5, obv_len=20, date_filter=False, date_mode="All"):
    with open(STRATEGY_TEMPLATE, "r", encoding="utf-8") as f:
        code = f.read()

    # Unique title to force chart reload and avoid cached inputs
    strat_title = f"Quant Swing [{rsi_len}-{atr_mult}-{obv_len}] {date_mode}"
    code = re.sub(r'strategy\(\s*"[^"]*"', f'strategy("{strat_title}"', code)

    # Set parameter defaults
    code = re.sub(r'rsiLength\s*=\s*input\.int\(\s*\d+', f'rsiLength = input.int({rsi_len}', code)
    code = re.sub(r'atrStopMult\s*=\s*input\.float\(\s*[0-9.]+', f'atrStopMult = input.float({atr_mult}', code)
    code = re.sub(r'obvEmaLength\s*=\s*input\.int\(\s*\d+', f'obvEmaLength = input.int({obv_len}', code)

    # Direct code-level enforcement of the trade window
    if not date_filter or date_mode == "All":
        window_logic = "inTradeWindow = true\n// All dates enabled"
    elif date_mode == "In-Sample (2018-2024)":
        window_logic = "inTradeWindow = (time >= inSampleStart and time <= inSampleEnd)\n// In-sample 2018-2024"
    elif date_mode == "Out-of-Sample (2025-2026)":
        window_logic = "inTradeWindow = (time >= outSampleStart and time <= outSampleEnd)\n// Out-of-sample 2025-2026"
    else:
        window_logic = "inTradeWindow = true"

    code = re.sub(r'inTradeWindow\s*=\s*true[\s\S]*?(?=// ─── 1\. MACRO REGIME FILTER)', window_logic + "\n\n", code)

    with open(TEMP_PINE, "w", encoding="utf-8") as f:
        f.write(code)
    return TEMP_PINE

if __name__ == "__main__":
    generate_variant(14, 2.5, 20, True, "Out-of-Sample (2025-2026)")
    print("Generated variant successfully.")
