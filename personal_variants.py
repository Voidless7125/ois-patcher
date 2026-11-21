"""
personal_variants.py

This file acts as a plugin template for 'ois-patcher'. 
You can use this file to add your own data fixes (modifying .txt files) 
or exe fixes (binary patching) without cluttering the main script.

If this file exists, ois_patcher.py will automatically detect and load it.

--- HOW TO USE ---

1. DATA FIXES:
   Add your text replacements to the `DATA_FIXES` dictionary below.
   Format:
   "filename.txt": [
       (number_of_occurrences_to_replace, "exact string to find", "exact replacement string"),
   ]

2. EXE FIXES:
   Write your binary patching functions and call them from inside `apply_exe_fixes()`.
   Ensure you import any required functions from `ois_patcher` *inside* your functions
   to prevent circular import errors when the script starts up.
"""
import re
import sys
import struct
from pathlib import Path

# Data half of the optional --mechanic-armaments variant (ois_patcher.fix_mechanic_armaments).  Only
# installed together with that exe patch: the two new buttons ask the mechanic for armament indices
# 4 and 5, which a stock exe does not have.  The buttons are moved up (pitch 12, first at y=140) to
# make room for two more; the armament list above them is one line per armament.
# The TD-8's price is this project's own number (the game ships it with none, i.e. free);
# `canprobestar` is the key the game really reads (weapons.txt spells it `probestar`, which nothing
# reads): the probe ignores HEAT damage, which is what makes it a *stellar* probe.
MECHANIC_FIXES = {
    "ui_x7.txt": [
        (1, "    button=168,148,134,`9Buy Countermeasure,MECHANIC_BUYARMAMENT:-1,MECHANIC_CAN_BUY_ARMAMENT:-1",
            "    button=168,140,134,`9Buy Countermeasure,MECHANIC_BUYARMAMENT:-1,MECHANIC_CAN_BUY_ARMAMENT:-1"),
        (1, "    greyedbutton=168,148,134,Buy Countermeasure,NONE,MECHANIC_CANNOT_BUY_ARMAMENT:-1",
            "    greyedbutton=168,140,134,Buy Countermeasure,NONE,MECHANIC_CANNOT_BUY_ARMAMENT:-1"),
        (1, "    button=168,161,134,`!Sell Armament,MECHANIC_SELLARMAMENT,MECHANIC_CAN_SELL_ARMAMENT",
            "    button=168,152,134,`!Sell Armament,MECHANIC_SELLARMAMENT,MECHANIC_CAN_SELL_ARMAMENT"),
        (1, "    greyedbutton=168,161,134,Sell Armament,NONE,MECHANIC_CANNOT_SELL_ARMAMENT",
            "    greyedbutton=168,152,134,Sell Armament,NONE,MECHANIC_CANNOT_SELL_ARMAMENT"),
        (1, "    button=168,174,134,`$E-10 EMP Torpedo,MECHANIC_BUYARMAMENT:2,MECHANIC_CAN_BUY_ARMAMENT:2",
            "    button=168,164,134,`$E-10 EMP Torpedo,MECHANIC_BUYARMAMENT:2,MECHANIC_CAN_BUY_ARMAMENT:2"),
        (1, "    greyedbutton=168,174,134,E-10 EMP Torpedo,NONE,MECHANIC_CANNOT_BUY_ARMAMENT:2",
            "    greyedbutton=168,164,134,E-10 EMP Torpedo,NONE,MECHANIC_CANNOT_BUY_ARMAMENT:2"),
        (1, "    button=168,187,134,`^M-12 Heavy Torpedo,MECHANIC_BUYARMAMENT:1,MECHANIC_CAN_BUY_ARMAMENT:1",
            "    button=168,176,134,`^M-12 Heavy Torpedo,MECHANIC_BUYARMAMENT:1,MECHANIC_CAN_BUY_ARMAMENT:1"),
        (1, "    greyedbutton=168,187,134,M-12 Heavy Torpedo,NONE,MECHANIC_CANNOT_BUY_ARMAMENT:1",
            "    greyedbutton=168,176,134,M-12 Heavy Torpedo,NONE,MECHANIC_CANNOT_BUY_ARMAMENT:1"),
        (1, "    button=168,200,134,`^M-10 Medium Torpedo,MECHANIC_BUYARMAMENT:0,MECHANIC_CAN_BUY_ARMAMENT:0",
            "    button=168,188,134,`^M-10 Medium Torpedo,MECHANIC_BUYARMAMENT:0,MECHANIC_CAN_BUY_ARMAMENT:0"),
        (1, "    greyedbutton=168,200,134,M-10 Medium Torpedo,NONE,MECHANIC_CANNOT_BUY_ARMAMENT:0",
            "    greyedbutton=168,188,134,M-10 Medium Torpedo,NONE,MECHANIC_CANNOT_BUY_ARMAMENT:0"),
        (1, "    button=168,213,134,`!TD-4 Science Probe,MECHANIC_BUYARMAMENT:3,MECHANIC_CAN_BUY_ARMAMENT:3",
            "    button=168,200,134,`!TD-4 Science Probe,MECHANIC_BUYARMAMENT:3,MECHANIC_CAN_BUY_ARMAMENT:3"),
        (1, "    greyedbutton=168,213,134,TD-4 Science Probe,NONE,MECHANIC_CANNOT_BUY_ARMAMENT:3",
            "    greyedbutton=168,200,134,TD-4 Science Probe,NONE,MECHANIC_CANNOT_BUY_ARMAMENT:3\n"
            "    button=168,212,134,`^M-6 Light Torpedo,MECHANIC_BUYARMAMENT:4,MECHANIC_CAN_BUY_ARMAMENT:4\n"
            "    greyedbutton=168,212,134,M-6 Light Torpedo,NONE,MECHANIC_CANNOT_BUY_ARMAMENT:4\n"
            "    button=168,224,134,`!TD-8 Stellar Probe,MECHANIC_BUYARMAMENT:5,MECHANIC_CAN_BUY_ARMAMENT:5\n"
            "    greyedbutton=168,224,134,TD-8 Stellar Probe,NONE,MECHANIC_CANNOT_BUY_ARMAMENT:5"),
    ],
    "weapons.txt": [
        (1, "probestar=true", "probestar=true\ncanprobestar=true\nbasecost=350"),
    ],
}

