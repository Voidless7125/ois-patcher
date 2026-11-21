"""personal_variants' optional DLL step, end to end on a scratch copy of a game folder.

    python3 tools/dll/test_dll_plugin.py [game folder]    # folder only supplies the DLL names/bytes

Builds a fake OIS-Update package (changed copies of some of the game's DLLs plus a manifest) and checks:
  no package            -> no question, nothing changes
  package, answer no    -> nothing changes
  package, answer yes   -> DLLs replaced, originals backed up, --status reports it, uninstall restores bytes
  package, --yes        -> applies without asking
  damaged package       -> refused
  already current       -> no question
"""
import hashlib, io, os, shutil, sys, tempfile
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import dll_update, personal_variants as pv


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def run(fn, *a, answer=None, tty=False, **k):
    buf = io.StringIO()
    old_in, old_input = sys.stdin, __builtins__["input"] if isinstance(__builtins__, dict) else __builtins__.input
    asked = []
    class FakeIn(io.StringIO):
        def isatty(self): return tty
    sys.stdin = FakeIn()
    import builtins
    builtins.input = lambda prompt="": (asked.append(prompt), answer)[1]
    try:
        with redirect_stdout(buf):
            r = fn(*a, **k)
    finally:
        sys.stdin = old_in
        builtins.input = old_input
    return r, buf.getvalue(), asked


def main():
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    tmp = Path(tempfile.mkdtemp())
    try:
        game = tmp / "game"; game.mkdir()
        names = ["OpenAL32.dll", "fmod.dll", "zlib1.dll"]
        for n in names:
            data = (src / n).read_bytes() if src and (src / n).is_file() else (n.encode() * 50)
            (game / n).write_bytes(data)
        orig = {n: sha(game / n) for n in names}
        pkgdir = tmp / "OIS-Update"; pkgdir.mkdir()
        lines = ["# Version=9.9.9"]
        for n in names:
            (pkgdir / n).write_bytes((game / n).read_bytes() + b"NEW")
            lines.append(f"game {sha(pkgdir / n)} {n}")
        (pkgdir / "manifest.txt").write_text("\n".join(lines) + "\n")
        dll_update.HERE = tmp / "nowhere" / "x"          # patcher "lives" elsewhere
        os.environ.pop(dll_update.ENV_PACKAGE_DIR, None)
        dll_update._extra_search_dirs.clear()
        dll_update.running_game_processes = lambda: []

        # 1. no package anywhere
        hidden = tmp / "hidden"; pkgdir.rename(hidden)
        _, out, asked = run(pv.begin_run, game, False, answer="y", tty=True)
        assert not asked and not pv._dll["go"], "asked without a package"
        run(pv.post_install, game)
        assert {n: sha(game / n) for n in names} == orig
        dll_update._extra_search_dirs.clear()
        hidden.rename(pkgdir)

        # 2. package in the folder beside the game: asked; 'n'
        _, out, asked = run(pv.begin_run, game, False, answer="n", tty=True)
        assert len(asked) == 1 and "9.9.9" in out, (asked, out)
        run(pv.post_install, game)
        assert {n: sha(game / n) for n in names} == orig, "declined but changed"
        assert run(pv.summary_lines)[0] == []

        # 3. package, 'y'
        _, out, asked = run(pv.begin_run, game, False, answer="y", tty=True)
        assert len(asked) == 1
        run(pv.post_install, game)
        assert all(sha(game / n) == sha(pkgdir / n) for n in names), "not applied"
        assert (game / dll_update.BACKUP_DIRNAME / "fmod.dll").is_file()
        assert "applied" in run(pv.summary_lines)[0][0]
        st = "\n".join(run(pv.status_lines, game)[0]); assert "9.9.9" in st and "3/3" in st, st
        assert any("DLL" in x for x in run(pv.uninstall_plan, game)[0])

        # 4. already current: no question
        _, out, asked = run(pv.begin_run, game, False, answer="y", tty=True)
        assert not asked and "already match" in out

        # 5. uninstall restores the original bytes
        ok, out, _ = run(pv.uninstall, game)
        assert ok and {n: sha(game / n) for n in names} == orig, out
        assert not (game / dll_update.STATE_NAME).exists()

        # 6. --yes applies without asking; non-interactive without --yes skips
        _, out, asked = run(pv.begin_run, game, False, tty=False)
        assert not asked and not pv._dll["go"] and "--yes" in out
        _, out, asked = run(pv.begin_run, game, True, tty=False)
        assert not asked and pv._dll["go"]
        run(pv.post_install, game)
        assert all(sha(game / n) == sha(pkgdir / n) for n in names)
        run(pv.uninstall, game)

        # 7. damaged package is refused
        (pkgdir / "fmod.dll").write_bytes(b"corrupt")
        _, out, asked = run(pv.begin_run, game, True, tty=False)
        assert not pv._dll["go"] and "incomplete" in out
        run(pv.post_install, game)
        assert {n: sha(game / n) for n in names} == orig
        print("DLL plugin: all checks passed")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


main()
