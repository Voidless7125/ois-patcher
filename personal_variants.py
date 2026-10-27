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
    
    cave_cursor = fix_torpedo_lost_target(data, pe, ptch_va, ptch_off, cave_cursor, server)
    
    return cave_cursor

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



