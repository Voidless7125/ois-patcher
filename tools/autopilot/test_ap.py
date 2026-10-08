#!/usr/bin/env python3
"""Emulation test for the autopilot overshoot fix (needs `pip install unicorn pefile`).

    python3 tools/autopilot/test_ap.py <game dir>/ois.exe     (or ois_server.exe)
"""
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))
import emu as tp
from unicorn.x86_const import (UC_X86_REG_EAX, UC_X86_REG_EBP, UC_X86_REG_EBX, UC_X86_REG_EDI, UC_X86_REG_ESP,
                               UC_X86_REG_XMM1, UC_X86_REG_XMM3)


def xmm(v):
    return int.from_bytes(struct.pack("<f", v) + b"\0" * 12, "little")


def main():
    exe = sys.argv[1]
    site = 0x516E2F if "server" in os.path.basename(exe).lower() else 0x51791F
    back = site + 0x1E
    emu = tp.Emu(exe)
    emu.dist_hooks = (0, 0)
    bad = 0

    def run(angle, vel, ship=(0.0, 0.0), wp=(100.0, 0.0)):
        sh, lst, wps = emu.alloc(0x400), emu.alloc(0x20), emu.alloc(0x40)
        emu.wd(sh + 0x28, ship[0])
        emu.wd(sh + 0x30, ship[1])
        emu.wf(sh + 0x118, vel[0])
        emu.wf(sh + 0x11C, vel[1])
        emu.w32(lst, wps)
        emu.wf(wps + 8, wp[0])
        emu.wf(wps + 0xC, wp[1])
        frame = tp.STACK_TOP - 0x3000
        emu.wf(frame - 0x10, angle)
        emu.stops.clear()
        emu.stops[back] = "back"
        emu.stopped_at = None
        for r, v in ((UC_X86_REG_EBP, frame), (UC_X86_REG_ESP, frame - 0x100), (UC_X86_REG_EBX, lst), (UC_X86_REG_EDI, sh)):
            emu.uc.reg_write(r, v)
        emu.uc.reg_write(UC_X86_REG_XMM3, xmm(1234.5))
        emu.uc.emu_start(site, 0, count=500)
        out = struct.unpack("<f", (emu.uc.reg_read(UC_X86_REG_XMM1) & 0xFFFFFFFF).to_bytes(4, "little"))[0]
        keep = struct.unpack("<f", (emu.uc.reg_read(UC_X86_REG_XMM3) & 0xFFFFFFFF).to_bytes(4, "little"))[0]
        return emu.stopped_at, out, keep

    for name, args, want in (("heading for the waypoint: retro burn, faces away", (0.0, (5.0, 0.0)), 180.0),
                             ("past it and moving away: faces the waypoint", (0.0, (-5.0, 0.0)), 0.0),
                             ("heading for it, angle wraps past 360", (200.0, (5.0, 0.0)), 20.0),
                             ("not moving: stock heading", (30.0, (0.0, 0.0)), 210.0),
                             ("moving away, angle 200", (200.0, (-5.0, 0.0)), 200.0)):
        where, out, keep = run(*args)
        ok = where == "back" and abs(out - want) < 1e-3 and keep == 1234.5
        bad += not ok
        print(("  PASS " if ok else "  FAIL ") + f"{name}: heading {out}")
    print("all autopilot checks pass" if not bad else f"{bad} FAILED")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
