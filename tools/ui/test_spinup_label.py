#!/usr/bin/env python3
"""Check of the torpedo "spinning up" state label fix (needs `pip install pefile`).

    python3 tools/ui/test_spinup_label.py <game dir>/ois.exe

The two weapon-state texts (short, 0x4F1192; advanced, 0x4F1758) pushed "`0idle" for a spinning-up tube.  Patched: each
site pushes its own string (checked: lives in .ptch, right length, NUL-terminated) and the push keeps its base
relocation (so the address is rebased under ASLR); the genuine "idle" pushes (not armed) are untouched.
"""
import struct
import sys

import pefile

SITES = ((0x4F1192, b"`!spinning"), (0x4F1758, b"`!spinning up"))
IDLE_PUSHES = (0x4F11B0, 0x4F178F)           # `push 6 ; push "`0idle"` for the not-armed case, must stay as it was
IDLE_VA = 0x6188F0


def main():
    exe = sys.argv[1]
    pe = pefile.PE(exe, fast_load=True)
    pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_BASERELOC"]])
    raw = open(exe, "rb").read()
    base = pe.OPTIONAL_HEADER.ImageBase
    relocs = {e.rva for r in pe.DIRECTORY_ENTRY_BASERELOC for e in r.entries if e.type == 3}

    def read(va, n):
        for s in pe.sections:
            a = base + s.VirtualAddress
            if a <= va < a + s.SizeOfRawData:
                o = s.PointerToRawData + va - a
                return raw[o:o + n], s.Name.rstrip(b"\0")
        return b"", b""

    bad, patched = 0, False
    for va, text in SITES:
        code, _ = read(va, 7)
        if code == bytes.fromhex("6A0668F0886100"):
            print(f"  stock: {va:#x} still pushes the 'idle' string")
            continue
        patched = True
        ok = code[0] == 0x6A and code[2] == 0x68 and code[1] == len(text)
        str_va = struct.unpack_from("<I", code, 3)[0]
        s, sec = read(str_va, len(text) + 1)
        ok = ok and s == text + b"\0" and sec == b".ptch" and (va + 3 - base) in relocs
        bad += not ok
        print(("  PASS " if ok else "  FAIL ") + f"{va:#x}: pushes {len(text)} bytes of {s[:-1]!r} from {sec.decode()} at {str_va:#x}, "
              f"relocation kept={(va + 3 - base) in relocs}")
    for va in IDLE_PUSHES:
        code, _ = read(va, 7)
        ok = code == bytes.fromhex("6A0668F0886100") and (va + 3 - base) in relocs
        bad += not ok
        print(("  PASS " if ok else "  FAIL ") + f"{va:#x}: the not-armed 'idle' push is unchanged")
    print("exe is not patched with this fix" if not patched else ("all spin-up label checks pass" if not bad else f"{bad} FAILED"))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