DATA_FIXES = MECHANIC_FIXES

# ==========================================
# 2. EXE FIXES
# ==========================================
def apply_exe_fixes(data, pe, ptch_va, ptch_off, cave_cursor, server=False):
    """Called by ois_patcher.py to apply custom binary patches."""
    print(f"  -> Applying personal variant patches ({'server' if server else 'client'})...")
    
    cave_cursor = fix_mechanic_armaments(data, pe, ptch_va, ptch_off, cave_cursor, server)
    cave_cursor = fix_torpedo_lost_target(data, pe, ptch_va, ptch_off, cave_cursor, server)
    cave_cursor = fix_hail_guard(data, pe, ptch_va, ptch_off, cave_cursor, server)

    return cave_cursor

# ============================================================
# Exe half of the MECHANIC_FIXES above: the station mechanic's Armaments tab also sells the M-6 light
# torpedo and the TD-8 stellar probe.
#
# weapons.txt defines six launchable armaments (m10, m12, e10, td4, m6, td8) but the mechanic only knows four:
# ShipInterface::doMechanicBuyArmament, TradeEngine::canBuyArmament, ShipData::checkMechanicCanBuyArmament and
# TradeEngine::getArmamentStatus all index one 4-entry table of id strings in .rdata.  The table cannot grow in
# place, and a table of absolute pointers in the added section would need base-relocation entries (the game does
# not load at its preferred base), so the four indexed loads are redirected to caves that compute the string
# address position-independently (CALL $+5 / POP) from six 4-byte ids appended to the cave, leaving every other
# register and the flags as the original load left them:
#       push [idx*4+T]    ->   PUSH EAX / CALL $+5 / POP EAX / LEA EAX,[EAX+idx*4+delta] / XCHG EAX,[ESP]
#       mov  r,[idx*4+T]  ->   CALL $+5 / POP r / LEA r,[r+idx*4+delta]      (through EAX when r is the index)
# getArmamentStatus lists one line per armament and then the countermeasure line, which it recognises by
# index 4 and loops up to; both constants become 6.  Without this the two new buttons in MECHANIC_FIXES would
# index past the end of the stock table.  tools/mech/test_mech.py runs the four instructions under emulation.
# ============================================================

MECH_IDS = (b"m10\0", b"m12\0", b"e10\0", b"td4\0", b"m6\0\0", b"td8\0")


