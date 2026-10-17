#!/usr/bin/env python3
"""Assembles the wrapper for the --debug-iff diagnostic (see fix_iff_debug in ois_patcher.py).
Developer tool: the patcher carries the finished bytes.

    pip install keystone-engine
    python3 asm_iff.py            # print the cave as hex + the fixup offsets
    python3 asm_iff.py --check    # verify the bytes embedded in the patcher match this source
"""
import sys
from keystone import Ks, KS_ARCH_X86, KS_MODE_32

PRINT = b"\xA1\xA1\xA1\xA1"   # placeholder for the rel32 of `call debugPrint`
RUN = b"\xB2\xB2\xB2\xB2"     # placeholder for the rel32 of `call ShipBehaviour::runLogic`

CAT = b"GAME\0"
FMT = b"IFFDBG %s: IFF %d -> %d, changed %s the AI update\0"
PHASES = b"outside\0inside\0\0"          # two 8-byte entries
FMT_AT, PHASES_AT = len(CAT), len(CAT) + len(FMT)


def _bytes(b):
    return ".byte " + ", ".join(hex(x) for x in b)


SOURCE = f"""
wrapper:
    push    esi
    push    ebx
    push    edi
    sub     esp, 8
    movss   dword ptr [esp], xmm1        # the frame time (runLogic takes it in XMM1)
    mov     esi, ecx                     # the ShipBehaviour
    xor     edi, edi                     # 0: seen outside the AI update
    call    chk
    movss   xmm1, dword ptr [esp]
    mov     ecx, esi
    .byte   0xE8, 0xB2, 0xB2, 0xB2, 0xB2     # call ShipBehaviour::runLogic
    mov     edi, 1                       # 1: seen inside the AI update
    call    chk
    add     esp, 8
    pop     edi
    pop     ebx
    pop     esi
    ret
chk:
    mov     eax, [esi+0x6c]              # the ship
    test    eax, eax
    jz      done
    mov     ecx, [eax+0x40]              # its SystemManager
    test    ecx, ecx
    jz      done
    movzx   edx, byte ptr [ecx+0x34]     # the IFF flag
    inc     edx                          # remembered as 1 (off) / 2 (on); 0 = not seen yet
    movzx   ecx, byte ptr [esi+0x162]
    mov     byte ptr [esi+0x162], dl
    cmp     ecx, edx
    je      done
    dec     ecx                          # -1 on the first sighting
    dec     edx
    call    over                         # pushes the address of the strings that follow
{_bytes(CAT + FMT + PHASES)}
over:
    pop     ebx
    shl     edi, 3
    lea     edi, [ebx + edi + {PHASES_AT}]
    push    edi                          # which phase
    push    edx                          # new value
    push    ecx                          # old value
    lea     ecx, [eax+8]                 # ship name (std::string, small-string optimisation)
    cmp     dword ptr [eax+0x1c], 0x10
    jb      inl
    mov     ecx, [ecx]
inl:
    push    ecx
    lea     ecx, [ebx + {FMT_AT}]
    push    ecx
    push    ebx                          # category "GAME"
    .byte   0xE8, 0xA1, 0xA1, 0xA1, 0xA1     # call debugPrint
    add     esp, 24
done:
    ret
"""



def build():
    code = bytes(Ks(KS_ARCH_X86, KS_MODE_32).asm(SOURCE)[0])
    assert code.count(PRINT) == 1 and code.count(RUN) == 1
    return code, code.index(PRINT), code.index(RUN)


if __name__ == "__main__":
    code, pr, run = build()
    if "--check" in sys.argv:
        sys.path.insert(0, "../..")
        import ois_patcher
        assert code == ois_patcher.IFF_DEBUG_CAVE and (pr, run) == (ois_patcher.IFF_DEBUG_PRINT_AT, ois_patcher.IFF_DEBUG_RUN_AT)
        print("embedded bytes match")
    else:
        print(len(code), "bytes; debugPrint rel32 at", pr, "runLogic rel32 at", run)
        print(code.hex())
