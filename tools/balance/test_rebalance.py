#!/usr/bin/env python3
"""Tests rebalance.py and its plugin hooks.

    python3 tools/balance/test_rebalance.py [<game dir>/assets]

Synthetic checks always run; with the game's assets folder it also checks the real files:
  - only `basevalue=` lines change; every other line is byte-identical
  - each class keeps its average price (within rounding), no price leaves the floor/ceiling band
  - a module that is better on every stat never costs less than one it beats
  - re-running on its own output changes nothing (the mod folder is read first when a data fix wrote a copy)
Plugin: choice remembered in a flag file, --yes keeps but never opts in, uninstall plan and uninstall clear it.
"""
import difflib
import io
import os
import statistics
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import rebalance as R
import personal_variants as pv

bad = 0


def check(ok, text):
    global bad
    bad += not ok
    print(("  PASS " if ok else "  FAIL ") + text)


def synthetic():
    mk = lambda i, tubes, spin, price: (f"begin module\ntype=weapon\nid={i}\nname={i}\ntubes={tubes}\nspinuptime={spin}\n"
                                        f"normalpowerusage=0.2\nhighpowerusage=5\nbasevalue={price}\nend module\n")
    text = mk("a", 1, 30, 2000) + mk("b", 4, 20, 2000) + mk("c", 8, 15, 2000)
    out, ch = R.rewrite("weapons", text)
    p = {i: n for i, (_, n) in ch.items()}
    check(p["a"] < p["b"] < p["c"], f"price follows output: {p}")
    check(abs(sum(p.values()) / 3 - 2000) <= 10, "class average kept")
    check(R.rewrite("weapons", out)[1].get("b", (0, p["b"]))[1] == p["b"], "re-run is stable")
    check(R.plan_file("helm", text) == {}, "classes without an output stat are skipped")
    check(R.plan_file("weapons", mk("x", 1, 1, 0) + mk("y", 2, 2, 0)) == {}, "modules without a basevalue (never sold) are skipped")
    check(R.rewrite("weapons", text, 0.0)[1] == {k: (2000, 2000) for k in "abc"}, "strength 0 changes nothing")


def real(assets):
    tmp = Path(tempfile.mkdtemp())
    n = R.apply(assets, tmp)
    check(n == 126, f"{n} modules repriced")
    spreads = {}
    for kind in R.SCORE:
        src = (assets / f"modules_{kind}.txt").read_text(encoding="utf-8", errors="surrogateescape")
        dst = (tmp / f"modules_{kind}.txt").read_text(encoding="utf-8", errors="surrogateescape")
        diff = [l for l in difflib.unified_diff(src.splitlines(), dst.splitlines(), lineterm="", n=0)
                if l[:1] in "+-" and not l.startswith(("+++", "---"))]
        only = all("basevalue=" in l for l in diff)
        olds = [d for d in (R._kv(m.group(1)) for m in R._blocks(src)) if "id" in d and R._num(d, "basevalue", 0) > 0]
        news = {d["id"]: R._num(d, "basevalue") for d in (R._kv(m.group(1)) for m in R._blocks(dst)) if "id" in d}
        mo = statistics.mean(R._num(d, "basevalue") for d in olds)
        mn = statistics.mean(news[d["id"]] for d in olds)
        band = all(R.FLOOR * 0.95 * mo <= news[d["id"]] <= R.CEILING * 1.05 * mo for d in olds)
        check(only and abs(mn / mo - 1) < 0.01 and band, f"{kind:<10} only basevalue lines, mean {mo:.0f} -> {mn:.0f}, inside the band")
        # monotone: strictly better on score never cheaper
        sc = {d["id"]: R.SCORE[kind](d) for d in olds}
        ok = all(news[a] <= news[b] for a in sc for b in sc if sc[a] < sc[b] * 0.999)
        check(ok, f"{kind:<10} higher score never costs less")
    # idempotent through the mod folder
    n2 = R.apply(assets, tmp)
    again = {k: (tmp / f"modules_{k}.txt").read_text(encoding="utf-8", errors="surrogateescape") for k in R.SCORE}
    tmp2 = Path(tempfile.mkdtemp())
    for k, t in again.items():
        (tmp2 / f"modules_{k}.txt").write_text(t, encoding="utf-8", errors="surrogateescape")
    R.apply(tmp, tmp2)
    same = all((tmp2 / f"modules_{k}.txt").read_text(encoding="utf-8", errors="surrogateescape") == again[k] for k in R.SCORE)
    check(same, "re-running on the repriced files changes nothing")


