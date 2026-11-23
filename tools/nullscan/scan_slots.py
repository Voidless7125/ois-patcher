"""Slot-array scan: loads of a component/addon slot (module+0xc array, element at
[+4+slot*4] / [+0x54+slot*4] / [-0x13c+...]) that are dereferenced before any test.
Usage: scan_slots.py <ois.exe> <ois.pdb> [out.json]"""
import re, sys, json
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from capstone.x86 import X86_OP_REG, X86_OP_MEM
from pdbsyms import load_publics

exe, pdb = sys.argv[1], sys.argv[2]
pe = pefile.PE(exe); base = pe.OPTIONAL_HEADER.ImageBase
t = [s for s in pe.sections if s.Name.startswith(b".text")][0]
tva = base + t.VirtualAddress; tdata = t.get_data()
pubs = load_publics(pdb, tva); starts = sorted(pubs)
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = True
SLOT_DISPS = {4, 0x54, -0x13c}
R = md.reg_name

def short(m):
    mm = re.match(r"\?([^@]+)@([^@]+)@@", m)
    return "%s::%s" % (mm.group(2), mm.group(1)) if mm else m

def regs(op):
    s = set()
    if op.type == X86_OP_MEM:
        if op.mem.base: s.add(R(op.mem.base))
        if op.mem.index: s.add(R(op.mem.index))
    return s

hits = []
for n, va in enumerate(starts):
    if not (tva <= va < tva + len(tdata)): continue
    end = starts[n + 1] if n + 1 < len(starts) else tva + len(tdata)
    ins = list(md.disasm(tdata[va - tva:end - tva], va))
    arr = {}   # reg -> addr where it got module+0xc
    for k, i in enumerate(ins):
        o = i.operands
        if i.mnemonic == "mov" and len(o) == 2 and o[0].type == X86_OP_REG and o[1].type == X86_OP_MEM \
                and o[1].mem.disp == 0xc and o[1].mem.base and not o[1].mem.index:
            arr[R(o[0].reg)] = k
            continue
        if i.mnemonic == "mov" and len(o) == 2 and o[0].type == X86_OP_REG and o[1].type == X86_OP_MEM \
                and o[1].mem.index and o[1].mem.scale == 4 and o[1].mem.disp in SLOT_DISPS \
                and o[1].mem.base and R(o[1].mem.base) in arr and k - arr[R(o[1].mem.base)] < 30:
            # slot element loaded into o[0]; follow it
            tr = {R(o[0].reg)}
            for j in ins[k + 1:k + 25]:
                jo = j.operands
                if j.mnemonic in ("test", "cmp") and jo and jo[0].type == X86_OP_REG and R(jo[0].reg) in tr:
                    break
                if any(regs(x) & tr for x in jo if x.type == X86_OP_MEM) and j.mnemonic != "lea":
                    hits.append({"fn": short(pubs[va]), "va": va, "load": i.address, "use": j.address,
                                 "text": "%s %s" % (j.mnemonic, j.op_str)})
                    break
                if j.mnemonic in ("ret", "jmp", "call"): break
                if j.mnemonic == "mov" and len(jo) == 2 and jo[0].type == X86_OP_REG:
                    d = R(jo[0].reg)
                    if jo[1].type == X86_OP_REG and R(jo[1].reg) in tr: tr.add(d)
                    else: tr.discard(d)
                    if not tr: break
for h in hits:
    print("%08x %-45s load %08x use %08x %s" % (h["va"], h["fn"][:45], h["load"], h["use"], h["text"]))
print(len(hits), "candidates")
if len(sys.argv) > 3: json.dump(hits, open(sys.argv[3], "w"), indent=1)
