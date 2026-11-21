#!/usr/bin/env python3
"""Lifecycle test for the local-news plugin feature (personal_variants.py).  Needs no game files:

    python3 tools/news/test_local_news.py [<game dir with assets/>]

Builds news_*.txt files in a temporary game folder (or copies the ones from <game dir>/assets, with any originals
the patcher saved laid over them), then runs the same sequence ois_patcher.py does -- begin_run, the patcher's own
in-place fixes (apply_data_fixes.apply_inplace), post_install -- and checks that each regional article gains exactly one
`Req: in_sector_N` line and nothing else changes, that re-running is a no-op, that the patcher's backups never contain
the line (so uninstall gives back the true originals), and that the plugin's own uninstall removes it again.
"""
import contextlib
import glob
import io
import os
import re
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", ".."))
import apply_data_fixes as adf
import personal_variants as pv


def quiet(fn, *a, **k):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*a, **k)


def synthetic(assets):
    """One regional + one global article per line ending, and a regional one the patcher itself fixes."""
    fixed_name, fixes = next((f, l) for f, l in adf.FIXES.items() if adf.is_inplace(f) and f.startswith("news_"))
    body = "".join(old + "\n" for _, old, _ in fixes)
    arts = {
        "news_t1.txt": "Publication: The Diwali Examiner\nDate: 1\n\nBody\n",
        "news_t2.txt": "Publication: The Diwali Examiner\r\nDate: 1\r\n\r\nBody\r\n",
        "news_t3.txt": "Publication: The Sentinel\nDate: 1\n\nBody\n",
        # a stock article that already carries a (different) sector requirement: must stay exactly as it is
        "news_theatrereviewtheproximacentauriplayers.txt": "Publication: The Penitent Times\nReq: in_sector_3\nDate: 1\n\nBody\n",
        "news_t4.txt": "Publication: The Penitent Times\nDate: 1\nReq: in_sector_2\n\nBody\n",
        fixed_name: "Publication: The Galilean Post\n" + body,
    }
    for n, t in arts.items():
        with open(os.path.join(assets, n), "wb") as f:
            f.write(t.encode())
    return set(arts) - {"news_t3.txt", "news_theatrereviewtheproximacentauriplayers.txt", "news_t4.txt"}


def main():
    game = tempfile.mkdtemp()
    assets, backups = os.path.join(game, "assets"), os.path.join(game, adf.ORIGINALS_DIRNAME)
    os.mkdir(assets)
    if len(sys.argv) > 1:
        src = sys.argv[1]
        for f in glob.glob(os.path.join(src, "assets", "news_*.txt")):
            shutil.copy(f, assets)
        for f in glob.glob(os.path.join(src, adf.ORIGINALS_DIRNAME, "news_*.txt")):
            shutil.copy(f, assets)
        regional = {os.path.basename(f) for f in glob.glob(os.path.join(assets, "news_*.txt"))
                    if os.path.basename(f) not in pv.STOCK_SECTOR_FILES
                    and pv.local_news_line(open(f, encoding="utf-8").read())
                    and not pv._SECTOR_REQ.search(open(f, encoding="utf-8").read())}
    else:
        regional = synthetic(assets)

    def snap():
        return {os.path.basename(f): open(f, "rb").read() for f in glob.glob(os.path.join(assets, "*.txt"))}

    ok = True

    def check(cond, what):
        nonlocal ok
        ok &= bool(cond)
        print(f"  {'PASS' if cond else 'FAIL'} {what}")

    def run():                                           # what ois_patcher.py does around an install
        quiet(pv.begin_run, game, True)
        quiet(adf.apply_inplace, assets, backups)
        quiet(pv.post_install, game)

    start = snap()
    quiet(adf.apply_inplace, assets, backups)
    base = snap()                                        # the patcher's own fixes only
    run()
    on = snap()
    changed = {k for k in on if on[k] != base[k]}
    check(changed == regional, f"{len(changed)} regional article(s) changed, no others")
    check(all(len(on[k].splitlines()) == len(base[k].splitlines()) + 1 for k in changed), "each gained exactly one line")
    check(all(re.search(rb"^Req: in_sector_\d+\r?$", on[k], re.M) for k in changed), "the line is `Req: in_sector_<n>`")
    check(all(pv.strip_local_news(on[k].decode()).encode() == base[k] for k in changed), "stripping it gives the fixed text back")
    check(all(not pv.has_local_news(open(os.path.join(backups, k), encoding="utf-8").read()) for k in changed
              if os.path.exists(os.path.join(backups, k))), "the patcher's saved originals never contain the line")
    check(all(on[k] == start[k] for k in ("news_theatrereviewtheproximacentauriplayers.txt", "news_t4.txt") if k in on),
          "articles that already have their own sector requirement are left exactly as they are")
    run()
    check(snap() == on, "running again changes nothing")
    quiet(pv.begin_run, game, True)
    check(snap() == base, "begin_run lifts it again (so the patcher's backup logic never sees it)")
    run()
    check(pv.uninstall_plan(game) != [], "uninstall plan offers to remove it")
    quiet(pv.uninstall, game)
    check(snap() == base and pv.uninstall_plan(game) == [], "plugin uninstall removes it")
    for f in glob.glob(os.path.join(backups, "*.txt")):  # then the patcher restores its saved originals
        shutil.copy(f, assets)
    after = snap()
    check(all(after[k] == start[k] for k in start), "after the patcher's restore every file equals the starting file")
    shutil.rmtree(game)
    print("\nall checks passed" if ok else "\nFAILED")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