def fix_mechanic_armaments(data, pe, ptch_va, ptch_off, cave_cursor, server=False):
    import struct
    import ois_patcher
    verify_site, bail, _fix_lists = ois_patcher.verify_site, ois_patcher.bail, ois_patcher._fix_lists
    neutralize_relocations, va_to_offset = ois_patcher.neutralize_relocations, ois_patcher.va_to_offset

    label = "Mechanic also sells the M-6 torpedo and TD-8 probe" + (" (server)" if server else "")
    applied, skipped = _fix_lists(server)
    if server:
        TABLE, COMPARES = 0x5DD9F4, (0x495107, 0x495249)
        SITES = ((0x494CC0, "push", "ebx"), (0x49517D, "mov", "edi"), (0x4D72B6, "push", "ebx"), (0x4E9067, "mov", "esi"))
    else:
        TABLE, COMPARES = 0x5DFACC, (0x495277, 0x4953B9)
        SITES = ((0x494E30, "push", "ebx"), (0x4952ED, "mov", "edi"), (0x4D74D6, "push", "ebx"), (0x4E95F7, "mov", "esi"))
    # (kind, index register) -> (original bytes before the table address, destination register, destination code)
    SHAPES = {("push", "ebx"): ("FF349D", None), ("mov", "edi"): ("8B1CBD", "ebx"), ("mov", "esi"): ("8B34B5", "esi")}
    REG = {"eax": 0, "ebx": 3, "esi": 6, "edi": 7}
    tbl = struct.pack("<I", TABLE)
    for site, kind, idx in SITES:
        if verify_site(data, pe, site, bytes.fromhex(SHAPES[(kind, idx)][0]) + tbl, label + f" (table load at {site:#x})") is None:
            return bail(label, cave_cursor, server)
    for at in COMPARES:
        if verify_site(data, pe, at, bytes.fromhex("83FF04"), label + f" (index limit at {at:#x})") is None:
            return bail(label, cave_cursor, server)

    cave_va = ptch_va + cave_cursor
    code = bytearray()
    entries = []                                              # (site, cave offset of the replacement)
    fix_delta = []                                            # (position of the disp32, position of the POP byte)
    for site, kind, idx in SITES:
        start = len(code)
        entries.append((site, start))
        dst = SHAPES[(kind, idx)][1]
        if kind == "push":
            code += bytes.fromhex("50" "E800000000" "58")                            # PUSH EAX / CALL $+5 / POP EAX
            pop_at = len(code) - 1
            code += bytes([0x8D, 0x84, 0x80 | (REG[idx] << 3) | 0]) + b"\0\0\0\0"      # LEA EAX,[EAX+idx*4+delta]
            fix_delta.append((len(code) - 4, pop_at))
            code += bytes.fromhex("870424")                                          # XCHG EAX,[ESP]
        elif dst != idx:
            code += bytes.fromhex("E800000000") + bytes([0x58 | REG[dst]])           # CALL $+5 / POP dst
            pop_at = len(code) - 1
            code += bytes([0x8D, 0x80 | (REG[dst] << 3) | 4, 0x80 | (REG[idx] << 3) | REG[dst]]) + b"\0\0\0\0"   # LEA dst,[dst+idx*4+delta]
            fix_delta.append((len(code) - 4, pop_at))
        else:                                                                        # destination is the index itself
            code += bytes.fromhex("50" "E800000000" "58")                            # PUSH EAX / CALL $+5 / POP EAX
            pop_at = len(code) - 1
            code += bytes([0x8D, 0x84, 0x80 | (REG[idx] << 3) | 0]) + b"\0\0\0\0"      # LEA EAX,[EAX+idx*4+delta]
            fix_delta.append((len(code) - 4, pop_at))
            code += bytes([0x89, 0xC0 | (0 << 3) | REG[idx]])                         # MOV idx,EAX
            code += b"\x58"                                                          # POP EAX (the original)
        code += b"\xE9" + struct.pack("<i", (site + 7) - (cave_va + len(code) + 5))   # JMP back
    code += b"\x90" * (-len(code) % 4)
    ids_at = len(code)
    code += b"".join(MECH_IDS)
    for disp_at, pop_at in fix_delta:
        struct.pack_into("<i", code, disp_at, (cave_va + ids_at) - (cave_va + pop_at))
    data[ptch_off + cave_cursor: ptch_off + cave_cursor + len(code)] = code
    for site, start in entries:
        neutralize_relocations(data, pe, site, 7, label)
        off = va_to_offset(pe, site)
        data[off:off + 7] = b"\xE9" + struct.pack("<i", (cave_va + start) - (site + 5)) + b"\x90\x90"
    for at in COMPARES:
        data[va_to_offset(pe, at) + 2] = 6
    print(f"  [OK] {label}")
    applied.append(label)
    return cave_cursor + len(code)


