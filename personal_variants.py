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
import struct

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



