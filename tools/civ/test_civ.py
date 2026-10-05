#!/usr/bin/env python3
"""CPU-emulation test of the --civilians-comply changes (needs `pip install unicorn pefile`).

    python3 ois_patcher.py <game dir> --civilians-comply
    python3 tools/civ/test_civ.py <game dir>/ois.exe            # or ois_server.exe --server

Checks, on the patched exe: the chance table; that the demand no longer records the
demander on the civilian's list (and execution still reaches the code after it); and
that the torpedo cave treats only YOUR live torpedoes near the civilian as "seen".
"""
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "pds"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
import test_pds as tp
import ois_patcher
from unicorn.x86_const import (UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_ECX, UC_X86_REG_EDI,
                               UC_X86_REG_ESI, UC_X86_REG_EBP, UC_X86_REG_ESP)

SERVER = "--server" in sys.argv
FUNC = 0x5043F0 if SERVER else 0x504B10
SEEN, CONTINUE = FUNC + 0x346, FUNC + 0x2AC


def main():
    exe = [a for a in sys.argv[1:] if not a.startswith("--")][0]
    emu = tp.Emu.__new__(tp.Emu)
    tp.GSWD = 0  # unused here
    tp.Emu.__init__(emu, exe)
    emu.dist_hooks = (0, 0)
    fails = []

    def check(name, cond, detail=""):
        print(("  PASS " if cond else "  FAIL ") + name + (f"   {detail}" if detail and not cond else ""))
        if not cond:
            fails.append(name)

    print("chance table")
    raw = bytes(emu.uc.mem_read(FUNC + 0x11E, 7))
    table = struct.unpack_from("<I", raw, 3)[0]
    vals = struct.unpack("<4I", bytes(emu.uc.mem_read(table, 16)))
    check("dropCargoChance is {100, 100, 90, 60}", vals == (100, 100, 90, 60), str(vals))

    print("demand no longer blocks hailing")
    sec = emu.alloc(0x200)
    emu.w32(sec, 7)
    npc = emu.make_ship(sec, 100.0, 100.0, rego="NPC")
    player = emu.make_ship(sec, 120.0, 100.0, rego="PLAYER")
    beh = emu.alloc(0x200)
    emu.w32(beh + 0x6C, npc)
    emu.w32(beh + 0x74, 3)
    emu.w32(npc + 0x35C, 0)                       # the list the civilian keeps of ships that demanded
    emu.w32(npc + 0x360, 0)
    emu.w32(npc + 0x364, 0)
    reached = FUNC + 0x7D
    emu.stops[reached] = "after-list"
    emu.stopped_at = None
    emu.w32(0x65700C, 0)
    emu.call_stdcall(FUNC, [player], ecx=beh)
    check("execution reaches the code after the list update", emu.stopped_at == "after-list", emu.stopped_at)
    check("the civilian's list is still empty (end pointer untouched)", emu.r32(npc + 0x360) == 0)
    check("[EBP-0x30] still holds the demander's registration pointer",
          emu.r32(emu.uc.reg_read(UC_X86_REG_EBP) - 0x30) == player + 0x238)

    print("a live torpedo of yours counts as seen")
    cave = emu.r32(FUNC + 0x2A4 + 1)
    cave = (FUNC + 0x2A4 + 5 + (cave - (1 << 32) if cave & 0x80000000 else cave)) & 0xFFFFFFFF
    emu.stops[SEEN], emu.stops[CONTINUE] = "seen", "continue"
    frame = emu.alloc(0x100) + 0x80
    emu.w32(frame + 8, player)
    emu.w32(frame - 0x14, 15)                     # the base chance computed earlier

    def run(ships):
        for s in ships:
            pass
        emu.w32(sec + 0xCC, 0)
        arr = emu.alloc(4 * (len(ships) + 1))
        for i, s in enumerate(ships):
            emu.w32(arr + 4 * i, s)
        emu.w32(sec + 0xCC, arr)
        emu.w32(sec + 0xD0, arr + 4 * len(ships))
        emu.w32(player + 0x24, sec)
        emu.stopped_at = None
        emu.call_stdcall(cave, [], regs={UC_X86_REG_EBP: frame, UC_X86_REG_ESI: beh})
        return emu.stopped_at, emu.uc.reg_read(UC_X86_REG_EBX), emu.uc.reg_read(UC_X86_REG_EDI)

    mine_near = emu.make_ship(sec, 180.0, 100.0, vtype=4, launcher=player)
    mine_far = emu.make_ship(sec, 600.0, 100.0, vtype=4, launcher=player)
    theirs = emu.make_ship(sec, 110.0, 100.0, vtype=4, launcher=0x9999)
    dead = emu.make_ship(sec, 105.0, 100.0, vtype=4, launcher=player, destroyed=True)
    ship = emu.make_ship(sec, 105.0, 100.0, vtype=0)
    where, ebx, edi = run([ship, theirs, dead, mine_far])
    check("no live torpedo of yours near: carry on unchanged (EBX = base chance, EDI = 100)",
          where == "continue" and ebx == 15 and edi == 100, f"{where} ebx={ebx} edi={edi}")
    where, _, _ = run([ship, theirs, dead, mine_far, mine_near])
    check("your live torpedo 80 units away: 'seen'", where == "seen", where)
    where, _, _ = run([mine_near])
    check("...even if it is the only vessel", where == "seen", where)
    print()
    if fails:
        print(f"{len(fails)} FAILED: {fails}")
        sys.exit(1)
    print("all civilian changes behave")


if __name__ == "__main__":
    main()