# ============================================================
# Personal-variants fix: a torpedo whose target is destroyed before it hits no
# longer re-targets the nearest contact (a station, another weapon or you); it
# drifts and can be re-targeted by hand.  Not on master: the upstream maintainer
# points to a developer video where a torpedo that lost its target circled back
# to its own ship, so the stock behaviour may be intended.
# ============================================================

def fix_torpedo_lost_target(data, pe, ptch_va, ptch_off, cave_cursor, server=False):
    import ois_patcher
    _fix_lists = ois_patcher._fix_lists
    verify_site = ois_patcher.verify_site
    bail = ois_patcher.bail
    _rel32_target = ois_patcher._rel32_target
    neutralize_relocations = ois_patcher.neutralize_relocations
    _rel32 = ois_patcher._rel32
    va_to_offset = ois_patcher.va_to_offset

    label = "Torpedo whose target dies re-targets the nearest contact" + (" (server)" if server else "")
    applied, skipped = _fix_lists(server)


    # Weapon::runHomeLogic (the torpedo's homing code) and GameLogic::entirelyRemoveShip
    HOME = 0x0051C790 if server else 0x0051D280
    REMOVE_SITE = 0x0040D6BB if server else 0x0040D98B
    ACQUIRE_SITE, AIM_CALL, AFTER_ACQUIRE = HOME + 0x6C, HOME + 0x918, HOME + 0x8D1
    # 1. runHomeLogic: `if (target == 0) pick the nearest sensor contact` -- stock behaviour once a target is gone
    if verify_site(data, pe, ACQUIRE_SITE, bytes.fromhex("39878C0300000F85"), label + " (target test)") is None:
        return bail(label, cave_cursor, server)
    if verify_site(data, pe, AFTER_ACQUIRE, bytes.fromhex("8B8788030000F30F1005"), label + " (after acquisition)") is None:
        return bail(label, cave_cursor, server)
    # 2. the aim call that follows it
    if verify_site(data, pe, AIM_CALL - 2, bytes.fromhex("8BCFE8"), label + " (aim call)") is None:
        return bail(label, cave_cursor, server)
    # 3. entirelyRemoveShip: the weapon loop that zeroes a torpedo's target when that ship is removed
    if verify_site(data, pe, REMOVE_SITE - 8, bytes.fromhex("39838C030000750AC7838C03000000000000"),
                   label + " (target cleared on removal)") is None:
        return bail(label, cave_cursor, server)
    PRESENT = _rel32_target(data, pe, ACQUIRE_SITE + 6, 2)       # the original `JNE <has a target>`
    AIM_FUNC = _rel32_target(data, pe, AIM_CALL, 1)              # Weapon::runAimLogic
    if verify_site(data, pe, AIM_FUNC, bytes.fromhex("558BEC6AFF68"), label + " (aim function)") is None:
        return bail(label, cave_cursor, server)
    CONTINUE = REMOVE_SITE + 10
    for site, length in ((ACQUIRE_SITE, 12), (AIM_CALL, 5), (REMOVE_SITE, 10)):
        neutralize_relocations(data, pe, site, length, label)

    NO_AIM = bytes.fromhex("003C1CC6")                            # -9999.0f, the game's "no aim point" value
    cave_va = ptch_va + cave_cursor
    # ---- A: runHomeLogic's target test.  A torpedo whose target was destroyed carries the marker
    #         byte 2 in its "have contact" flag [+0x3DC]; it does not go looking for a new victim.
    a = bytearray(bytes.fromhex("39878C030000"))                  # CMP [EDI+0x38C],EAX   (EAX = 0)
    a += b"\x0F\x85" + _rel32(cave_va, len(a), PRESENT, 2)           # JNE <has a target>
    a += bytes.fromhex("80BFDC03000002")                          # CMP BYTE [EDI+0x3DC],2
    a += b"\x0F\x84" + _rel32(cave_va, len(a), AFTER_ACQUIRE, 2)     # JE  <skip acquisition>
    a += b"\xE9" + _rel32(cave_va, len(a), ACQUIRE_SITE + 12, 1)      # JMP <stock acquisition>
    a_va = cave_va
    cave_va += len(a)
    # ---- B: runHomeLogic's call to runAimLogic.  A torpedo that lost its target and has no new aim
    #         point does not steer or thrust (the same idle state runTravelLogic uses), so it drifts.
    b = bytearray()
    b += bytes.fromhex("83B98C03000000")                          # CMP DWORD [ECX+0x38C],0
    jne1 = len(b); b += b"\x75\x00"
    b += bytes.fromhex("80B9DC03000002")                          # CMP BYTE [ECX+0x3DC],2
    jne2 = len(b); b += b"\x75\x00"
    b += bytes.fromhex("81B92C010000") + NO_AIM                   # CMP DWORD [ECX+0x12C],-9999.0f
    jne3 = len(b); b += b"\x75\x00"
    b += bytes.fromhex("81B930010000") + NO_AIM                   # CMP DWORD [ECX+0x130],-9999.0f
    jne4 = len(b); b += b"\x75\x00"
    b += bytes.fromhex("8B4140" "8B10" "85D2" "7404" "C6426200")   # engine slot 0 off, if present
    b += bytes.fromhex("8B4010" "85C0" "7404" "C6406200")          # engine slot 0x10 off, if present
    b += bytes.fromhex("C20800")                                  # RET 8  (runAimLogic is callee-cleaned)
    orig = len(b)
    for j in (jne1, jne2, jne3, jne4):
        b[j + 1] = orig - (j + 2)
    b += b"\xE9" + _rel32(cave_va, len(b), AIM_FUNC, 1)              # JMP runAimLogic
    b_va = cave_va
    cave_va += len(b)
    # ---- C: the weapon loop in entirelyRemoveShip.  Stock zeroes the target; also mark the torpedo
    #         "target lost" and clear its aim point, so A and B above recognise it.
    c = bytearray(bytes.fromhex("C7838C030000" "00000000"))       # MOV DWORD [EBX+0x38C],0
    c += bytes.fromhex("C683DC03000002")                          # MOV BYTE [EBX+0x3DC],2
    c += bytes.fromhex("C7832C010000") + NO_AIM                   # MOV DWORD [EBX+0x12C],-9999.0f
    c += bytes.fromhex("C78330010000") + NO_AIM                   # MOV DWORD [EBX+0x130],-9999.0f
    c += b"\xE9" + _rel32(cave_va, len(c), CONTINUE, 1)
    c_va = cave_va
    body = bytes(a + b + c)
    data[ptch_off + cave_cursor: ptch_off + cave_cursor + len(body)] = body
    cave_cursor += len(body)

    off = va_to_offset(pe, ACQUIRE_SITE)
    data[off:off + 12] = b"\xE9" + struct.pack("<i", a_va - (ACQUIRE_SITE + 5)) + b"\x90" * 7
    off = va_to_offset(pe, AIM_CALL)
    data[off:off + 5] = b"\xE8" + struct.pack("<i", b_va - (AIM_CALL + 5))
    off = va_to_offset(pe, REMOVE_SITE)
    data[off:off + 10] = b"\xE9" + struct.pack("<i", c_va - (REMOVE_SITE + 5)) + b"\x90" * 5
    print(f"  [OK] {label}")
    applied.append(label)
    return cave_cursor





