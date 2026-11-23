#!/usr/bin/env python3
"""Layout check for --ui-extras (no game needed beyond the installed mod folder).

    python3 tools/ui/check_extras.py <game dir>/ObjectsInSpace/mods/oisbugfix

Finds the sensors AUTO button on the Ceres/Proxima, Enceladus and Remora sensor screens and checks that it lies inside the
screen and overlaps no other button, display, list or text on that screen, and that the depot buttons added to the Enceladus
docking screen are inside it and overlap no other button.  Buttons are 12 units tall.
"""
import re
import sys
from pathlib import Path


def screens(path):
    text = Path(path).read_text()
    for m in re.finditer(r"begin screen(.*?)end screen", text, re.S):
        block = m.group(1)
        name = re.search(r"shortname=(\S+)", block).group(1)
        width, height = (int(re.search(rf"{k}=(\d+)", block).group(1)) for k in ("width", "height"))
        widgets = []
        for line in block.splitlines():
            line = line.strip()
            b = re.match(r"^(button|greyedbutton)=(\d+),(\d+),(\d+),", line)
            if b:
                widgets.append((int(b.group(2)), int(b.group(3)), int(b.group(4)), 12, line))
                continue
            r = re.match(r"^(sensordisplay|sensorselect|sensorwaveform|textfield|border|data|text)=(\d+),(\d+),(\d+),(\d+)", line)
            if r:
                widgets.append(tuple(int(v) for v in r.groups()[1:]) + (line,))
        yield name, width, height, widgets


def overlap(a, b):
    return a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3]


def main():
    mod = Path(sys.argv[1])
    bad = 0
    for fname, screen in (("ui_ceres.txt", "c_sensors"), ("ui_enceladus.txt", "e_sensors"), ("ui_remora.txt", "r_sensors")):
        for name, w, h, widgets in screens(mod / fname):
            if name != screen:
                continue
            autos = [x for x in widgets if "SENSOR_SET_AUTO" in x[4] or "SENSOR_UNSET_AUTO" in x[4]]
            if not autos:
                print(f"  FAIL {fname}:{name}: no AUTO button"); bad += 1; continue
            hits = [x[4][:50] for x in widgets if x not in autos and any(overlap(a, x) for a in autos)]
            inside = all(a[0] + a[2] <= w and a[1] + a[3] <= h for a in autos)
            ok = inside and not hits
            bad += not ok
            print(f"  {'PASS' if ok else 'FAIL'} {fname}:{name} AUTO at x={autos[0][0]} y={autos[0][1]} w={autos[0][2]} "
                  f"(screen {w}x{h})" + (f", overlaps {hits}" if hits else ""))
    for name, w, h, widgets in screens(mod / "ui_enceladus.txt"):
        if name != "e_docking":
            continue
        depot = [x for x in widgets if "DEPOT" in x[4] and x[4].startswith(("button", "greyedbutton"))]
        others = [x for x in widgets if x[4].startswith(("button", "greyedbutton")) and x not in depot]
        inside = all(x[0] + x[2] <= w and x[1] + x[3] <= h for x in depot)
        hits = [x[4][:40] for d in depot for x in others if overlap(d, x)]
        ok = bool(depot) and inside and not hits
        bad += not ok
        print(f"  {'PASS' if ok else 'FAIL'} ui_enceladus.txt:{name}: {len(depot)} depot button lines, inside screen: {inside}"
              + (f", overlap with {hits}" if hits else ", no overlap with the other buttons"))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
