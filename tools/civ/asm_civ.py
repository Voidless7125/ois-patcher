#!/usr/bin/env python3
"""Assembles the cave for the --civilians-comply variant (see fix_civilians_comply in
ois_patcher.py).  Developer tool: the patcher carries the finished bytes.

    pip install keystone-engine capstone
    python3 tools/civ/asm_civ.py            # print
    python3 tools/civ/asm_civ.py --python   # the tables embedded in the patcher
    python3 tools/civ/asm_civ.py --check    # verify the embedded bytes match this source
"""
import struct
import sys
from keystone import Ks, KS_ARCH_X86, KS_MODE_32

# ShipBehaviour::respondToPirateDemand (client 0x504B10, server 0x5043F0):
SEEN     = 0x00504E56   # "a torpedo is close": sets the flag and boosts the chance
CONTINUE = 0x00504DBC   # ... carry on with the roll using EBX as the chance

RADIUS = 250.0          # how far from the civilian one of YOUR live torpedoes still counts
R2 = struct.unpack("<I", struct.pack("<f", RADIUS * RADIUS))[0]

SOURCE = f"""
    mov     eax, [ebp+8]                  # the ship making the demand
    mov     eax, [eax+0x24]               # its sector
    test    eax, eax
    je      none
    mov     edi, [eax+0xcc]               # sector vessels: begin
    mov     ebx, [eax+0xd0]               #                 end
    mov     ecx, [esi+0x6c]               # the civilian
    movsd   xmm4, [ecx+0x28]
    cvtpd2ps xmm4, xmm4
    movsd   xmm5, [ecx+0x30]
    cvtpd2ps xmm5, xmm5
    mov     eax, {R2:#x}
    movd    xmm1, eax                     # radius squared
next:
    cmp     edi, ebx
    je      none
    mov     ecx, [edi]
    add     edi, 4
    mov     eax, [ecx+0x254]
    test    eax, eax
    je      next
    cmp     dword ptr [eax+0x158], 4      # a weapon...
    jne     next
    mov     eax, [ebp+8]
    cmp     [ecx+0x39c], eax              # ...launched by the demander...
    jne     next
    cmp     byte ptr [ecx+0x3cc], 0       # ...that is still in flight
    jne     next
    movsd   xmm2, [ecx+0x28]
    cvtpd2ps xmm2, xmm2
    movsd   xmm3, [ecx+0x30]
    cvtpd2ps xmm3, xmm3
    subss   xmm2, xmm4
    subss   xmm3, xmm5
    mulss   xmm2, xmm2
    mulss   xmm3, xmm3
    addss   xmm2, xmm3
    comiss  xmm1, xmm2
    jb      next                          # too far from the civilian
    jmp     {SEEN}
none:
    mov     ebx, [ebp-0x14]               # what the stock code does here
    mov     edi, 0x64
    jmp     {CONTINUE}
"""
SYMBOLS = {SEEN: "SEEN", CONTINUE: "CONTINUE"}


def assemble(base):
    enc, _ = Ks(KS_ARCH_X86, KS_MODE_32).asm(SOURCE, base)
    return bytes(enc)


def build():
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32, CS_GRP_JUMP, CS_GRP_CALL
    base = 0x00700000
    code = assemble(base)
    cs = Cs(CS_ARCH_X86, CS_MODE_32)
    cs.detail = True
    fixups = []
    for ins in cs.disasm(code, base):
        if (CS_GRP_JUMP in ins.groups or CS_GRP_CALL in ins.groups) and ins.op_str.startswith("0x"):
            t = int(ins.op_str, 16)
            if not (base <= t < base + len(code)):
                fixups.append((ins.address - base + ins.size - 4, t))
    return code, fixups


def emit_python():
    code, fixups = build()
    h = code.hex()
    lines = ["CIVILIAN_TORPEDO_CAVE = bytes.fromhex("]
    lines += [f'    "{h[i:i+64]}"' for i in range(0, len(h), 64)]
    lines += [")", "CIVILIAN_TORPEDO_FIXUPS = [" + ", ".join(f'({p:#x}, "{SYMBOLS[t]}")' for p, t in fixups) + "]"]
    return "\n".join(lines)


if __name__ == "__main__":
    if "--python" in sys.argv:
        print(emit_python())
    elif "--check" in sys.argv:
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
        import ois_patcher
        code, fixups = build()
        ok = (ois_patcher.CIVILIAN_TORPEDO_CAVE == code
              and ois_patcher.CIVILIAN_TORPEDO_FIXUPS == [(p, SYMBOLS[t]) for p, t in fixups])
        print("ok " if ok else "DIFF", "civilian torpedo cave")
        sys.exit(0 if ok else 1)
    else:
        from capstone import Cs, CS_ARCH_X86, CS_MODE_32
        code = assemble(0x00700000)
        print(f"{len(code)} bytes")
        for i in Cs(CS_ARCH_X86, CS_MODE_32).disasm(code, 0x00700000):
            print(f"  {i.address:08x}: {i.mnemonic} {i.op_str}")
