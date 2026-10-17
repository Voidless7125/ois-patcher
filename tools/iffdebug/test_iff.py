#!/usr/bin/env python3
"""Emulates the --debug-iff wrapper (the cave bytes embedded in the patcher) with a fake ship, a fake
debugPrint and a fake ShipBehaviour::runLogic (needs `pip install unicorn`).

    python3 tools/iffdebug/test_iff.py
"""
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
import ois_patcher as op
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import *

CAVE, DATA, STACK = 0x10000000, 0x20000000, 0x30000000
PRINT, RUN = 0x11000000, 0x12000000
DT = 0.016


def build():
    uc = Uc(UC_ARCH_X86, UC_MODE_32)
    uc.mem_map(CAVE, 0x2000)
    uc.mem_map(DATA, 0x10000)
    uc.mem_map(STACK, 0x10000)
    uc.mem_map(PRINT, 0x1000)
    uc.mem_map(RUN, 0x1000)
    code = bytearray(op.IFF_DEBUG_CAVE)
    struct.pack_into("<i", code, op.IFF_DEBUG_PRINT_AT, PRINT - (CAVE + op.IFF_DEBUG_PRINT_AT + 4))
    struct.pack_into("<i", code, op.IFF_DEBUG_RUN_AT, RUN - (CAVE + op.IFF_DEBUG_RUN_AT + 4))
    uc.mem_write(CAVE, bytes(code))
    uc.mem_write(PRINT, b"\xC3")
    uc.mem_write(RUN, b"\xC3")
    return uc


def main():
    uc = build()
    log, state = [], {"run": None}

    def cstr(a):
        out = b""
        while True:
            c = bytes(uc.mem_read(a, 1))
            if c == b"\0":
                return out.decode()
            out += c
            a += 1

    def hook(uc, address, size, _):
        if address == PRINT:
            esp = uc.reg_read(UC_X86_REG_ESP)
            a = struct.unpack("<6I", bytes(uc.mem_read(esp + 4, 24)))
            log.append((cstr(a[0]), cstr(a[1]) % (cstr(a[2]), struct.unpack("<i", struct.pack("<I", a[3]))[0],
                                                  struct.unpack("<i", struct.pack("<I", a[4]))[0], cstr(a[5]))))
        elif address == RUN and state["run"]:
            state["run"]()
            # the dt must arrive in XMM1 unchanged
            state["xmm1"] = uc.reg_read(UC_X86_REG_XMM1).to_bytes(16, "little")[:4]
            state["ecx"] = uc.reg_read(UC_X86_REG_ECX)

    uc.hook_add(UC_HOOK_CODE, hook)

    beh, ship, sysm = DATA + 0x100, DATA + 0x1000, DATA + 0x2000
    uc.mem_write(beh + 0x6C, struct.pack("<I", ship))
    uc.mem_write(ship + 0x40, struct.pack("<I", sysm))
    uc.mem_write(ship + 8, b"SS Jolly Rancher\0")
    uc.mem_write(ship + 0x1C, struct.pack("<I", 0xF))
    long_name = DATA + 0x3000
    uc.mem_write(long_name, b"A ship with a rather long name\0")

    def call(label):
        ret = 0x30008000
        sp = STACK + 0x8000
        uc.mem_write(sp, struct.pack("<I", ret))
        uc.reg_write(UC_X86_REG_ESP, sp)
        uc.reg_write(UC_X86_REG_ECX, beh)
        for r in (UC_X86_REG_EBX, UC_X86_REG_ESI, UC_X86_REG_EDI):
            uc.reg_write(r, 0x1234)
        uc.reg_write(UC_X86_REG_XMM1, int.from_bytes(struct.pack("<f", DT), "little"))
        uc.emu_start(CAVE, ret)
        assert uc.reg_read(UC_X86_REG_ESP) == sp + 4, "stack not balanced"
        assert uc.reg_read(UC_X86_REG_EBX) == 0x1234 and uc.reg_read(UC_X86_REG_ESI) == 0x1234 \
            and uc.reg_read(UC_X86_REG_EDI) == 0x1234, "callee-saved registers not preserved"

    fails = []

    def check(name, cond, detail=""):
        print(("  PASS " if cond else "  FAIL ") + name + (f"   {detail}" if detail and not cond else ""))
        if not cond:
            fails.append(name)

    uc.mem_write(sysm + 0x34, b"\x01")
    call("first")
    check("first sighting is logged with the starting value",
          log == [("GAME", "IFFDBG SS Jolly Rancher: IFF -1 -> 1, changed outside the AI update")], str(log))
    log.clear()
    call("steady")
    check("no change, no line", log == [], str(log))

    def off_inside():
        uc.mem_write(sysm + 0x34, b"\x00")
    state["run"] = off_inside
    call("off inside")
    check("a change during the AI update is reported as inside",
          log == [("GAME", "IFFDBG SS Jolly Rancher: IFF 1 -> 0, changed inside the AI update")], str(log))
    check("runLogic received ECX = the behaviour", state["ecx"] == beh)
    check("runLogic received the frame time in XMM1", struct.unpack("<f", state["xmm1"])[0] == struct.unpack("<f", struct.pack("<f", DT))[0])
    log.clear()
    state["run"] = None
    uc.mem_write(sysm + 0x34, b"\x01")
    call("on outside")
    check("a change between two updates is reported as outside",
          log == [("GAME", "IFFDBG SS Jolly Rancher: IFF 0 -> 1, changed outside the AI update")], str(log))
    log.clear()
    uc.mem_write(ship + 8, struct.pack("<I", long_name))
    uc.mem_write(ship + 0x1C, struct.pack("<I", 0x20))
    uc.mem_write(sysm + 0x34, b"\x00")
    call("long name")
    check("a long (heap) ship name is read through its pointer",
          log == [("GAME", "IFFDBG A ship with a rather long name: IFF 1 -> 0, changed outside the AI update")], str(log))
    # no ship / no system manager: nothing logged, nothing crashes
    log.clear()
    uc.mem_write(beh + 0x6C, struct.pack("<I", 0))
    call("no ship")
    check("a behaviour without a ship is ignored", log == [])
    print("all IFF-debug checks pass" if not fails else f"{len(fails)} FAILED")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
