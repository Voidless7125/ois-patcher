#!/usr/bin/env python3
"""Emulation test for --mechanic-armaments (needs `pip install unicorn pefile`).

    python3 tools/mech/test_mech.py <game dir>/ois.exe        (or ois_server.exe)

The four instructions that index the mechanic's armament-id table are run from the instruction to the one after it,
for every index 0..5, with every register and the flags set to recognisable values.

  patched exe : indices 0-3 give the stock ids (m10 m12 e10 td4), 4 and 5 give m6 and td8, the destination holds a
                pointer to that id, and nothing else changed (other registers, flags, ESP apart from the pushed
                value).  The two `cmp edi,4` in getArmamentStatus must now compare with 6   -> exit 0
  stock exe   : indices 0-3 give the stock ids, 4 and 5 do not exist (reported)               -> exit 1
"""
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "pds"))
import test_pds as tp
from unicorn.x86_const import (UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_ECX, UC_X86_REG_EDI, UC_X86_REG_EDX,
                               UC_X86_REG_EFLAGS, UC_X86_REG_EBP, UC_X86_REG_ESI, UC_X86_REG_ESP)

IDS = ["m10", "m12", "e10", "td4", "m6", "td8"]
REGS = {"eax": UC_X86_REG_EAX, "ebx": UC_X86_REG_EBX, "ecx": UC_X86_REG_ECX, "edx": UC_X86_REG_EDX,
        "esi": UC_X86_REG_ESI, "edi": UC_X86_REG_EDI, "ebp": UC_X86_REG_EBP}
# (site, kind, index register, destination register)
CLIENT = ((0x494E30, "push", "ebx", None), (0x4952ED, "mov", "edi", "ebx"),
          (0x4D74D6, "push", "ebx", None), (0x4E95F7, "mov", "esi", "esi"))
SERVER = ((0x494CC0, "push", "ebx", None), (0x49517D, "mov", "edi", "ebx"),
          (0x4D72B6, "push", "ebx", None), (0x4E9067, "mov", "esi", "esi"))
COMPARES_CLIENT, COMPARES_SERVER = (0x495277, 0x4953B9), (0x495107, 0x495249)
FLAG_PATTERNS = (0x0246, 0x0A97, 0x0202)           # ZF/PF, CF/AF/SF/OF mix, all clear


def cstr(emu, addr):
    out = b""
    while len(out) < 16:
        c = bytes(emu.uc.mem_read(addr, 1))
        if c == b"\0":
            break
        out += c
        addr += 1
    return out.decode("latin1")


def run_site(exe, site, kind, idx_reg, dst_reg, index, flags):
    emu = tp.Emu(exe)
    emu.dist_hooks = (0, 0)
    start = {"eax": 0xAAAA0001, "ebx": 0xBBBB0002, "ecx": 0xCCCC0003, "edx": 0xDDDD0004,
             "esi": 0xE5E50005, "edi": 0xEDED0006, "ebp": tp.STACK_TOP - 0x4000}
    start[idx_reg] = index
    for name, reg in REGS.items():
        emu.uc.reg_write(reg, start[name])
    esp = tp.STACK_TOP - 0x2000
    emu.uc.reg_write(UC_X86_REG_ESP, esp)
    emu.uc.reg_write(UC_X86_REG_EFLAGS, flags)
    emu.stops = {site + 7: "end"}
    emu.uc.emu_start(site, site + 0x100, count=200)
    if emu.stopped_at != "end":
        return None
    end = {n: emu.uc.reg_read(r) for n, r in REGS.items()}
    result = {"regs": end, "start": start, "flags": emu.uc.reg_read(UC_X86_REG_EFLAGS) & 0x8D5,
              "esp": emu.uc.reg_read(UC_X86_REG_ESP), "esp0": esp}
    ptr = emu.r32(esp - 4) if kind == "push" else end[dst_reg]
    try:
        result["id"] = cstr(emu, ptr)
    except Exception:
        result["id"] = None
    result["ptr"] = ptr
    return result


def main():
    exe = sys.argv[1]
    server = "server" in os.path.basename(exe).lower()
    sites, compares = (SERVER, COMPARES_SERVER) if server else (CLIENT, COMPARES_CLIENT)
    bad = 0
    patched = None
    for site, kind, idx_reg, dst_reg in sites:
        probe = tp.Emu(exe)
        is_patched = bytes(probe.uc.mem_read(site, 1)) == b"\xE9"
        patched = is_patched if patched is None else patched
        for index in range(6):
            for flags in FLAG_PATTERNS:
                r = run_site(exe, site, kind, idx_reg, dst_reg, index, flags)
                problems = []
                if r is None:
                    problems.append("did not reach the end of the instruction")
                else:
                    if r["id"] != IDS[index]:
                        problems.append(f"id {r['id']!r}, wanted {IDS[index]!r}")
                    if (flags & 0x8D5) != r["flags"]:
                        problems.append(f"flags changed {flags & 0x8D5:#x} -> {r['flags']:#x}")
                    if kind == "push":
                        if r["esp"] != r["esp0"] - 4:
                            problems.append("ESP did not drop by exactly 4")
                    elif r["esp"] != r["esp0"]:
                        problems.append("ESP changed")
                    for n in REGS:
                        if n == dst_reg:
                            continue
                        if n == idx_reg and kind == "push" and r["regs"][n] != r["start"][n]:
                            problems.append(f"{n} changed")
                        elif n != idx_reg and r["regs"][n] != r["start"][n]:
                            problems.append(f"{n} changed")
                        elif n == idx_reg and kind == "mov" and r["regs"][n] != r["start"][n]:
                            problems.append(f"{n} (the index) changed")
                if problems and not (not is_patched and index >= 4):
                    bad += 1
                if flags == FLAG_PATTERNS[0]:
                    status = "PASS" if not problems else ("n/a " if (not is_patched and index >= 4) else "FAIL")
                    print(f"  {status} {site:#x} {kind:<4} index {index} -> {r['id'] if r else '-'!s:<5}"
                          + (f"  ({'; '.join(problems)})" if problems else ""))
    for at in compares:
        emu = tp.Emu(exe)
        imm = bytes(emu.uc.mem_read(at, 3))
        want = b"\x83\xFF\x06" if patched else b"\x83\xFF\x04"
        ok = imm == want
        bad += (not ok) and patched
        print(f"  {'PASS' if ok else 'FAIL'} {at:#x} cmp edi,{imm[2]}   ({'patched' if patched else 'stock'}: wants {want[2]})")
    if patched:
        print(f"\npatched exe: {'all checks passed' if not bad else str(bad) + ' check(s) failed'}")
    else:
        print("\nstock exe: indices 0-3 work, 4 and 5 (M-6, TD-8) do not exist; apply --mechanic-armaments")
    sys.exit(1 if bad or not patched else 0)


if __name__ == "__main__":
    main()
