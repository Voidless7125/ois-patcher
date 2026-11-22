#!/usr/bin/env python3
"""Reads every modules_*.txt and components.txt of a game install and prints the balance tables used in BALANCE.md.

    python3 tools/balance/analyze.py "<game dir>/assets" [> tables.md]

Model (see BALANCE.md for the reasoning and its limits):
  efficiency of a module configuration = 100 + sum(efficiencymodifier of its installed components)
        (ComponentInterfaceInstance::getEfficiencyPercent; the asets/bsets step values are all 0 in the data)
  price of a module                    = class basevalue + sum(component basecost)        (ShipModule::getValue, full health)
  performance                          = the module's own stat(s) scaled by efficiency where the game does so
"""
import glob, os, re, sys

A = sys.argv[1] if len(sys.argv) > 1 else "assets"


def kv_blocks(path, kind):
    t = open(path, encoding="latin1").read()
    return re.findall(r"begin %s\b(.*?)end %s" % (kind, kind), t, re.S)


comps = {}
for b in kv_blocks(f"{A}/components.txt", "component"):
    d = {k.strip(): v.strip() for k, v in (l.strip().split("=", 1) for l in b.splitlines() if "=" in l and not l.strip().startswith("#"))}
    comps[int(d["id"])] = d
mods = []
for f in sorted(glob.glob(f"{A}/modules_*.txt")):
    for b in kv_blocks(f, "module"):
        d = {"_t": os.path.basename(f)[8:-4], "cfg": {}}
        for l in b.splitlines():
            l = l.strip()
            if not l or l.startswith("#") or "=" not in l:
                continue
            k, v = l.split("=", 1)
            if k == "configuration":
                p = v.split(",")
                d["cfg"][p[0].split(":")[0]] = [int(x) for x in p[1:] if re.fullmatch(r"\s*-?\d+\s*", x)]
            elif k != "boot":
                d[k] = v
        mods.append(d)


def num(d, k):
    try:
        return float(re.match(r"[-\d.]+", d[k]).group())
    except Exception:
        return None


def cfg_stats(m):
    out = {}
    for n, ids in m["cfg"].items():
        e = 100.0
        cost = 0.0
        for i in ids:
            if i in comps:
                e += float(comps[i].get("efficiencymodifier", 0))
                cost += float(comps[i].get("basecost", 0))
        out[n] = (e, num(m, "basevalue") + cost)
    return out


def dice_sides(s):
    m = re.match(r"(\d+)d(\d+)", s or "")
    return int(m.group(2)) if m else None


def perf(m, e):
    t, f = m["_t"], e / 100
    n = lambda k: num(m, k)
    return {"maindrive": lambda: n("thrust") * f, "generators": lambda: n("generationrate") * f,
            "batteries": lambda: n("maxpowercontent") * f, "solar": lambda: n("generationrate"),
            "rcs": lambda: n("rotationrate") * f, "jumpdrive": lambda: n("jumpdistance") * f,
            "weapons": lambda: n("tubes") * f / n("spinuptime"),
            "pds": lambda: (1 / dice_sides(m["hitchance"])) / n("reloadtime") * f,
            "cms": lambda: n("tubes") / n("reloadtime") * f, "comms": lambda: f / n("synctime"),
            "hackers": lambda: n("hackrange") / n("hacktime") * f, "arms": lambda: f / n("grappletime"),
            "sensors": lambda: n("sensorquality") * f, "ladar": lambda: n("ladarrange") * f}.get(t, lambda: None)()


def fm(x):
    return f"{x:,.0f}" if x >= 100 else f"{x:.3g}"


print("| Class | Module | Base | Price (new) | Eff min / new / max | Eff-adjusted stat (new) | Price per stat (new) | across configs |")
print("| :--- | :--- | ---: | ---: | :--- | ---: | ---: | :--- |")
for t in sorted({m["_t"] for m in mods}):
    for m in mods:
        if m["_t"] != t or not m.get("basevalue") or t == "npc":
            continue
        cs = cfg_stats(m)
        if "new" not in cs:
            continue
        e, p = cs["new"]
        pf = perf(m, e)
        vals = [cs[c][1] / perf(m, cs[c][0]) for c in cs if perf(m, cs[c][0])]
        es = [v[0] for v in cs.values()]
        print(f"| {t} | {m['name']} | {num(m, 'basevalue'):.0f} | {p:.0f} | {min(es):.0f} / {e:.0f} / {max(es):.0f} | "
              f"{fm(pf)} | {fm(p / pf)} | {fm(min(vals))} - {fm(max(vals))} |" if pf else
              f"| {t} | {m['name']} | {num(m, 'basevalue'):.0f} | {p:.0f} | {min(es):.0f} / {e:.0f} / {max(es):.0f} | - | - | - |")
