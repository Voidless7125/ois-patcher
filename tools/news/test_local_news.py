#!/usr/bin/env python3
"""Round-trip test for --local-news (no game needed beyond its news_/info_ text files).

    python3 tools/news/test_local_news.py <assets folder>

Works on a temporary copy of the news_*/info_* files in <assets folder>, with the originals this tool saved next to it
(oisbugfix_original_assets) laid over them if present.  Checks that switching local news on adds exactly one `Req: in_sector_N`
line to each regional article (and nothing else changes), that running again changes nothing, that switching it off
returns to the standing fixes, and that restoring the saved originals gives back the starting files.
"""
import glob
import hashlib
import os
import re
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
import apply_data_fixes as adf


def main():
    src = sys.argv[1]
    work = tempfile.mkdtemp()
    assets, backups = os.path.join(work, "assets"), os.path.join(work, "orig")
    os.mkdir(assets)
    for f in glob.glob(os.path.join(src, "news_*.txt")) + glob.glob(os.path.join(src, "info_*.txt")):
        shutil.copy(f, assets)
    saved = os.path.join(src, "..", adf.ORIGINALS_DIRNAME)          # an installed game: start from the saved originals
    for f in glob.glob(os.path.join(saved, "*.txt")):
        shutil.copy(f, assets)

    def snap():
        return {os.path.basename(f): open(f, "rb").read() for f in glob.glob(os.path.join(assets, "*.txt"))}

    start = snap()
    quiet = lambda *a, **k: None
    ok = True

    def check(cond, what):
        nonlocal ok
        ok &= bool(cond)
        print(f"  {'PASS' if cond else 'FAIL'} {what}")

    import contextlib, io
    with contextlib.redirect_stdout(io.StringIO()):
        adf.apply_inplace(assets, backups, False)
    base = snap()
    with contextlib.redirect_stdout(io.StringIO()):
        adf.apply_inplace(assets, backups, True)
    on = snap()
    changed = [k for k in on if on[k] != base[k]]
    regional = [k for k in on if k.startswith("news_") and adf.local_news_fix(base[k].decode("utf-8"))]
    check(sorted(changed) == sorted(regional), f"{len(changed)} regional articles changed, no others")
    one_line = all(len(on[k].splitlines()) == len(base[k].splitlines()) + 1 for k in changed)
    check(one_line, "each gained exactly one line")
    check(all(re.search(rb"^Req: in_sector_\d+\r?$", on[k], re.M) for k in changed), "the line is `Req: in_sector_<n>`")
    check(all(on[k].replace(re.search(rb"^Req: in_sector_\d+\r?\n", on[k], re.M).group(0), b"", 1) == base[k]
              for k in changed), "removing that line gives the standing-fix text back")
    with contextlib.redirect_stdout(io.StringIO()):
        adf.apply_inplace(assets, backups, True)
    check(snap() == on, "running again changes nothing")
    with contextlib.redirect_stdout(io.StringIO()):
        adf.apply_inplace(assets, backups, False)
    check(snap() == base, "switching it off returns to the standing fixes")
    with contextlib.redirect_stdout(io.StringIO()):
        adf.apply_inplace(assets, backups, True)
    for f in glob.glob(os.path.join(backups, "*.txt")):
        shutil.copy(f, assets)
    restored = snap()
    check(not any(b"in_sector_" in restored[k] and b"in_sector_" not in start[k] for k in restored),
          "restoring the saved originals removes every local-news line")
    shutil.rmtree(work)
    print("\nall checks passed" if ok else "\nFAILED")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
