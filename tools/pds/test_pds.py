#!/usr/bin/env python3
"""Emulation test of the point-defence torpedo fix (needs `pip install unicorn pefile`).

    python3 tools/pds/test_pds.py <game dir>/ois.exe      (client only)

Drives the patched candidate filter, target selection and damage delivery against a small synthetic
sector built from the field offsets the real code uses.  Nothing here runs the game.
"""
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))
import emu as tp
from unicorn.x86_const import UC_X86_REG_EBP, UC_X86_REG_EBX, UC_X86_REG_EDI, UC_X86_REG_ESI

SELECT_CALL = 0x4AF752          # `call getShipWithinDistance` in the PDS branch
DAMAGE_SITE = SELECT_CALL + 0x16D


def site_target(emu, va, opcode_len):
    off = emu.r32(va + opcode_len)
    off = off - (1 << 32) if off & 0x80000000 else off
    return va + opcode_len + 4 + off


def main():
    emu = tp.Emu(sys.argv[1])
    emu.efficiency = 100
    emu.locate_dist_hooks()
    failures = []

    def check(name, cond, detail=""):
        print(("  PASS " if cond else "  FAIL ") + name + (f"   {detail}" if detail and not cond else ""))
        if not cond:
            failures.append(name)

    select_cave = site_target(emu, SELECT_CALL, 1)
    f32 = lambda v: struct.unpack("<I", struct.pack("<f", v))[0]

    print("selection (weapons first; ships by the stock IFF-off rule; own and destroyed weapons never)")
    sec = emu.make_world()
    me = emu.make_ship(sec, 100.0, 100.0, rego="ME")
    station = emu.make_ship(sec, 101.0, 100.0, vtype=1, iff_on=False)
    no_iff = emu.make_ship(sec, 102.0, 100.0, iff_on=False, rego="Dark")
    trader = emu.make_ship(sec, 103.0, 100.0, iff_on=True, rego="Trader")
    own_torp = emu.make_ship(sec, 100.2, 100.0, vtype=4, launcher=me)
    dead_torp = emu.make_ship(sec, 100.3, 100.0, vtype=4, launcher=0x1234, destroyed=True)
    enemy_torp = emu.make_ship(sec, 104.0, 100.0, vtype=4, launcher=0x1234)
    far_ship = emu.make_ship(sec, 190.0, 100.0, iff_on=False)
    emu.ships = [me, station, no_iff, trader, own_torp, dead_torp, enemy_torp, far_ship]
    emu.commit()

    def pick(rng=5.0):
        args = [7, me, 1, f32(100.0), f32(100.0)]
        keep = {UC_X86_REG_EBX: 0x11111111, UC_X86_REG_ESI: 0x22222222, UC_X86_REG_EDI: 0x33333333,
                UC_X86_REG_EBP: 0x44444444}
        eax, popped = emu.call_stdcall(select_cave, args, xmm2=rng, regs=keep)
        pick.preserved = all(emu.uc.reg_read(r) == v for r, v in keep.items())
        return eax, popped

    got, popped = pick()
    check("a hostile torpedo is chosen before a nearer ship", got == enemy_torp, f"got {got:#x}")
    check("callee pops exactly its 5 arguments (stdcall ret 0x14)", popped == 0x14, f"popped {popped:#x}")
    check("EBX/ESI/EDI/EBP are preserved", pick.preserved)
    emu.ships.remove(enemy_torp)
    emu.commit()
    got, _ = pick()
    check("then a ship with its IFF off (stock rule), not the station, own or destroyed torpedo, or IFF-on ship",
          got == no_iff or got == station, f"got {got:#x}")
    emu.ships.remove(station)
    emu.commit()
    got, _ = pick()
    check("the ship with its IFF off", got == no_iff, f"got {got:#x}")
    emu.ships.remove(no_iff)
    emu.commit()
    got, _ = pick()
    check("an IFF-on ship, our own torpedo and a destroyed one are never chosen", got == 0, f"got {got:#x}")
    got, _ = pick(rng=100.0)
    check("a larger range reaches the far IFF-off ship", got == far_ship, f"got {got:#x}")

    emu.ships = [me, station, trader]
    emu.commit()
    gswd = tp.GSWD
    eax, _ = emu.call_stdcall(gswd, [7, me, 0, f32(100.0), f32(100.0)], xmm2=5.0)
    check("flag 0 (every other caller) still returns the first ship in range", eax == station, f"got {eax:#x}")

    print("damage delivery")
    damage_cave = site_target(emu, DAMAGE_SITE + 1, 1)
    emu.ships = [me]
    torp = emu.make_ship(sec, 0, 0, vtype=4, launcher=0x1234)
    ship = emu.make_ship(sec, 0, 0, vtype=0)
    stub = 0x7FEFFE00
    emu.uc.mem_write(stub, b"\xc2\x10\x00")              # ret 0x10: stands in for Ship::damage
    emu.w32(emu.r32(ship) + 0xC, stub)
    emu.stops[stub] = "ship-damage"
    emu.call_stdcall(damage_cave, [45, 0x42C80000, 2, me], regs={UC_X86_REG_EDI: torp})
    check("a locked torpedo is destroyed", emu.rb(torp + 0x3CC) == 1 and emu.stopped_at == "returned")
    emu.stopped_at = None
    emu.call_stdcall(damage_cave, [45, 0x42C80000, 2, me], regs={UC_X86_REG_EDI: ship})
    check("a ship still goes through Ship::damage", emu.stopped_at == "ship-damage", emu.stopped_at)
    check("...and is not flagged destroyed", emu.rb(ship + 0x3CC) == 0)
    print("all point-defence checks pass" if not failures else f"{len(failures)} FAILED")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