# ============================================================
# Hail guard: you cannot hail anyone while your own comms are off.
#
# ShipInterface::doCommunicateWithSelected (the HAIL command) only checks that something is selected and that
# it has a comms channel; it never looks at the player's own comms module (id 0xe), so a ship with comms
# switched off (or no comms module) can still open a channel to an authority ship or a station.  The 1.0.6
# change log says outgoing hails were stopped while comms are disabled ("emergency or incoming only"), but
# nothing in the handler does that.  The guard runs first thing in the handler: if SystemManager::getModule(0xe)
# gives no module, or the module is disconnected (the flag doToggleComms tests, +0x63), the command logs
# "Comms offline: cannot hail." and returns false -- by jumping to the handler's own error exit, so the stack
# and registers are unwound exactly as for "No object selected.".  Incoming hails are not touched.
# tools/hail/test_hail.py runs it under emulation (client and server).
# ============================================================

HAIL_MSG = b"Comms offline: cannot hail.\0"


def fix_hail_guard(data, pe, ptch_va, ptch_off, cave_cursor, server=False):
    import ois_patcher
    _fix_lists = ois_patcher._fix_lists
    verify_site = ois_patcher.verify_site
    bail = ois_patcher.bail
    _rel32_target = ois_patcher._rel32_target
    _rel32 = ois_patcher._rel32
    neutralize_relocations = ois_patcher.neutralize_relocations
    va_to_offset = ois_patcher.va_to_offset

    label = "Outgoing hails need your comms module connected (personal variant)" + (" (server)" if server else "")
    applied, skipped = _fix_lists(server)
    if server:
        HOOK, GETMOD, JOIN = 0x004E553D, 0x004E7B18, 0x004E558A
    else:
        HOOK, GETMOD, JOIN = 0x004E5ACD, 0x004E80A8, 0x004E5B1A
    # mov esi,[ebx+0x19c] ; test esi,esi ; jne +7   -- the first thing the handler does with the selection
    if verify_site(data, pe, HOOK, bytes.fromhex("8BB39C010000" "85F6" "7507"), label + " (handler entry)") is None:
        return bail(label, cave_cursor, server)
    # push 0 ; push 0xe ; mov ecx,[reg+0x40] ; call getModule   (doToggleComms)
    if (verify_site(data, pe, GETMOD, bytes.fromhex("6A006A0E"), label + " (getModule args)") is None
            or verify_site(data, pe, GETMOD + 7, bytes([0xE8]), label + " (getModule call)") is None):
        return bail(label, cave_cursor, server)
    GET_MODULE = _rel32_target(data, pe, GETMOD + 7, 1)
    # push 2 ; push [ebx+0x224] ; call addLogLine  -- the shared error exit
    if verify_site(data, pe, JOIN, bytes.fromhex("6A02FFB324020000E8"), label + " (error exit)") is None:
        return bail(label, cave_cursor, server)

    cave_va = ptch_va + cave_cursor
    code = bytearray()
    code += bytes.fromhex("6A00" "6A0E" "8B4B40")                              # push 0 ; push 0xe ; mov ecx,[ebx+0x40]
    code += b"\xE8" + _rel32(cave_va, len(code), GET_MODULE, 1)                # call getModule
    code += bytes.fromhex("85C0")                                              # test eax,eax
    jz_at = len(code); code += bytes.fromhex("7400")                           # jz refuse
    code += bytes.fromhex("80786300")                                          # cmp byte [eax+0x63],0
    je_at = len(code); code += bytes.fromhex("7400")                           # je refuse
    code += bytes.fromhex("8BB39C010000")                                      # mov esi,[ebx+0x19c]   (displaced)
    code += b"\xE9" + _rel32(cave_va, len(code), HOOK + 6, 1)                  # jmp back
    refuse = len(code)
    code[jz_at + 1] = refuse - (jz_at + 2)
    code[je_at + 1] = refuse - (je_at + 2)
    code += bytes.fromhex("E800000000")                                        # call $+5
    pop_at = len(code); code += b"\x58"                                        # pop eax  (= address of this byte)
    msg_delta_at = len(code) + 1; code += bytes.fromhex("05" "00000000")       # add eax,<message - here>
    code += b"\x50"                                                            # push eax
    code += b"\xE9" + _rel32(cave_va, len(code), JOIN, 1)                      # jmp error exit (push 2 ; push [ebx+0x224] ; call)
    msg_at = len(code)
    struct.pack_into("<i", code, msg_delta_at, msg_at - pop_at)
    code += HAIL_MSG
    code += b"\x90" * (-len(code) % 4)

    data[ptch_off + cave_cursor: ptch_off + cave_cursor + len(code)] = code
    neutralize_relocations(data, pe, HOOK, 6, label)
    off = va_to_offset(pe, HOOK)
    data[off:off + 6] = b"\xE9" + struct.pack("<i", cave_va - (HOOK + 5)) + b"\x90"
    print(f"  [OK] {label}")
    applied.append(label)
    return cave_cursor + len(code)


