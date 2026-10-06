#!/usr/bin/env python3
"""Run every skill's tests/smoke.py and write STATUS.md. Exit 1 if any skill fails.

Usage: python3 tests/run_all.py [--skills NAME,NAME] [--status STATUS.md]
"""
import argparse, datetime, pathlib, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--skills", help="comma-separated skill names (default: all)")
    ap.add_argument("--status", default=str(ROOT / "STATUS.md"))
    a = ap.parse_args()
    wanted = set(a.skills.split(",")) if a.skills else None
    rows, failed = [], 0
    for smoke in sorted(ROOT.glob("skills/*/tests/smoke.py")):
        name = smoke.parents[1].name
        if wanted and name not in wanted:
            continue
        t0 = datetime.datetime.now()
        p = subprocess.run([sys.executable, str(smoke)], capture_output=True, text=True, timeout=900)
        secs = (datetime.datetime.now() - t0).seconds
        ok = p.returncode == 0
        failed += 0 if ok else 1
        lines = [l for l in (p.stdout + p.stderr).splitlines() if l.strip()]
        rows.append((name, ok, secs, lines))
        print(f"{'OK  ' if ok else 'FAIL'} {name} ({secs}s)")
        for l in lines:
            print("     " + l[:160])
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    out = [f"# Endpoint status", "", f"Last run: {now}. One minimal live call per endpoint; see each skill's `tests/smoke.py`.", "",
           "| Skill | Status | Seconds | Detail |", "|---|---|---|---|"]
    for name, ok, secs, lines in rows:
        detail = "<br>".join(l.replace("|", "/")[:120] for l in lines[:12])
        out.append(f"| {name} | {'OK' if ok else 'FAIL'} | {secs} | {detail} |")
    pathlib.Path(a.status).write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"\nwrote {a.status}; {len(rows)} skills, {failed} failed")
    sys.exit(1 if failed else 0)

if __name__ == "__main__":
    main()
