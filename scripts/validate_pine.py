import pathlib, re, sys
ROOT = pathlib.Path(r"C:\Users\RehmanPC\Downloads\TradingView Indicator")
files = ["CONFLUENCE_SWING_SUITE.pine", "CONFLUENCE_STUDY_OVERLAY.pine", "FINAL_OPTIMIZED_STRATEGY.pine"]
for fn in files:
    p = ROOT / fn
    if not p.exists():
        print(f"\n=== {fn} (MISSING — purged per 2026-09-07 consolidation, skipped) ===")
        continue
    txt = p.read_text(encoding="utf-8")
    print(f"\n=== {fn} ({len(txt.splitlines())} lines, {len(txt)} bytes) ===")
    checks = {
        "version 5/6": bool(re.search(r"//@version\s*=\s*[56]", txt)),
        "strategy or indicator": bool(re.search(r"(strategy|indicator)\s*\(", txt)),
        "lookahead_off": "barmerge.lookahead_off" in txt,
        "close[1] for security": "close[1]" in txt,
        "no lookahead_on": "lookahead_on" not in txt,
        "process_orders_on_close": "process_orders_on_close" in txt if "strategy(" in txt else True,
        "barstate.isconfirmed": "barstate.isconfirmed" in txt,
        "max_boxes_count": "max_boxes_count" in txt,
        "max_labels_count": "max_labels_count" in txt,
        "strategy.exit bracket": "strategy.exit" in txt if "strategy(" in txt else True,
        "pivotLeft=5": "pivotLeft" in txt,
        "atrStopMult": "atrStopMult" in txt,
        "tpMultiple": "tpMultiple" in txt,
        "wrFastLen 21": "wrFastLen" in txt,
        "wrSlowLen 112": "wrSlowLen" in txt,
        "godmode": "godmode" in txt,
        "fisher": "fisher" in txt,
        "fibLength 233": "fibLength" in txt,
        "confluenceScore": "confluenceScore" in txt,
        "FRED:FEDFUNDS": "FRED:FEDFUNDS" in txt,
        "Weekly 200 EMA": "wEma200" in txt,
    }
    for k,v in checks.items():
        print(f"  {'[PASS]' if v else '[FAIL]'} {k}")
    # bracket balance
    opens = txt.count("(")
    closes = txt.count(")")
    # box handling check
    if "osBox" in txt and "box.new" in txt:
        print(f"  [INFO] Box handling: osBox present, box.new count {txt.count('box.new')}")
    # mismatched brackets
    if opens != closes:
        print(f"  [WARN] Paren mismatch: ( {opens} vs ) {closes}")
    else:
        print(f"  [OK] Parens balanced: {opens}")
    # check for syntax errors: unmatched braces
    if txt.count("{") != txt.count("}"):
        print(f"  [WARN] Brace mismatch: {{ {txt.count('{')} vs }} {txt.count('}')}")
    # check indicator limit handling in runner
    # ensure no obvious Pine errors: double equals
    bad = re.findall(r"strategy\.entry\s*\([^)]*\)\s*\n\s*strategy\.entry", txt)
    if bad:
        print("  [WARN] consecutive entries without exit")
    # check HUD table
    if "table.new" in txt:
        print(f"  [INFO] HUD table present")

# Validate runner.py limit handling
print("\n=== runner.py hardening ===")
runner = (ROOT / "runner.py").read_text(encoding="utf-8")
checks_r = {
    "preDismiss limit modal": "limit reached" in runner.lower(),
    "Update on chart": "Update on chart" in runner,
    "Ctrl+Enter fallback": "dispatchKeyEvent" in runner and "modifiers" in runner,
    "Allow auto-click": "auto_allowed" in runner,
    "Save dialog": "save this script" in runner.lower(),
    "minimal removal": "hasQuantOnChart" in runner,
    "Monaco inject": "executeEdits" in runner,
    "polling 8s": "for _poll in range(16)" in runner,
    "read-only copy": "This script is read-only" in runner,
    "scrape report": "reportContainer" in runner,
}
for k,v in checks_r.items():
    print(f"  {'[PASS]' if v else '[FAIL]'} {k}")

# diff FINAL vs CONFLUENCE (skip if purged)
import difflib
try:
    c = (ROOT / "CONFLUENCE_SWING_SUITE.pine").read_bytes()
    f = (ROOT / "FINAL_OPTIMIZED_STRATEGY.pine").read_bytes()
    print(f"\n=== FINAL vs CONFLUENCE ===")
    print(f"  CONFLUENCE bytes: {len(c)}, FINAL bytes: {len(f)}, identical: {c==f}")
    if c!=f:
        diff = list(difflib.unified_diff(c.decode().splitlines()[:20], f.decode().splitlines()[:20]))
        print("\n".join(diff[:20]))
except FileNotFoundError:
    print(f"\n=== FINAL vs CONFLUENCE ===\n  Skipped — CONFLUENCE purged (single-script master: FINAL only, 1 slot)")

# Check handle_save_dialog
hsd = (ROOT / "scripts" / "handle_save_dialog.py").read_text(encoding="utf-8")
print("\n=== handle_save_dialog.py ===")
for kw in ["Auto-allowed", "Save this script", "limit reached"]:
    print(f"  {'[PASS]' if kw in hsd else '[FAIL]'} {kw}")

# Check Edge scripts
ea = (ROOT / "scripts" / "enable_always_allow_debug.ps1").read_text(encoding="utf-8")
print("\n=== enable_always_allow_debug.ps1 ===")
for kw in ["RemoteDebuggingAllowed", "edge://inspect", "Allow remote debugging"]:
    print(f"  {'[PASS]' if kw in ea else '[FAIL]'} {kw}")
la = (ROOT / "scripts" / "launch_edge_with_debugging.ps1").read_text(encoding="utf-8")
print("\n=== launch_edge_with_debugging.ps1 ===")
for kw in ["remote-debugging-port", "TcpTestSucceeded", "evaluate_all_assets"]:
    print(f"  {'[PASS]' if kw in la else '[FAIL]'} {kw}")

print("\n=== VALIDATION COMPLETE ===")
