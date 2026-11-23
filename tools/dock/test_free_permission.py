#!/usr/bin/env python3
"""Emulation test for "free starbases ask for undocking permission" (needs `pip install unicorn pefile`).

    python3 tools/dock/test_free_permission.py <game dir>/ois.exe

Runs SpaceStation::shipHasUndockingClearance (0x51C350) and SpaceStation::requestUndockingClearance (0x51B9D0) on a
fake station.  Expected after the fix, for a type-1 starbase with dockcost 0:
  * no request on file            -> no clearance (the Request permission button appears)
  * request on file, state 0      -> no clearance;  requesting turns it into state 2
  * request on file, state 2      -> clearance
A type-3 station (depot) with dockcost 0, and any station with a fee, behave exactly as before.
The stock exe answers "clearance" for every dockcost-0 case (FAIL on the first three).
"""
import struct
import sys

import pefile
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_ESP

HAS, REQ = 0x51C350, 0x51B9D0
STATION, CLASS, SHIP, VEC, REC, RET = 0x10001000, 0x10002000, 0x10003000, 0x10004000, 0x10005000, 0x10009000


def run(exe, fn, dockcost, stype, state, req_flag=False):
    pe = pefile.PE(exe, fast_load=True)
    raw = open(exe, "rb").read()
    uc = Uc(UC_ARCH_X86, UC_MODE_32)
    base = pe.OPTIONAL_HEADER.ImageBase
    for sec in pe.sections:
        sz = (max(sec.Misc_VirtualSize, sec.SizeOfRawData) + 0xFFF) & ~0xFFF
        uc.mem_map(base + sec.VirtualAddress, sz)
        uc.mem_write(base + sec.VirtualAddress, raw[sec.PointerToRawData:sec.PointerToRawData + sec.SizeOfRawData])
    uc.mem_map(0x10000000, 0x20000)
    uc.mem_write(STATION + 0x3DC, struct.pack("<I", dockcost))
    uc.mem_write(STATION + 0x254, struct.pack("<I", CLASS))
    uc.mem_write(CLASS + 0x158, struct.pack("<I", stype))
    uc.mem_write(STATION + 0x390, struct.pack("<I", 0))              # no faction
    if state is not None:
        uc.mem_write(VEC, struct.pack("<I", REC))                     # one request: {ship, ?, state}
        uc.mem_write(REC, struct.pack("<III", SHIP, 0, state))
        uc.mem_write(STATION + 0x3C4, struct.pack("<II", VEC, VEC + 4))
    uc.reg_write(UC_X86_REG_ECX, STATION)
    sp = 0x1000F000
    args = [SHIP, 1 if req_flag else 0] if fn == REQ else [SHIP]
    for a in reversed(args):
        sp -= 4
        uc.mem_write(sp, struct.pack("<I", a))
    sp -= 4
    uc.mem_write(sp, struct.pack("<I", RET))
    uc.reg_write(UC_X86_REG_ESP, sp)
    uc.mem_write(RET, b"\x90")
    uc.hook_add(UC_HOOK_CODE, lambda u, a, s, _: u.emu_stop(), begin=RET, end=RET)
    uc.emu_start(fn, 0, count=400)
    st = struct.unpack("<I", uc.mem_read(REC + 8, 4))[0] if state is not None else None
    return uc.reg_read(UC_X86_REG_EAX) & 0xFF, st


def main():
    exe = sys.argv[1]
    pe = pefile.PE(exe, fast_load=True)
    patched = open(exe, "rb").read()[pe.get_offset_from_rva(0x51C35A - pe.OPTIONAL_HEADER.ImageBase)] == 0x90
    cases = (
        ("free starbase, no request", HAS, (0, 1, None), 0),
        ("free starbase, request state 0", HAS, (0, 1, 0), 0),
        ("free starbase, request state 2", HAS, (0, 1, 2), 1),
        ("free depot (type 3), no request", HAS, (0, 3, None), 1),
        ("fee starbase, no request", HAS, (10, 1, None), 0),
        ("fee starbase, request state 2", HAS, (10, 1, 2), 1),
    )
    bad = 0
    for name, fn, (cost, typ, state), want in cases:
        got, _ = run(exe, fn, cost, typ, state)
        ok = got == want
        bad += not ok
        print(f"  {'PASS' if ok else 'FAIL'} {name}: clearance={got} (want {want})")
    got, st = run(exe, REQ, 0, 1, 0, False)
    ok = got == 1 and st == 2
    bad += not ok
    print(f"  {'PASS' if ok else 'FAIL'} free starbase, request undocking: returned {got}, request state {st} (want 1, 2)")
    got, st = run(exe, REQ, 10, 1, 0, False)
    ok = got == 1 and st == 2
    bad += not ok
    print(f"  {'PASS' if ok else 'FAIL'} fee starbase, request undocking: returned {got}, request state {st} (want 1, 2)")
    print("\nall checks passed" if not bad and patched else
          ("exe is not patched with this fix" if not patched else f"\n{bad} check(s) failed"))
    sys.exit(0 if patched and not bad else 1)


if __name__ == "__main__":
    main()
