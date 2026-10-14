#!/usr/bin/env python3
"""Assembles the three point-defence caves (see fix_pds_torpedoes in ois_patcher.py).

Developer tool -- the patcher itself carries the finished bytes and does not
need keystone.  Run this to regenerate / double-check them:

    pip install keystone-engine
    python3 tools/pds/asm_pds.py

Each cave is assembled twice at different base addresses; every byte that
differs is a rel32 operand pointing outside the cave, i.e. a fixup the patcher
resolves once it knows where the cave landed.
"""
import sys
from keystone import Ks, KS_ARCH_X86, KS_MODE_32

# ---- original-exe addresses (client ois.exe 1.0.7) ------------------------
GSWD            = 0x004A6D10   # GameData::getShipWithinDistance (stdcall, ret 0x14)
GSWD_PASS       = 0x004A6DAF   # inside it: "this ship is a candidate"
GSWD_SKIP       = 0x004A6E37   # inside it: "next ship"
PDS_AFTER_SHOT  = 0x004AF9CA   # ShipModule::runLogic: shake + sound + start reload

SOURCES = {}

# 1. Candidate filter inside getShipWithinDistance.  Replaces the 32 bytes at
#    0x4A6D8F.  Entered with ECX = ship, BL = flag argument, ESI = sector,
#    [EBP+0xC] = the ship that owns the PDS.  Only the PDS passes a non-zero flag.
SOURCES["filter"] = f"""
    test    bl, bl
    je      {GSWD_PASS}                   # flag 0: every ship (all other callers, unchanged)
    mov     eax, [ecx+0x254]              # ShipClass*
    test    eax, eax
    je      ship
    cmp     dword ptr [eax+0x158], 4      # vessel type 4: torpedo / probe / mine
    jne     ship
    cmp     byte ptr [ecx+0x3cc], 0       # a weapon that is already destroyed
    jne     {GSWD_SKIP}
    mov     eax, [ecx+0x39c]              # launching ship
    cmp     eax, [ebp+0xc]                # ours? the PDS must not shoot our own weapons
    je      {GSWD_SKIP}
    jmp     {GSWD_PASS}                   # a hostile weapon: stock rule, always a candidate
ship:
    cmp     bl, 2                         # pass 1 asks for weapons only
    je      {GSWD_SKIP}
    mov     eax, [ecx+0x40]
    cmp     byte ptr [eax+0x34], 0        # stock rule for ships: only if the IFF transponder is off
    je      {GSWD_PASS}
    jmp     {GSWD_SKIP}
"""

# 2. Target selection.  Replaces `call getShipWithinDistance` in the PDS code.
#    Same stack protocol (5 dwords, callee pops), range in XMM2.  Looks for
#    weapons first, then ships.
SOURCES["select"] = f"""
    sub     esp, 4
    movss   [esp], xmm2                   # remember the range
    push    dword ptr [esp+0x18]          # Vec2.y
    push    dword ptr [esp+0x18]          # Vec2.x
    push    2                             # pass 1: weapons only
    push    dword ptr [esp+0x18]          # PDS ship
    push    dword ptr [esp+0x18]          # sector id
    movss   xmm2, [esp+0x14]
    call    {GSWD}
    test    eax, eax
    jne     done
    push    dword ptr [esp+0x18]
    push    dword ptr [esp+0x18]
    push    1                             # pass 2: ships
    push    dword ptr [esp+0x18]
    push    dword ptr [esp+0x18]
    movss   xmm2, [esp+0x14]
    call    {GSWD}
done:
    add     esp, 4
    ret     0x14
"""

# 3. Delivering the shot.  Replaces `mov ecx,edi / push eax / call [edx+0xc]`
#    (Ship::damage).  The stock call is a no-op on torpedoes (Ship::damage
#    returns early for vessel type 4), which is why the PDS never stopped one.
SOURCES["damage"] = """
    mov     ecx, edi
    mov     eax, [ecx+0x254]
    test    eax, eax
    je      ship
    cmp     dword ptr [eax+0x158], 4
    jne     ship
    mov     byte ptr [ecx+0x3cc], 1       # weapon destroyed (no warhead blast at point-blank range)
    ret     0x10
ship:
    mov     eax, [ecx]
    jmp     dword ptr [eax+0xc]           # Ship::damage, original stack
"""


def assemble(name, base):
    ks = Ks(KS_ARCH_X86, KS_MODE_32)
    enc, _ = ks.asm(SOURCES[name], base)
    return bytes(enc)


def build(name):
    """-> (machine code, [(offset of rel32 operand, absolute target VA)])
    for every call/jump that leaves the cave."""
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32, CS_GRP_JUMP, CS_GRP_CALL
    base = 0x00700000
    code = assemble(name, base)
    cs = Cs(CS_ARCH_X86, CS_MODE_32)
    cs.detail = True
    fixups = []
    for ins in cs.disasm(code, base):
        if (CS_GRP_JUMP in ins.groups or CS_GRP_CALL in ins.groups) and ins.op_str.startswith("0x"):
            target = int(ins.op_str, 16)
            if not (base <= target < base + len(code)):
                assert ins.size - ins.address + ins.address >= 5
                fixups.append((ins.address - base + ins.size - 4, target))
    return code, fixups


SYMBOLS = {GSWD: "GSWD", GSWD_PASS: "PASS", GSWD_SKIP: "SKIP", PDS_AFTER_SHOT: "AFTER_SHOT"}


def emit_python():
    out = []
    for name in SOURCES:
        code, fixups = build(name)
        out.append(f"{name.upper()}_CAVE = bytes.fromhex(")
        h = code.hex()
        for i in range(0, len(h), 64):
            out.append(f'    "{h[i:i+64]}"')
        out.append(")")
        out.append(f"{name.upper()}_FIXUPS = [" + ", ".join(f'({p:#x}, "{SYMBOLS[t]}")' for p, t in fixups) + "]")
        out.append("")
    return "\n".join(out)


if __name__ == "__main__":
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    cs = Cs(CS_ARCH_X86, CS_MODE_32)
    if "--check" in sys.argv:
        # the bytes embedded in ois_patcher.py must be exactly what this source assembles to
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
        import ois_patcher
        bad = 0
        for name in SOURCES:
            code, fixups = build(name)
            same = (ois_patcher.__dict__[name.upper() + "_CAVE"] == code
                    and ois_patcher.__dict__[name.upper() + "_FIXUPS"] == [(p, SYMBOLS[t]) for p, t in fixups])
            print(f"{'ok ' if same else 'DIFF'} {name}")
            bad += not same
        sys.exit(1 if bad else 0)
    if "--python" in sys.argv:
        print(emit_python())
        sys.exit(0)
    for name in SOURCES:
        code = assemble(name, 0x00700000)
        print(f"== {name}: {len(code)} bytes")
        print(code.hex())
        if "-v" in sys.argv:
            for ins in cs.disasm(code, 0x00700000):
                print(f"   {ins.address:08x}: {ins.mnemonic} {ins.op_str}")
