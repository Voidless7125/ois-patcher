#!/usr/bin/env python3
"""Emulation test for --hail-guard (needs `pip install unicorn pefile`).

    python3 tools/hail/test_hail.py <game dir>/ois.exe        (or ois_server.exe)

Runs ShipInterface::doCommunicateWithSelected from its first instruction with a player ship whose comms module is
(a) missing, (b) disconnected, (c) connected, and a selected object that has a comms channel, and reports what the
handler did.  SystemManager::getModule and the log call are stubbed; everything else is the real code.

  patched exe : (a) and (b) refuse -- one log line "Comms offline: cannot hail.", return false, EBX/ESI/EDI/EBP/ESP
                restored -- and (c) reaches the original code with ESI = the selected object   -> exit 0
  stock exe   : all three go straight on to the channel lookup (the bug)                           -> exit 1
"""
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "pds"))
import test_pds as tp
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import (UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_ECX, UC_X86_REG_EDI, UC_X86_REG_EDX,
                               UC_X86_REG_EBP, UC_X86_REG_EIP, UC_X86_REG_ESI, UC_X86_REG_ESP)

CLIENT = dict(entry=0x4E5AC0, hook=0x4E5ACD, getmod_site=0x4E80AF, join=0x4E5B1A)
SERVER = dict(entry=0x4E5530, hook=0x4E553D, getmod_site=0x4E7B1F, join=0x4E558A)
CHANNEL = 0x1234


def rel_target(emu, at):
    rel = struct.unpack("<i", bytes(emu.uc.mem_read(at + 1, 4)))[0]
    return at + 5 + rel


def run_case(exe, sites, module_state):
    emu = tp.Emu(exe)
    emu.dist_hooks = (0, 0)
    uc = emu.uc
    getmod = rel_target(emu, sites["getmod_site"])
    logfn = rel_target(emu, sites["join"] + 8)
    ship = emu.alloc(0x400)
    sysm = emu.alloc(0x100)
    emu.w32(ship + 0x40, sysm)
    selected = emu.alloc(0x200)
    emu.w32(selected + 0x130, CHANNEL)
    emu.w32(ship + 0x19C, selected)
    emu.w32(ship + 0x224, 0x7777)
    module = None
    if module_state != "missing":
        module = emu.alloc(0x100)
        uc.mem_write(module + 0x63, bytes([1 if module_state == "connected" else 0]))
    log = []
    outcome = {}
    sentinel = 0x7FEFFF00
    uc.mem_map(0x7FEFF000, 0x1000)
    uc.mem_write(sentinel, b"\xf4")

    def hook(u, address, size, _):
        esp = u.reg_read(UC_X86_REG_ESP)
        if address == getmod:                    # thiscall getModule(this, id, flag), callee pops 8
            if emu.r32(esp + 4) == 0xE and u.reg_read(UC_X86_REG_ECX) == sysm:
                u.reg_write(UC_X86_REG_EAX, module or 0)
            else:
                u.reg_write(UC_X86_REG_EAX, 0xDEAD)
            u.reg_write(UC_X86_REG_EIP, emu.r32(esp))
            u.reg_write(UC_X86_REG_ESP, esp + 12)
        elif address == logfn:                   # addLogLine(owner, priority, text), cdecl
            ptr = emu.r32(esp + 12)
            text = bytes(u.mem_read(ptr, 40)).split(b"\0")[0].decode("latin1")
            log.append((emu.r32(esp + 4), emu.r32(esp + 8), text))
            u.reg_write(UC_X86_REG_EIP, emu.r32(esp))
            u.reg_write(UC_X86_REG_ESP, esp + 4)
        elif address == sites["hook"] + 6:       # the original code after the displaced instruction
            outcome["reached"] = True
            outcome["esi"] = u.reg_read(UC_X86_REG_ESI)
            u.emu_stop()
        elif address == sentinel:
            outcome["returned"] = True
            outcome["eax"] = u.reg_read(UC_X86_REG_EAX)
            u.emu_stop()

    for addr in (getmod, logfn, sites["hook"] + 6, sentinel):
        uc.hook_add(UC_HOOK_CODE, hook, begin=addr, end=addr)
    start = {UC_X86_REG_EBX: 0xB0B00001, UC_X86_REG_ESI: 0x5151F00D, UC_X86_REG_EDI: 0xED1ED1ED, UC_X86_REG_EBP: 0xBEBE0002}
    esp = tp.STACK_TOP - 0x1000
    esp -= 4; emu.w32(esp, ship)                 # argument 1: the player's ship
    esp -= 4; emu.w32(esp, sentinel)
    for r, v in start.items():
        uc.reg_write(r, v)
    uc.reg_write(UC_X86_REG_ESP, esp)
    entry_esp = esp
    try:
        uc.emu_start(sites["entry"], sentinel + 1, count=3000)
    except Exception as e:                       # the stock path runs on into code that needs a real game
        outcome["error"] = str(e)
    if outcome.get("returned"):
        outcome["restored"] = (all(uc.reg_read(r) == v for r, v in start.items() if r != UC_X86_REG_EBX)
                               and uc.reg_read(UC_X86_REG_ESP) == entry_esp + 4)
        outcome["ebx"] = uc.reg_read(UC_X86_REG_EBX) == start[UC_X86_REG_EBX]
    outcome["log"] = log
    outcome["selected"] = selected
    return outcome


def main():
    exe = sys.argv[1]
    sites = SERVER if "server" in os.path.basename(exe).lower() else CLIENT
    patched = bytes(tp.Emu(exe).uc.mem_read(sites["hook"], 1)) == b"\xE9"
    bad = 0
    for state in ("missing", "disconnected", "connected"):
        o = run_case(exe, sites, state)
        refused = bool(o.get("returned")) and not o.get("reached")
        passed_on = bool(o.get("reached")) and o.get("esi") == o["selected"]
        want_refuse = state != "connected"
        problems = []
        if want_refuse:
            if not refused:
                problems.append("the hail was not refused")
            else:
                if o["eax"] & 0xFF:
                    problems.append("did not return false")
                if len(o["log"]) != 1 or o["log"][0][2] != "Comms offline: cannot hail." or o["log"][0][:2] != (0x7777, 2):
                    problems.append(f"log was {o['log']}")
                if not (o["restored"] and o["ebx"]):
                    problems.append("registers/stack not restored")
        elif not passed_on:
            problems.append(f"hail did not reach the channel lookup ({o})")
        if problems:
            bad += 1
        print(f"  {'FAIL' if problems else 'PASS'} comms module {state:<12} -> "
              f"{'refused' if refused else 'went on to the original code' if passed_on else 'other'}"
              + (f"  ({'; '.join(problems)})" if problems else ""))
    if patched:
        print(f"\npatched exe: {'all checks passed' if not bad else str(bad) + ' check(s) failed'}")
        sys.exit(1 if bad else 0)
    print("\nstock exe: a ship with comms missing or disconnected can still hail; apply --hail-guard")
    sys.exit(1)


if __name__ == "__main__":
    main()