def plugin():
    from ois_patcher import MOD_DIR_RELATIVE
    g = Path(tempfile.mkdtemp())
    (g / "assets").mkdir()
    mod = g.joinpath(*MOD_DIR_RELATIVE)
    mod.mkdir(parents=True)
    (g / "assets" / "modules_weapons.txt").write_text(
        "".join(f"begin module\ntype=weapon\nid={i}\nname={i}\ntubes={t}\nspinuptime={s}\nnormalpowerusage=0.2\nhighpowerusage=5\n"
                f"basevalue=2000\nend module\n" for i, t, s in (("a", 1, 30), ("b", 4, 20), ("c", 8, 15))))
    flag = g / pv.REBALANCE_FLAG

    class In(io.StringIO):
        def isatty(self): return self.tty
    def run(fn, *a, answer=None, tty=True, env=None):
        import builtins
        old_in, old_input = sys.stdin, builtins.input
        sys.stdin = In(); sys.stdin.tty = tty
        builtins.input = lambda prompt="": answer
        old_env = os.environ.get("OIS_REBALANCE")
        if env is None: os.environ.pop("OIS_REBALANCE", None)
        else: os.environ["OIS_REBALANCE"] = env
        try:
            with redirect_stdout(io.StringIO()):
                return fn(*a)
        finally:
            sys.stdin, builtins.input = old_in, old_input
            if old_env is None: os.environ.pop("OIS_REBALANCE", None)
            else: os.environ["OIS_REBALANCE"] = old_env
    price = lambda: [l for l in (mod / "modules_weapons.txt").read_text().splitlines() if l.startswith("basevalue")] if (mod / "modules_weapons.txt").exists() else None

    run(pv._rebalance_ask, g, False, answer="n"); run(pv._rebalance_apply, g)
    check(price() is None and not flag.exists(), "declined: nothing written")
    run(pv._rebalance_ask, g, True, tty=False); run(pv._rebalance_apply, g)
    check(price() is None and not flag.exists(), "--yes alone does not opt in")
    run(pv._rebalance_ask, g, False, answer="y"); run(pv._rebalance_apply, g)
    p = price()
    check(p and len(set(p)) == 3 and flag.exists(), f"accepted: repriced {p}, flag written")
    check("put the module prices back" in " ".join(pv.uninstall_plan(g)), "uninstall plan mentions it")
    check("applied" in " ".join(pv.status_lines(g)), "--status reports it")
    (mod / "modules_weapons.txt").unlink()
    run(pv._rebalance_ask, g, True, tty=False); run(pv._rebalance_apply, g)
    check(price() is not None and flag.exists(), "--yes keeps an existing choice")
    (mod / "modules_weapons.txt").unlink()
    run(pv._rebalance_ask, g, False, answer="n"); run(pv._rebalance_apply, g)
    check(price() is None and not flag.exists(), "answering n to 'keep it?' turns it off and clears the flag")
    run(pv._rebalance_ask, g, True, tty=False, env="1"); run(pv._rebalance_apply, g)
    check(price() is not None and flag.exists(), "OIS_REBALANCE=1 opts in unattended")
    with redirect_stdout(io.StringIO()):
        pv.uninstall(g)
    check(not flag.exists(), "uninstall clears the flag")


synthetic()
plugin()
if len(sys.argv) > 1:
    real(Path(sys.argv[1]))
print("all rebalance checks pass" if not bad else f"{bad} FAILED")
sys.exit(1 if bad else 0)
