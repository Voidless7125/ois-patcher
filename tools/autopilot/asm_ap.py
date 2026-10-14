#!/usr/bin/env python3
"""Assembles the autopilot overshoot cave (see fix_autopilot_overshoot in ois_patcher.py).

    pip install keystone-engine
    python3 tools/autopilot/asm_ap.py          # prints the bytes and the fixup offset

Entered in place of the 30 bytes that compute the braking heading (angle to the final waypoint + 180)
in the autopilot's "decelerate" state.  EBX = waypoint list, EDI = ship, [EBP-0x10] = angle to waypoint.
Leaves the heading in XMM1; XMM3 (distance) must survive, so only XMM0-2/5/6 are touched.
"""
import struct
import sys
from keystone import Ks, KS_ARCH_X86, KS_MODE_32

SOURCE = """
    movss   xmm1, [ebp-0x10]
    mov     eax, [ebx]
    cvtps2pd xmm0, qword ptr [eax+8]       # waypoint (x, y)
    movsd   xmm5, [edi+0x28]
    movhpd  xmm5, [edi+0x30]               # ship (x, y)
    subpd   xmm0, xmm5                     # vector to the waypoint
    cvtps2pd xmm6, qword ptr [edi+0x118]   # velocity
    mulpd   xmm0, xmm6
    movapd  xmm6, xmm0
    unpckhpd xmm6, xmm6
    addsd   xmm0, xmm6                     # dot(to waypoint, velocity)
    xorpd   xmm6, xmm6
    comisd  xmm0, xmm6
    jb      done                           # already past it and moving away: thrust TOWARDS it to brake
    mov     eax, 0x43340000                # 180.0f
    movd    xmm6, eax
    addss   xmm1, xmm6                     # moving towards it: face away from it (retro burn), as before
    mov     eax, 0x43b40000                # 360.0f
    movd    xmm6, eax
    comiss  xmm1, xmm6
    jb      done
    subss   xmm1, xmm6
done:
    jmp     0x00700000
"""


def build():
    enc, _ = Ks(KS_ARCH_X86, KS_MODE_32).asm(SOURCE, 0x00600000)
    code = bytes(enc)
    # the final JMP rel32 is the only external reference
    assert code[-5] == 0xE9
    return code[:-5]            # the patcher appends its own JMP back


if __name__ == "__main__":
    code = build()
    h = code.hex()
    print("AUTOPILOT_CAVE = bytes.fromhex(")
    for i in range(0, len(h), 64):
        print(f'    "{h[i:i+64]}"')
    print(")")
