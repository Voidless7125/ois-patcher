#!/usr/bin/env python3
"""Assembles the three PDS caves (see fix_pds_target_everything in ois_patcher.py).

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
GET_EFFICIENCY  = 0x00437E40   # ComponentInterfaceInstance::getEfficiencyPercent (thiscall)
PDS_AFTER_SHOT  = 0x004AF9CA   # ShipModule::runLogic: shake + sound + start reload
PDS_NO_TARGET   = 0x004AFA5C   # ShipModule::runLogic: nothing to shoot
PDS_HIT_PATH    = 0x004AF843   # ShipModule::runLogic: the roll succeeded
PDS_MISS_PATH   = 0x004AF9AF   # ShipModule::runLogic: the roll failed ("miss")

SOURCES = {}

# 1. Candidate filter inside getShipWithinDistance.  Replaces the 32 bytes at
#    0x4A6D8F.  Entered with ECX = ship, BL = flag argument, ESI = sector,
#    [EBP+0xC] = the ship that owns the PDS.  Only the PDS passes a non-zero flag.
SOURCES["filter"] = f"""
    test    bl, bl
    je      {GSWD_PASS}                   # flag 0: every ship (all other callers, unchanged)
    mov     eax, [ecx+0x254]              # ShipClass*
    test    eax, eax
    je      {GSWD_SKIP}
    mov     eax, [eax+0x158]              # vessel type: 0 ship, 1 station, 2 gate, 4 torpedo/probe/mine
    cmp     bl, 2
    je      weapons
    test    eax, eax                      # flag 1: ordinary ships only (never stations / gates)
    jne     {GSWD_SKIP}
    cmp     dword ptr [ecx+0xd4], 3       # not one that is docked
    jne     {GSWD_PASS}
    cmp     dword ptr [ecx+0xf8], 2
    je      {GSWD_SKIP}
    jmp     {GSWD_PASS}
weapons:
    cmp     eax, 4                        # flag 2: torpedoes, probes, mines
    jne     {GSWD_SKIP}
    cmp     byte ptr [ecx+0x3cc], 0       # already destroyed
    jne     {GSWD_SKIP}
    mov     eax, [ecx+0x39c]              # launching ship
    cmp     eax, [ebp+0xc]                # ours? leave our own weapons alone
    je      {GSWD_SKIP}
    jmp     {GSWD_PASS}
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

# 3b. The hit roll.  Replaces `cmp [ebp-0x40],1 / jne miss` (10 bytes).  The roll
#    models a laser missing a manoeuvring ship; a locked torpedo is simply shot down.
SOURCES["roll"] = f"""
    mov     eax, [ebp-0x3c]               # the target chosen above
    mov     ecx, [eax+0x254]
    test    ecx, ecx
    je      roll
    cmp     dword ptr [ecx+0x158], 4
    je      {PDS_HIT_PATH}
roll:
    cmp     dword ptr [ebp-0x40], 1
    jne     {PDS_MISS_PATH}
    jmp     {PDS_HIT_PATH}
"""

# 4. Countermeasures.  Entered instead of "no target": ESI = ship, EBX = module.
SOURCES["countermeasure"] = f"""
    sub     esp, 0x10
    mov     ecx, [ebx+0xc]
    call    {GET_EFFICIENCY}
    movd    xmm0, eax
    cvtdq2ps xmm0, xmm0
    mov     eax, 0x42c80000               # 100.0f
    movd    xmm2, eax
    divss   xmm0, xmm2
    mov     eax, [ebx+8]
    movss   xmm1, [eax+0x104]
    mulss   xmm1, xmm0                    # range
    mulss   xmm1, xmm1                    # range squared
    movsd   xmm4, [esi+0x28]
    cvtpd2ps xmm4, xmm4
    movsd   xmm5, [esi+0x30]
    cvtpd2ps xmm5, xmm5                   # our position
    mov     eax, [esi+0x24]               # Sector*
    test    eax, eax
    je      none
    mov     ecx, [eax+0x9c]               # synthetic objects: begin
    mov     edx, [eax+0xa0]               #                    end
    mov     [esp], ecx
    mov     [esp+4], edx
next:
    mov     ecx, [esp]
    cmp     ecx, [esp+4]
    je      none
    add     dword ptr [esp], 4
    mov     eax, [ecx]                    # object
    cmp     dword ptr [eax+0x60], 3       # countermeasure?
    jne     next
    cmp     dword ptr [eax+0xf4], 0       # timer already run out (about to be removed)?
    jle     next
    movsd   xmm2, [eax+0x28]
    cvtpd2ps xmm2, xmm2
    movsd   xmm3, [eax+0x30]
    cvtpd2ps xmm3, xmm3
    subss   xmm2, xmm4
    subss   xmm3, xmm5
    mulss   xmm2, xmm2
    mulss   xmm3, xmm3
    addss   xmm2, xmm3
    comiss  xmm1, xmm2
    jb      next                          # out of range
    mov     edx, [eax+0x78]               # owner's registration vs ours
    cmp     edx, [esi+0x248]
    jne     found                         # different length: not ours
    test    edx, edx
    je      next                          # both empty: treat as ours
    push    esi
    push    edi
    lea     edi, [eax+0x68]
    cmp     dword ptr [eax+0x7c], 0x10
    jb      mine_ok
    mov     edi, [edi]
mine_ok:
    lea     ecx, [esi+0x238]
    cmp     dword ptr [esi+0x24c], 0x10
    jb      ours_ok
    mov     ecx, [ecx]
ours_ok:
    mov     esi, ecx
    mov     ecx, edx
    repe cmpsb
    pop     edi
    pop     esi
    je      next                          # identical: our own decoy
found:
    mov     dword ptr [eax+0xf4], 0       # decoy timer expires -> removed on its next tick
    add     esp, 0x10
    jmp     {PDS_AFTER_SHOT}
none:
    add     esp, 0x10
    jmp     {PDS_NO_TARGET}
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


SYMBOLS = {GSWD: "GSWD", GSWD_PASS: "PASS", GSWD_SKIP: "SKIP", GET_EFFICIENCY: "EFFICIENCY",
           PDS_AFTER_SHOT: "AFTER_SHOT", PDS_NO_TARGET: "NO_TARGET", PDS_HIT_PATH: "HIT", PDS_MISS_PATH: "MISS"}


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
