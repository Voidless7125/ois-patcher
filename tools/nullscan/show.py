import sys, pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
pe = pefile.PE(sys.argv[1]); base = pe.OPTIONAL_HEADER.ImageBase
md = Cs(CS_ARCH_X86, CS_MODE_32)
def show(va, before=0x10, n=24):
    for s in pe.sections:
        if s.VirtualAddress+base <= va < s.VirtualAddress+base+s.Misc_VirtualSize:
            off = va - base - s.VirtualAddress - before
            d = s.get_data()[off:off+before+n*6]
            for i in list(md.disasm(d, va-before))[:n+before//3]:
                print("%s%08x  %s %s" % (">" if i.address==va else " ", i.address, i.mnemonic, i.op_str))
for a in sys.argv[2:]:
    print("----", a); show(int(a,16))