# ============================================================
# Local news (data only): the developers said (Steam forums, 14 Mar 2019) that news articles were meant to appear only
# when you are in the right star system, and that it was on their list but never shipped.  The engine already has what
# is needed: an article's `Req:` lines (all must hold) accept any flag, and `in_sector_<id>` is true while you are in
# that sector.  So each article from a regional paper gets `Req: in_sector_<home sector>` and appears the first time you
# are in that system on or after its date (and then stays).  Papers are matched to a sector by name; papers of no
# single place (The Sentinel, The Inquirer, The Suns, The Libertarian, The Free Press, ...) stay global.  Edit the table
# to taste -- the key is the exact `Publication:` text.
#
# The news files are edited in place (mods cannot override them).  The patcher keeps pristine copies for the files it
# fixes itself; this plugin adds its one line AFTER that and strips it again at the start of every run and on uninstall,
# so the patcher's own backup logic only ever sees stock or stock-plus-its-own-fixes text.
# ============================================================

LOCAL_NEWS_SECTORS = {
    "The Magellan Courier": 0, "The Magella Herald": 0, "The Loaiso Herald": 0, "Loaiso Herald": 0,   # Magella (Loaiso is in it)
    "The Penitent Times": 1, "The Crassus Lens": 1, "The Globe": 1, "The Leon Marker": 1,             # Leo
    "The Tegan Mirror": 3,                                                                              # Tega
    "The Cansan Sentinel": 4,                                                                           # Cansa
    "The Diwali Examiner": 5,                                                                           # Diwali
    "The Galilean Post": 6,                                                                             # Galileo
    "The Lights": 8,                                                                                    # Sagan's Lights
    "The Parssusian Worker": 9, "The Age of Parssus": 9, "Age of Parssus": 9,                          # Parssus
    "The Sisters Post": 11,                                                                             # Two Sisters
}
_PUBLICATION = re.compile(r"^Publication:[ \t]*(.*?)[ \t]*\r?$", re.M)
_SECTOR_REQ = re.compile(r"^Req:[ \t]*in_sector_\d+", re.M)
# Five stock articles already carry their own `Req: in_sector_N` (found on the full game data).  They are event articles
# (a theatre review that needs sector 3 although its paper is mapped to sector 1, ...), so a second, different sector
# requirement would AND to "in two sectors at once" and the article would never appear.  Never touched, either way.
STOCK_SECTOR_FILES = {"news_weunhappyfewwebandofsuckers.txt", "news_editorialonposttheatre.txt",
                      "news_theatrereviewtheproximacentauriplayers.txt", "news_authoritiesbaffledbyactors.txt",
                      "news_ilongedfordeathbeforeoedipusdid.txt"}


