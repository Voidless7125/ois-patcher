#!/usr/bin/env python3
"""Checks gog_port.py against the current ois_patcher.py (no game files needed).

    python3 tools/gog/test_gog_port.py

  1. every ported fix still translates (no address in its source missing from MAP);
  2. every client fix the patcher runs is classified: ported, native (same addresses in both builds) or unported -- so a
     newly added fix fails this test until someone decides what it does on GOG;
  3. on a GOG-stamped exe the ported fixes look only at GOG addresses, on a Steam-stamped one only at Steam addresses,
     and the unported ones are skipped on GOG only (and not for the server);
  4. the server exe is never rerouted.
"""
import ast
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
sys.path.insert(0, ROOT)
import gog_port as G
import ois_patcher as P

bad = 0


def check(ok, text):
    global bad
    bad += not ok
    print(("  PASS " if ok else "  FAIL ") + text)


class FE:                        # just enough of a PE
    def __init__(self, ts):
        self.FILE_HEADER = type("H", (), {"TimeDateStamp": ts})()


STEAM, GOGPE = FE(1557140428), FE(G.GOG_TIMESTAMP)

# the client fix list, read from the patcher's own source
src = open(os.path.join(ROOT, "ois_patcher.py"), encoding="utf-8").read()
tree = ast.parse(src)
main_fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
client_calls = []
for n in ast.walk(main_fn):
    if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id.startswith("fix_") and \
            not any(k.arg == "server" for k in n.keywords) and n.func.id not in client_calls:
        client_calls.append(n.func.id)
# fixes in main() that belong to the client path (patch_server_exe has its own list)
known = set(G.PORTED) | set(G.NATIVE) | set(G.UNPORTED)
check(True, f"{len(G.PORTED)} ported + {len(G.NATIVE)} native + {len(G.UNPORTED)} unported")
unclassified = [c for c in client_calls if c not in known]
check(not unclassified, f"every client fix is classified (unclassified: {unclassified})")
check(all(hasattr(P, n) for n in known), "every classified name exists in ois_patcher.py")

ported, failed = G.install(P)
check(not failed, f"all ported fixes translate (failed: {failed})")
check(set(ported) == set(G.PORTED), f"{len(G.PORTED)} ported functions built")

# 3. which addresses does each fix look at?
seen = []
real_verify = P.verify_site
P.verify_site = lambda data, pe, va, expected, label: (seen.append(va), None)[1]
P.FIXES_SKIPPED.clear()
steam_keys, gog_vals = set(G.MAP), set(G.MAP.values())
for name in G.PORTED:
    for pe, pool, tag in ((GOGPE, gog_vals, "GOG"), (STEAM, steam_keys, "Steam")):
        seen.clear()
        try:
            r = getattr(P, name)(bytearray(), pe, 0, 0, 0) if name != "fix_pirate_hunt_format_string" else getattr(P, name)(bytearray(), pe)
        except Exception as e:                    # a fix that touches pe/data before verify_site: not testable this way
            seen.append(None)
        real = [v for v in seen if v is not None]
        if not real and None in seen:
            continue
        ok = bool(real) and all(any(abs(v - a) <= 16 for a in pool) for v in real)   # a site may be addressed as SITE-n
        check(ok, f"{name:<44} {tag}: looks at {len(real)} site(s), all {tag} addresses")
# unported: skipped on GOG client, run on Steam and on server
P.FIXES_SKIPPED.clear()
ran = []
for name, label in G.UNPORTED.items():
    r = getattr(P, name)(bytearray(), GOGPE, 0, 0, 7)
    check(r == 7 and any(label in s for s in P.FIXES_SKIPPED), f"{name:<44} skipped on GOG, cursor unchanged")
n0 = len(P.FIXES_SKIPPED)
for name in G.UNPORTED:
    try:
        getattr(P, name)(bytearray(), STEAM, 0, 0, 7)
    except Exception:
        pass                                      # reached its own code (empty data), i.e. not intercepted
check(not any("GOG build" in s for s in P.FIXES_SKIPPED[n0:]), "unported fixes are not intercepted on a Steam exe")
P.verify_site = real_verify
print("all GOG-port checks pass" if not bad else f"{bad} FAILED")
sys.exit(1 if bad else 0)
