#!/usr/bin/env python3
"""Emulation test for the mail-terminal fix (needs `pip install unicorn pefile`).

    python3 tools/mail/test_mail_select.py <game dir>/ois.exe

Runs ComputerSystem::selectedEmail(int) (0x4B64A0) on a fake terminal holding three emails.  Indexes 0..2 must reach
renderEmail with that email; -1 must go to renderEmails (back to the list); any other index (3, 99, -2, 0x80000000)
must return without rendering anything and without storing the index.  The stock exe renders garbage for those (FAIL).
"""
import struct
import sys

import pefile
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ECX, UC_X86_REG_EIP, UC_X86_REG_ESP

FN, RENDER_EMAIL, RENDER_LIST, G_GAMEDATA = 0x4B64A0, 0x4B4C90, 0x4B58A0, 0x65D704
THIS, VEC, GD, RET = 0x10000000, 0x10001000, 0x10002000, 0x10004000
EMAILS = (0xAAAA0001, 0xBBBB0002, 0xCCCC0003)


def run(exe, index):
    pe = pefile.PE(exe, fast_load=True)
    raw = open(exe, "rb").read()
    uc = Uc(UC_ARCH_X86, UC_MODE_32)
    base = pe.OPTIONAL_HEADER.ImageBase
    for sec in pe.sections:
        size = (max(sec.Misc_VirtualSize, sec.SizeOfRawData) + 0xFFF) & ~0xFFF
        uc.mem_map(base + sec.VirtualAddress, size)
        uc.mem_write(base + sec.VirtualAddress, raw[sec.PointerToRawData:sec.PointerToRawData + sec.SizeOfRawData])
    uc.mem_map(0x10000000, 0x10000)
    uc.mem_write(THIS + 0xC, struct.pack("<III", VEC, VEC + 12, VEC + 12))      # begin, end, capacity
    uc.mem_write(THIS, struct.pack("<i", -77))                                  # the "selected" slot
    uc.mem_write(VEC, struct.pack("<III", *EMAILS))
    uc.mem_write(G_GAMEDATA, struct.pack("<I", GD))
    uc.mem_write(GD + 0x12C, struct.pack("<I", 0x12345678))
    esp = 0x10008000
    uc.mem_write(esp, struct.pack("<Ii", RET, index))
    uc.reg_write(UC_X86_REG_ESP, esp)
    uc.reg_write(UC_X86_REG_ECX, THIS)
    seen = {}

    def hook(u, addr, size, _):
        if addr in (RENDER_EMAIL, RENDER_LIST):
            sp = u.reg_read(UC_X86_REG_ESP)
            seen["call"] = ("email" if addr == RENDER_EMAIL else "list",
                            struct.unpack("<II", bytes(u.mem_read(sp + 4, 8))) if addr == RENDER_EMAIL else None)
            u.emu_stop()
    uc.hook_add(UC_HOOK_CODE, hook, begin=RENDER_LIST, end=RENDER_EMAIL + 1)
    uc.emu_start(FN, RET, count=200)
    stored = struct.unpack("<i", bytes(uc.mem_read(THIS, 4)))[0]
    return seen.get("call"), stored


def main():
    exe = sys.argv[1]
    probe = pefile.PE(exe, fast_load=True)
    data = open(exe, "rb").read()
    patched = data[probe.get_offset_from_rva(0x4B64C4 - probe.OPTIONAL_HEADER.ImageBase)] == 0xE9
    bad = 0
    for idx in (0, 1, 2):
        call, stored = run(exe, idx)
        ok = call == ("email", (0x12345678, EMAILS[idx])) and stored == idx
        bad += not ok
        print(f"  {'PASS' if ok else 'FAIL'} index {idx}: renders email {call[1][1]:#x}" if call and call[0] == "email" else f"  FAIL index {idx}: {call}")
    call, stored = run(exe, -1)
    ok = call and call[0] == "list" and stored == -77
    bad += not ok
    print(f"  {'PASS' if ok else 'FAIL'} index -1: back to the list")
    for idx in (3, 4, 99, -2, -0x80000000):
        call, stored = run(exe, idx)
        ok = call is None and stored == -77
        bad += not ok
        print(f"  {'PASS' if ok else 'FAIL'} index {idx}: {'ignored, nothing rendered' if call is None else 'renders ' + hex(call[1][1])}")
    print("\nall checks passed" if not bad and patched else
          ("exe is not patched with this fix" if not patched else f"\n{bad} check(s) failed"))
    sys.exit(0 if patched and not bad else 1)


if __name__ == "__main__":
    main()