def local_news_line(text):
    """(publication line, the line this plugin appends after it) for a regional article, else None."""
    pubs = _PUBLICATION.findall(text)
    if len(pubs) != 1 or pubs[0] not in LOCAL_NEWS_SECTORS:
        return None
    m = _PUBLICATION.search(text)
    return m.group(0).rstrip("\r"), f"Req: in_sector_{LOCAL_NEWS_SECTORS[pubs[0]]}"


def has_local_news(text):
    """True when this plugin's line is present right after the Publication line."""
    hit = local_news_line(text)
    if hit is None:
        return False
    eol = "\r\n" if "\r\n" in text else "\n"
    return hit[0] + eol + hit[1] in text


def add_local_news(text):
    """text with the regional line added (unchanged for a global article, one that already has it, or one that
    already carries a sector requirement of its own)."""
    hit = local_news_line(text)
    if hit is None or _SECTOR_REQ.search(text):
        return text
    pub, req = hit
    eol = "\r\n" if "\r\n" in text else "\n"
    return text.replace(pub, pub + eol + req, 1)


def strip_local_news(text):
    """Exactly undoes add_local_news."""
    if not has_local_news(text):
        return text
    pub, req = local_news_line(text)
    eol = "\r\n" if "\r\n" in text else "\n"
    return text.replace(pub + eol + req, pub, 1)


def _news_files(game_dir):
    return sorted(f for f in (Path(game_dir) / "assets").glob("news_*.txt") if f.name not in STOCK_SECTOR_FILES)


def _rewrite_news(game_dir, fn):
    """Applies fn to every news file; returns how many changed."""
    n = 0
    for f in _news_files(game_dir):
        old = f.read_bytes().decode("utf-8")
        new = fn(old)
        if new != old:
            f.write_bytes(new.encode("utf-8"))
            n += 1
    return n


