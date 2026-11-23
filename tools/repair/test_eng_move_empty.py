#!/usr/bin/env python3
"""Emulation test for the repair-screen fix (needs `pip install unicorn pefile`).

    python3 tools/repair/test_eng_move_empty.py <game dir>/ois.exe

Runs the two socket-class loads of ShipInterface::doEngMoveComponent (0x4E105E) with the source component present and the
destination (a) a matching component, (b) a component of another socket class, (c) null -- the slot of a part that has just
been unmounted.  Expected: (a) goes on to the swap (0x4E107C), (b) and (c) take the "Dragging component to an invalid slot."
exit (0x4E1072).  The stock exe faults on (c) (FAIL).
"""
import struct
import sys

import pefile
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE, UcError
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_ESP

SITE, REJECT, SWAP = 0x4E105E, 0x4E1072, 0x4E107C
A, B, CA, CB = 0x10000100, 0x10000200, 0x10000300, 0x10000400


def run(exe, dest, dest_class):
    pe = pefile.PE(exe, fast_load=True)
    raw = open(exe, "rb").read()
    uc = Uc(UC_ARCH_X86, UC_MODE_32)
    base = pe.OPTIONAL_HEADER.ImageBase
    for sec in pe.sections:
        sz = (max(sec.Misc_VirtualSize, sec.SizeOfRawData) + 0xFFF) & ~0xFFF
        uc.mem_map(base + sec.VirtualAddress, sz)
        uc.mem_write(base + sec.VirtualAddress, raw[sec.PointerToRawData:sec.PointerToRawData + sec.SizeOfRawData])
    uc.mem_map(0x10000000, 0x10000)
    uc.mem_write(A + 4, struct.pack("<I", CA))
    uc.mem_write(CA + 0x80, struct.pack("<I", 7))
    if dest:
        uc.mem_write(B + 4, struct.pack("<I", CB))
        uc.mem_write(CB + 0x80, struct.pack("<I", dest_class))
    uc.reg_write(UC_X86_REG_EAX, A)
    uc.reg_write(UC_X86_REG_EBX, B if dest else 0)
    uc.reg_write(UC_X86_REG_ESP, 0x10008000)
    out = {}

    def hook(u, addr, size, _):
        out["end"] = addr
        u.emu_stop()
    uc.hook_add(UC_HOOK_CODE, hook, begin=REJECT, end=REJECT)
    uc.hook_add(UC_HOOK_CODE, hook, begin=SWAP, end=SWAP)
    try:
        uc.emu_start(SITE, 0, count=50)
    except UcError:
        out["end"] = "fault"
    return out.get("end")


def main():
    exe = sys.argv[1]
    pe = pefile.PE(exe, fast_load=True)
    patched = open(exe, "rb").read()[pe.get_offset_from_rva(SITE - pe.OPTIONAL_HEADER.ImageBase)] == 0xE9
    bad = 0
    for name, dest, cls, want in (("matching component", True, 7, SWAP), ("other socket class", True, 9, REJECT),
                                  ("empty slot (null)", False, 0, REJECT)):
        got = run(exe, dest, cls)
        ok = got == want
        bad += not ok
        print(f"  {'PASS' if ok else 'FAIL'} destination {name}: " + ("swap" if got == SWAP else "refused" if got == REJECT else str(got)))
    print("\nall checks passed" if not bad and patched else
          ("exe is not patched with this fix" if not patched else f"\n{bad} check(s) failed"))
    sys.exit(0 if patched and not bad else 1)


if __name__ == "__main__":
    main()
