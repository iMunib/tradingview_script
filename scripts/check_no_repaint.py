"""No-repaint regression guard (Phase 1e).

Fails the commit if:
  1. the count of `lookahead_off` in FINAL_OPTIMIZED_STRATEGY.pine decreases
     vs HEAD, or
  2. any `request.security()` call lacks `lookahead=barmerge.lookahead_off`.

Usage: python scripts/check_no_repaint.py [--base HEAD]
Exit 0 = pass, 1 = fail.
"""
import subprocess
import sys

MASTER = "FINAL_OPTIMIZED_STRATEGY.pine"


def git_show(rev, path):
    r = subprocess.run(["git", "show", f"{rev}:{path}"],
                       capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


def audit(code):
    lines = code.splitlines()
    la = code.count("lookahead_off")
    bad = [(i + 1, l.strip()[:160]) for i, l in enumerate(lines)
           if "request.security(" in l and "lookahead_off" not in l]
    return la, bad


def main():
    base = sys.argv[2] if len(sys.argv) > 2 and sys.argv[1] == "--base" else "HEAD"
    with open(MASTER, encoding="utf-8") as f:
        work = f.read()
    w_la, w_bad = audit(work)
    ref = git_show(base, MASTER)
    if ref is not None:
        r_la, _ = audit(ref)
        if w_la < r_la:
            print(f"FAIL: lookahead_off count decreased {r_la} -> {w_la}")
            return 1
        print(f"lookahead_off: {r_la} (base) -> {w_la} (work) OK")
    else:
        print(f"lookahead_off: {w_la} (no base to compare) OK")
    if w_bad:
        print("FAIL: request.security() without lookahead_off:")
        for n, l in w_bad:
            print(f"  line {n}: {l}")
        return 1
    print("All request.security() calls carry lookahead_off. PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