# ============================================================
# Optional DLL refresh (dll_update.py, a port of OIS-Update's Patch_OIS.bat).
# Only offered when an OIS-Update package is actually on disk: an `OIS-Update` (or `OIS-Update-dev`) folder
# next to ois_patcher.py, in or beside the game folder, or the folder named by %OIS_UPDATE_DIR%.  Nothing is
# downloaded.  The player is asked once, before anything is patched; --yes answers yes.  The DLLs are copied
# after the rest of the install, so a failed exe patch never leaves half an update behind.
# ============================================================

_dll = {"pkg": None, "go": False, "result": None}


def _dll_module():
    try:
        import dll_update
    except ModuleNotFoundError as e:
        if e.name != "dll_update":
            raise
        return None
    return dll_update


def _dll_current(du, game_dir, pkg):
    return all((game_dir / n).is_file() and du.sha256_file(game_dir / n) == s for n, s in pkg.game)


def _dll_ask(game_dir, assume_yes):
    du = _dll_module()
    _dll.update(pkg=None, go=False, result=None)
    if du is None:
        return
    game_dir = Path(game_dir)
    du.add_search_dir(game_dir)
    pkg = du.find_local_package()
    if pkg is None:
        return
    missing, bad = du.check_package(pkg)
    print(f"\nOIS-Update package {pkg.version} found at {pkg.root}")
    if missing or bad:
        print(f"  [SKIP] It is incomplete ({len(missing)} missing, {len(bad)} with the wrong SHA256); "
              "the DLLs will not be touched.")
        return
    if _dll_current(du, game_dir, pkg):
        print("  The game's DLLs already match it; nothing to do.")
        return
    print("  It replaces the game's bundled DLLs with newer ones (originals are backed up to "
          f"{du.BACKUP_DIRNAME}/ and put back by --uninstall).")
    if assume_yes:
        go = True
    elif sys.stdin.isatty():
        try:
            go = input("  Also update the game's DLLs from it? [y/N]: ").strip().lower() in ("y", "yes")
        except (EOFError, KeyboardInterrupt):
            print()
            go = False
    else:
        print("  [SKIP] Not an interactive session; re-run with --yes to apply it.")
        go = False
    _dll.update(pkg=pkg if go else None, go=go)


def _dll_install(game_dir):
    if not _dll["go"]:
        return
    du = _dll_module()
    print("\nUpdating the game's DLLs...")
    ok = du.install(Path(game_dir), package=_dll["pkg"])
    _dll["result"] = ok
    print(f"  [{'OK' if ok else 'FAILED'}] DLL update" + ("" if ok else " (see above; the game's other fixes are unaffected)"))


def begin_run(game_dir, assume_yes=False, **kwargs):
    n = _rewrite_news(game_dir, strip_local_news)
    if n:
        print(f"  (local news: lifted from {n} article(s) before patching; re-added afterwards)")
    _dll_ask(game_dir, assume_yes)


def post_install(game_dir):
    n = _rewrite_news(game_dir, add_local_news)
    if n:
        print(f"  [OK] Local news: {n} regional article(s) now need you to be in their system")
    _dll_install(game_dir)


def summary_lines():
    if not _dll["go"]:
        return []
    return [f"DLL update: {'applied' if _dll['result'] else 'FAILED, see above'}"]


def status_lines(game_dir):
    n = sum(1 for f in _news_files(game_dir) if has_local_news(f.read_bytes().decode("utf-8")))
    lines = [f"  {'local news':<16} {f'{n} regional article(s) gated by sector' if n else 'not applied'}"]
    du = _dll_module()
    if du is not None:
        du.add_search_dir(game_dir)
        lines += du.status_lines(game_dir)
        pkg = du.find_local_package()
        if pkg is not None and not _dll_current(du, Path(game_dir), pkg):
            lines.append(f"  {'':<16} OIS-Update {pkg.version} is available at {pkg.root}; run the patcher to apply it")
    return lines


def uninstall_plan(game_dir):
    plan = []
    if any(has_local_news(f.read_bytes().decode("utf-8")) for f in _news_files(game_dir)):
        plan.append("remove the local-news sector requirement from the news articles in assets/")
    du = _dll_module()
    if du is not None:
        du.add_search_dir(game_dir)
        plan += du.uninstall_plan(game_dir)
    return plan


def uninstall(game_dir, keep_backups=False):
    n = _rewrite_news(game_dir, strip_local_news)
    print(f"  removed the local-news requirement from {n} article(s)")
    du = _dll_module()
    if du is not None:
        du.add_search_dir(game_dir)
        return bool(du.uninstall(Path(game_dir), keep_backups))
    return True
