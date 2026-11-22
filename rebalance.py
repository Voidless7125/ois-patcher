"""
rebalance.py -- optional module price rebalance for personal_variants.py (not part of the stock patcher).

What it changes: the `basevalue` of the modules that ship in stations, so the price follows what the module does.
What it leaves alone: every other stat, the components (their cost and efficiency), the module files' other lines.
See BALANCE.md for the analysis behind it (price per unit of output differed by 2x to 9x inside a class).

How the new price is worked out, per class (jump drives, weapons, ...):
  1. score = a weighted geometric mean of the module's own stats, higher being better (thrust, tubes per second, range ...)
     and lower being better (power draw, emissions, reload ...); the weights are in SCORE below.
  2. price = (class average price) * (score / class average score) ** STRENGTH, kept between FLOOR and CEILING times the
     class average, then scaled so the class average price is exactly what it was.
So a class costs the same on average as before; inside it, a module that does twice as much costs about twice as much (at
STRENGTH 1.0).  Efficiency comes from the components and is priced by them, so it is deliberately not in the score.
Nothing here is bundled game data: it is computed at install time from the player's own module files.

Classes with no output stat to price (helm, LADAR which the shop never sells, the NPC modules) are untouched.
"""
import math
import re
from pathlib import Path

STRENGTH = 1.0      # 0 = no change, 1 = price proportional to output, in between = a gentler version
FLOOR, CEILING = 0.4, 2.0
ROUND_TO = 10


def _blocks(text):
    return list(re.finditer(r"begin module\b(.*?)end module", text, re.S))


def _kv(block):
    d = {}
    for line in block.splitlines():
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            d.setdefault(k.strip(), v.strip())
    return d


def _num(d, k, default=1.0):
    try:
        v = float(re.match(r"-?[\d.]+", d[k]).group())
    except (KeyError, AttributeError, ValueError):
        return default
    return v if v else default


def _dice(s):
    m = re.match(r"(\d+)d(\d+)(?:\+(\d+))?", s or "")
    return (int(m.group(1)), int(m.group(2)), int(m.group(3) or 0)) if m else (1, 1, 0)


def _avg(s):
    n, sides, k = _dice(s)
    return n * (sides + 1) / 2 + k


def _g(*pairs):
    s = 1.0
    for x, w in pairs:
        s *= max(x, 1e-6) ** w
    return s


# stat -> weight; "1/x" means lower is better
SCORE = {
    "maindrive": lambda d: _g((_num(d, "thrust"), .75), (1 / _num(d, "highpowerusage"), .1), (1 / _num(d, "emissionhighstrength"), .15)),
    "generators": lambda d: _g((_num(d, "generationrate"), .8), (1 / _num(d, "emissionstrength"), .2)),
    "batteries": lambda d: _g((_num(d, "maxpowercontent"), .85), (1 + 5 * _num(d, "generationrate", 0.0), .15)),
    "solar": lambda d: _g((_num(d, "generationrate"), .75), (_num(d, "range"), .25)),
    "rcs": lambda d: _g((_num(d, "rotationrate"), .7), (1 / _num(d, "highpowerusage"), .3)),
    "jumpdrive": lambda d: _g((_num(d, "jumpdistance"), .45), (1 / _num(d, "spinuptime"), .25), (1 / _num(d, "calctime"), .1),
                              (1 / _num(d, "highpowerusage"), .2)),
    "weapons": lambda d: _g((_num(d, "tubes") / _num(d, "spinuptime"), .75), (1 / _num(d, "highpowerusage"), .15),
                            (1 / _num(d, "normalpowerusage"), .1)),
    "pds": lambda d: _g(((1 / _dice(d.get("hitchance"))[1]) / _num(d, "reloadtime"), .5), (_num(d, "range"), .3),
                        (1 / _num(d, "highpowerusage"), .2)),
    "cms": lambda d: _g((_num(d, "tubes") / _num(d, "reloadtime"), .8), (1 / _num(d, "normalpowerusage"), .2)),
    "comms": lambda d: _g((1 / _num(d, "synctime"), .6), (1 / _num(d, "highpowerusage"), .2), (1 / _num(d, "normalpowerusage"), .2)),
    "hackers": lambda d: _g((_num(d, "hackrange"), .4), (1 / _num(d, "hacktime"), .4), (1 / _num(d, "highpowerusage"), .2)),
    # fewer ghosts (a longer ghost timer) and a faster analysis are better
    "sensors": lambda d: _g((_num(d, "sensorquality"), .4), (_avg(d.get("ghosttimer")), .25), (1 / _avg(d.get("analysistime")), .2),
                            (1 / _num(d, "normalpowerusage"), .15)),
    "arms": lambda d: _g((1 / _num(d, "grappletime"), .75), (1 / _num(d, "highpowerusage"), .25)),
    # every nav computer plots in the same time; what differs is the screen (only NavMap3 shows nebula kinds apart) and the power draw
    "navcom": lambda d: _g(({"NavMap3": 1.5, "NavMap2": 1.0, "NavMap1": 0.8}.get(d.get("uiprefix"), 1.0), .5),
                           (1 / _num(d, "normalpowerusage"), .5)),
}


def plan_file(kind, text, strength=STRENGTH):
    """{module id: new basevalue} for one modules_<kind>.txt. Modules with no basevalue (never sold) are skipped."""
    score = SCORE.get(kind)
    if score is None:
        return {}
    mods = [(d["id"], _num(d, "basevalue", 0.0), score(d)) for d in (_kv(m.group(1)) for m in _blocks(text))
            if "id" in d and _num(d, "basevalue", 0.0) > 0]
    if len(mods) < 2:
        return {}
    mean_s = sum(s for _, _, s in mods) / len(mods)
    mean_b = sum(b for _, b, _ in mods) / len(mods)
    raw = {i: mean_b * min(CEILING, max(FLOOR, (s / mean_s) ** strength)) for i, _, s in mods}
    k = mean_b / (sum(raw.values()) / len(raw))
    return {i: int(round(v * k / ROUND_TO)) * ROUND_TO for i, v in raw.items()}


def rewrite(kind, text, strength=STRENGTH):
    """Returns (new text, {id: (old, new)}); only `basevalue=` lines of the planned modules change."""
    new = plan_file(kind, text, strength)
    changes = {}

    def fix(m):
        d = _kv(m.group(1))
        i = d.get("id")
        if i not in new:
            return m.group(0)
        body, n = re.subn(r"^([ \t]*basevalue=)\d+", lambda b: f"{b.group(1)}{new[i]}", m.group(0), count=1, flags=re.M)
        if n:
            changes[i] = (int(_num(d, "basevalue", 0)), new[i])
        return body
    return re.sub(r"begin module\b(.*?)end module", fix, text, flags=re.S), changes


def apply(assets_dir, mod_dir, strength=STRENGTH, log=print):
    """Reads each modules_*.txt (the mod folder's copy if a data fix already wrote one, else the game's), writes the
    repriced file into the mod folder. Returns the number of modules repriced."""
    assets_dir, mod_dir = Path(assets_dir), Path(mod_dir)
    total = 0
    for kind in SCORE:
        name = f"modules_{kind}.txt"
        src = mod_dir / name if (mod_dir / name).is_file() else assets_dir / name
        if not src.is_file():
            continue
        text = src.read_text(encoding="utf-8", errors="surrogateescape")
        out, changes = rewrite(kind, text, strength)
        if changes:
            (mod_dir / name).write_text(out, encoding="utf-8", errors="surrogateescape")
            total += len(changes)
    return total
