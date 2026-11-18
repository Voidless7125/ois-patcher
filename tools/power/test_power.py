#!/usr/bin/env python3
"""Emulation test for the power-drain fix (needs `pip install unicorn pefile`).

    python3 tools/power/test_power.py <game dir>/ois.exe        (or ois_server.exe)

The two patched functions are run against synthetic modules.  getPowerModifier and drawPower are
stubbed (their own behaviour is not what is being tested); every other instruction is the patched exe.

  SystemManager::totalPowerDrain  must equal the sum of what each module says it draws:
      switched off -> 0, idle -> idle drain, active -> active drain * setting%, all * (1 + modifier)
  ShipModule::drainPower          must take that same amount from the batteries.
"""
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))
import emu as tp
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import (UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_ECX, UC_X86_REG_EDI, UC_X86_REG_EIP,
                               UC_X86_REG_ESI, UC_X86_REG_ESP, UC_X86_REG_XMM0, UC_X86_REG_XMM1)

SERVER = {"total": 0x522BE0, "drain": 0x4AE120, "mod": 0x438020, "draw": 0x521A50}
CLIENT = {"total": 0x5246B0, "drain": 0x4AE260, "mod": 0x438200, "draw": 0x523520}


def xmm(value):
    return int.from_bytes(struct.pack("<f", value) + b"\0" * 12, "little")


def main():
    exe = sys.argv[1]
    A = SERVER if "server" in os.path.basename(exe).lower() else CLIENT
    emu = tp.Emu(exe)
    emu.dist_hooks = (0, 0)
    mods, draws = {}, []

    def stub(uc, address, size, user):
        esp = uc.reg_read(UC_X86_REG_ESP)
        if address == A["mod"]:                                   # getPowerModifier(ecx = components)
            uc.reg_write(UC_X86_REG_XMM0, xmm(mods[uc.reg_read(UC_X86_REG_ECX)]))
        elif address == A["draw"]:                                # drawPower(amount in xmm1)
            draws.append(struct.unpack("<f", (uc.reg_read(UC_X86_REG_XMM1) & 0xFFFFFFFF).to_bytes(4, "little"))[0])
            uc.reg_write(UC_X86_REG_EAX, 1)
        else:
            return
        uc.reg_write(UC_X86_REG_EIP, emu.r32(esp))
        uc.reg_write(UC_X86_REG_ESP, esp + 4)

    emu.uc.hook_add(UC_HOOK_CODE, stub, begin=min(A["mod"], A["draw"]), end=max(A["mod"], A["draw"]))

    def module(sysmgr, idle, active, enabled=True, running=False, setting=100, modifier=0.0):
        m, cls, comp = emu.alloc(0x80), emu.alloc(0x120), emu.alloc(0x10)
        emu.w32(m + 4, sysmgr)
        emu.w32(m + 8, cls)
        emu.w32(m + 0xC, comp)
        emu.wf(cls + 0xBC, active)
        emu.wf(cls + 0xC0, idle)
        emu.uc.mem_write(m + 0x62, bytes([1 if running else 0, 1 if enabled else 0]))
        emu.w32(m + 0x64, setting)
        mods[comp] = modifier
        return m

    bad = 0

    def check(name, got, want):
        nonlocal bad
        ok = abs(got - want) < 1e-4
        bad += not ok
        print(("  PASS " if ok else "  FAIL ") + f"{name}: {got:.4f}" + ("" if ok else f" (want {want:.4f})"))

    sm = emu.alloc(0x100)
    cases = [module(sm, 0.5, 2.0, modifier=0.4),                              # idle            0.5 * 1.4
             module(sm, 0.3, 2.0, running=True, setting=50, modifier=0.4),    # active at 50 %  2.0 * 0.5 * 1.4
             module(sm, 9.0, 9.0, enabled=False, modifier=0.4),               # switched off    0
             module(sm, 0.25, 0.0, modifier=0.0)]                             # no modifier     0.25
    arr = emu.alloc(4 * len(cases))
    for i, m in enumerate(cases):
        emu.w32(arr + 4 * i, m)
    emu.w32(sm + 0x3C, arr)
    emu.w32(sm + 0x40, arr + 4 * len(cases))
    want_each = [0.7, 1.4, 0.0, 0.25]

    print("totalPowerDrain")
    keep = {UC_X86_REG_EBX: 0x11111111, UC_X86_REG_ESI: 0x22222222, UC_X86_REG_EDI: 0x33333333}
    emu.call_stdcall(A["total"], [], ecx=sm, regs=keep)
    got = struct.unpack("<f", (emu.uc.reg_read(UC_X86_REG_XMM0) & 0xFFFFFFFF).to_bytes(4, "little"))[0]
    check("sum of the modules' own drains", got, sum(want_each))
    ok = all(emu.uc.reg_read(r) == v for r, v in keep.items())
    bad += not ok
    print(("  PASS " if ok else "  FAIL ") + "EBX/ESI/EDI preserved")
    emu.w32(sm + 0x40, arr)
    emu.call_stdcall(A["total"], [], ecx=sm)
    got = struct.unpack("<f", (emu.uc.reg_read(UC_X86_REG_XMM0) & 0xFFFFFFFF).to_bytes(4, "little"))[0]
    check("no modules -> 0", got, 0.0)

    print("drainPower (dt = 0.5 s)")
    dt = struct.unpack("<I", struct.pack("<f", 0.5))[0]
    for i, (m, want) in enumerate(zip(cases, want_each)):
        draws.clear()
        emu.call_stdcall(A["drain"], [dt], ecx=m, regs={UC_X86_REG_ESI: 0x5A5A5A5A})
        if i == 2:
            ok = not draws
            bad += not ok
            print(("  PASS " if ok else "  FAIL ") + "switched off: nothing drawn")
        else:
            check(f"module {i}: amount drawn this tick", draws[0] if draws else -1.0, want * 0.5)
    print("all power-drain checks pass" if not bad else f"{bad} FAILED")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
