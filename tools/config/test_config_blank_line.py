#!/usr/bin/env python3
"""Emulation test for the config-log fix (needs `pip install unicorn pefile`).

    python3 tools/config/test_config_blank_line.py <game dir>/ois.exe

Runs the "line is not key=value" branch of the config loader (0x4B1849) on a fake line string.  An empty line must jump
straight to the loop's next iteration (0x4B2907) with nothing logged; a non-empty line (short or heap-backed) must still
reach the log call (0x4B28FA) with the line text and the 'Unable to parse' format string pushed.  Stock exe: the empty
line is logged too (FAIL).
"""
import struct
import sys

import pefile
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EDI, UC_X86_REG_ESP

SITE, LOG, NEXT, FMT = 0x4B1849, 0x4B28FA, 0x4B2907, 0x610C48
LINE = 0x10000000


def run(exe, size, text):
    pe = pefile.PE(exe, fast_load=True)
    raw = open(exe, "rb").read()
    uc = Uc(UC_ARCH_X86, UC_MODE_32)
    base = pe.OPTIONAL_HEADER.ImageBase
    for sec in pe.sections:
        sz = (max(sec.Misc_VirtualSize, sec.SizeOfRawData) + 0xFFF) & ~0xFFF
        uc.mem_map(base + sec.VirtualAddress, sz)
        uc.mem_write(base + sec.VirtualAddress, raw[sec.PointerToRawData:sec.PointerToRawData + sec.SizeOfRawData])
    uc.mem_map(0x10000000, 0x10000)
    cap = 0xF if size < 16 else 0x1F
    buf = text.ljust(16, b"\0")
    if size < 16:
        uc.mem_write(LINE, buf)                      # short string: characters inline
    else:
        uc.mem_write(LINE, struct.pack("<I", LINE + 0x1000))
        uc.mem_write(LINE + 0x1000, text + b"\0")    # long string: heap pointer
    uc.mem_write(LINE + 0x10, struct.pack("<II", size, cap))
    uc.reg_write(UC_X86_REG_EDI, LINE)
    uc.reg_write(UC_X86_REG_ESP, 0x10008000)
    out = {}

    def hook(u, addr, sz, _):
        out["end"] = addr
        out["stack"] = struct.unpack("<II", bytes(u.mem_read(u.reg_read(UC_X86_REG_ESP), 8)))
        u.emu_stop()
    uc.hook_add(UC_HOOK_CODE, hook, begin=LOG, end=LOG)
    uc.hook_add(UC_HOOK_CODE, hook, begin=NEXT, end=NEXT)
    uc.emu_start(SITE, 0, count=100)
    return out


def main():
    exe = sys.argv[1]
    pe = pefile.PE(exe, fast_load=True)
    patched = open(exe, "rb").read()[pe.get_offset_from_rva(SITE - pe.OPTIONAL_HEADER.ImageBase)] == 0xE9
    bad = 0
    o = run(exe, 0, b"")
    ok = o["end"] == NEXT
    bad += not ok
    print(f"  {'PASS' if ok else 'FAIL'} empty line: {'skipped, nothing logged' if ok else 'logged'}")
    for size, text in ((5, b"abcde"), (40, b"x" * 40)):
        o = run(exe, size, text)
        ok = o["end"] == LOG and o["stack"][0] == FMT and o["stack"][1] in (LINE, LINE + 0x1000)
        bad += not ok
        print(f"  {'PASS' if ok else 'FAIL'} {size}-char line: still logged as unparseable")
    print("\nall checks passed" if not bad and patched else
          ("exe is not patched with this fix" if not patched else f"\n{bad} check(s) failed"))
    sys.exit(0 if patched and not bad else 1)


if __name__ == "__main__":
    main()
