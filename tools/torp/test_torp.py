#!/usr/bin/env python3
"""Emulation test for the torpedo-lost-target fix (needs `pip install unicorn pefile`).

    python3 tools/torp/test_torp.py <game dir>/ois.exe
    python3 tools/torp/test_torp.py <game dir>/ois_server.exe

Runs the three patched sites against a synthetic Weapon:
  C  GameLogic::entirelyRemoveShip  -- target removed: target cleared, marker set, aim point cleared
  A  Weapon::runHomeLogic target test -- only an *unmarked* torpedo with no target goes looking for one
  B  the call to Weapon::runAimLogic  -- a marked torpedo with no aim point neither steers nor thrusts,
                                         anything else still reaches the real aim code
"""
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))
import emu as tp
from unicorn.x86_const import UC_X86_REG_EBX, UC_X86_REG_ECX, UC_X86_REG_EDI, UC_X86_REG_EAX, UC_X86_REG_ESP

TARGET, AIM_X, AIM_Y, MARKER, ENGINE_SLOTS = 0x38C, 0x12C, 0x130, 0x3DC, 0x40
NO_AIM = struct.unpack("<I", struct.pack("<f", -9999.0))[0]


def main():
    exe = sys.argv[1]
    server = "server" in os.path.basename(exe).lower()
    home = 0x51C790 if server else 0x51D280
    remove_site = 0x40D6BB if server else 0x40D98B
    acquire_site, aim_call, skip = home + 0x6C, home + 0x918, home + 0x8D1
    emu = tp.Emu(exe)
    emu.dist_hooks = (0, 0)

    def stock(va, n):          # bytes as patched (the stock `JNE` target is recovered from the cave)
        return bytes(emu.uc.mem_read(va, n))

    bad = 0

    def check(name, cond, detail=""):
        nonlocal bad
        bad += not cond
        print(("  PASS " if cond else "  FAIL ") + name + (f"  {detail}" if detail and not cond else ""))

    def weapon(target=0, marker=0, aim=(1.0, 2.0)):
        w = emu.alloc(0x500)
        emu.w32(w + TARGET, target)
        emu.uc.mem_write(w + MARKER, bytes([marker]))
        emu.wf(w + AIM_X, aim[0]) if aim else emu.w32(w + AIM_X, NO_AIM)
        emu.wf(w + AIM_Y, aim[1]) if aim else emu.w32(w + AIM_Y, NO_AIM)
        return w

    # ---- C: target removal -------------------------------------------------------------------
    emu.stops.clear()
    emu.stops[remove_site + 10] = "continue"
    w = weapon(target=0x1234, marker=1, aim=(5.0, 6.0))
    emu.call_stdcall(remove_site, [], regs={UC_X86_REG_EBX: w})
    check("C: removal reaches the original continuation", emu.stopped_at == "continue", str(emu.stopped_at))
    check("C: target cleared", emu.r32(w + TARGET) == 0)
    check("C: marker set", emu.rb(w + MARKER) == 2)
    check("C: aim point cleared", emu.r32(w + AIM_X) == NO_AIM and emu.r32(w + AIM_Y) == NO_AIM)

    # ---- A: runHomeLogic target test -----------------------------------------------------------
    # follow the patched jump to find the cave, then read the stock `JNE` target out of the cave
    jmp = stock(acquire_site, 5)
    assert jmp[0] == 0xE9, "site is not patched"
    cave = acquire_site + 5 + struct.unpack("<i", jmp[1:])[0]
    present = cave + 12 + struct.unpack("<i", stock(cave + 8, 4))[0]
    for label, tgt, marker, want in (("has a target", 0x1234, 0, "present"), ("has a target, marked", 0x1234, 2, "present"),
                                     ("no target, never had one", 0, 0, "acquire"), ("no target, had one (flag 1)", 0, 1, "acquire"),
                                     ("no target, target died", 0, 2, "skip")):
        emu.stops.clear()
        emu.stops.update({present: "present", acquire_site + 12: "acquire", skip: "skip"})
        w = weapon(target=tgt, marker=marker)
        emu.call_stdcall(acquire_site, [], regs={UC_X86_REG_EDI: w, UC_X86_REG_EAX: 0})
        check(f"A: {label} -> {want}", emu.stopped_at == want, str(emu.stopped_at))

    # ---- B: the aim call -----------------------------------------------------------------------
    callins = stock(aim_call, 5)
    assert callins[0] == 0xE8
    # the original callee, recovered from the cave's final JMP
    cave_b = aim_call + 5 + struct.unpack("<i", callins[1:])[0]
    body = stock(cave_b, 0x80)
    end = body.index(b"\xC2\x08\x00") + 3
    assert body[end] == 0xE9
    aim_func = cave_b + end + 5 + struct.unpack("<i", body[end + 1:end + 5])[0]
    for label, tgt, marker, aim, want in (("target alive", 0x1234, 2, None, "aim"),
                                          ("never had a target", 0, 0, None, "aim"),
                                          ("flag 1, no target", 0, 1, None, "aim"),
                                          ("target died, player picked a point", 0, 2, (3.0, 4.0), "aim"),
                                          ("target died, no new aim point", 0, 2, None, "drift")):
        emu.stops.clear()
        emu.stops.update({aim_func: "aim", aim_call + 5: "drift"})
        w = weapon(target=tgt, marker=marker, aim=aim)
        slots = emu.alloc(0x40)
        mod0, mod10 = emu.alloc(0x80), emu.alloc(0x80)
        emu.w32(w + ENGINE_SLOTS, slots)
        emu.w32(slots, mod0)
        emu.w32(slots + 0x10, mod10)
        emu.uc.mem_write(mod0 + 0x62, b"\x01")
        emu.uc.mem_write(mod10 + 0x62, b"\x01")
        emu.call_stdcall(aim_call, [0x11111111, 0x22222222], regs={UC_X86_REG_ECX: w})
        esp = emu.uc.reg_read(UC_X86_REG_ESP)
        ok = emu.stopped_at == want
        if want == "drift":
            ok = ok and emu.rb(mod0 + 0x62) == 0 and emu.rb(mod10 + 0x62) == 0
            # CALL pushed one return address; RET 8 must pop it plus the two argument words
            ok = ok and esp == tp.STACK_TOP - 0x1000 - 4
        else:
            ok = ok and emu.rb(mod0 + 0x62) == 1 and emu.rb(mod10 + 0x62) == 1
        check(f"B: {label} -> {want}", ok, str(emu.stopped_at))
    print("all torpedo-fix checks pass" if not bad else f"{bad} FAILED")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
