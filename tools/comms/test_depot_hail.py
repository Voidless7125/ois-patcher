#!/usr/bin/env python3
"""Emulation test for "hailing a depot crashes" (needs `pip install unicorn pefile`).

    python3 tools/comms/test_depot_hail.py <game dir>/ois.exe

Runs the ship-type test at the top of PrivateCommsManager::switchTo (0x43116F) for each ship type and reports where it
goes.  Expected after the fix:  type 0 (ship) -> the conversation path (0x4311B3);  type 1 (starbase) and type 3
(depot) -> the station comms path (0x431174, which starts by storing 1 as the screen mode);  type 2 (jumpgate) -> the
conversation path, as before.  The stock exe sends type 3 down the conversation path (FAIL for the depot).
"""
import sys

import pefile
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_ESP

SITE, STATION, OTHER = 0x43116F, 0x431174, 0x4311B3


def route(exe, ship_type):
    pe = pefile.PE(exe, fast_load=True)
    raw = open(exe, "rb").read()
    uc = Uc(UC_ARCH_X86, UC_MODE_32)
    base = pe.OPTIONAL_HEADER.ImageBase
    for sec in pe.sections:
        sz = (max(sec.Misc_VirtualSize, sec.SizeOfRawData) + 0xFFF) & ~0xFFF
        uc.mem_map(base + sec.VirtualAddress, sz)
        uc.mem_write(base + sec.VirtualAddress, raw[sec.PointerToRawData:sec.PointerToRawData + sec.SizeOfRawData])
    uc.mem_map(0x10000000, 0x10000)
    uc.reg_write(UC_X86_REG_ESP, 0x1000F000)
    uc.reg_write(UC_X86_REG_EAX, ship_type)
    seen = {}

    def stop(u, a, s, _):
        seen["va"], seen["eax"] = a, u.reg_read(UC_X86_REG_EAX)
        u.emu_stop()
    uc.hook_add(UC_HOOK_CODE, stop, begin=STATION, end=STATION)
    uc.hook_add(UC_HOOK_CODE, stop, begin=OTHER, end=OTHER)
    uc.emu_start(SITE, 0, count=50)
    return seen["va"], seen["eax"]


def main():
    exe = sys.argv[1]
    want = {0: OTHER, 1: STATION, 2: OTHER, 3: STATION}
    bad = 0
    for t, target in want.items():
        va, eax = route(exe, t)
        ok = va == target and (eax == 1 if target == STATION else eax == t)
        bad += not ok
        print(("  PASS " if ok else "  FAIL ") + f"type {t}: goes to {va:#x} ({'station comms' if va == STATION else 'conversation path'})"
              f", EAX={eax}")
    print("all depot-hail checks pass" if not bad else f"{bad} FAILED (stock exe: the depot takes the conversation path)")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
