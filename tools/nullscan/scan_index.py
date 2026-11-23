"""Unchecked-index scan: a stack argument (ebp+8/0xc/..) used as an array index in a memory
operand before any cmp/test on it. Mail crash (Fix 43) was exactly this.
Usage: scan_index.py <ois.exe> <ois.pdb> [out.json]"""
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
R = md.reg_name
def short(m):
    mm = re.match(r"\?([^@]+)@([^@]+)@@", m)
    return "%s::%s" % (mm.group(2), mm.group(1)) if mm else m
UI = re.compile(r"(UI_|Screen|Interface|ComputerSystem|Network|Tablet|Menu)")
hits = []
for n, va in enumerate(starts):
    if not (tva <= va < tva + len(tdata)) or "$" in pubs[va]: continue
    end = starts[n + 1] if n + 1 < len(starts) else tva + len(tdata)
    ins = list(md.disasm(tdata[va - tva:end - tva], va))
    if not ins or ins[0].mnemonic != "push" or ins[0].op_str != "ebp": continue   # ebp frames only
    tr = {}   # reg -> arg disp
    guarded = set()
    for k, i in enumerate(ins[:70]):
        o = i.operands; mn = i.mnemonic
        if mn in ("jmp", "ret", "call") and mn != "call": break
        if mn == "call":
            tr = {r: d for r, d in tr.items() if r in ("ebx", "esi", "edi")}
        # arg load
        if mn == "mov" and len(o) == 2 and o[0].type == X86_OP_REG and o[1].type == X86_OP_MEM \
                and o[1].mem.base and R(o[1].mem.base) == "ebp" and 8 <= o[1].mem.disp <= 0x14 and not o[1].mem.index:
            tr[R(o[0].reg)] = o[1].mem.disp; continue
        # cmp/test on arg (reg or memory)
        if mn in ("cmp", "test") and o:
            if o[0].type == X86_OP_REG and R(o[0].reg) in tr: guarded.add(tr[R(o[0].reg)])
            if o[0].type == X86_OP_MEM and o[0].mem.base and R(o[0].mem.base) == "ebp" and 8 <= o[0].mem.disp <= 0x14:
                guarded.add(o[0].mem.disp)
            if len(o) > 1 and o[1].type == X86_OP_REG and R(o[1].reg) in tr: guarded.add(tr[R(o[1].reg)])
        # index use
        for x in o:
            if x.type == X86_OP_MEM and x.mem.index and R(x.mem.index) in tr and x.mem.scale in (4, 8) \
                    and tr[R(x.mem.index)] not in guarded and mn != "lea":
                hits.append({"fn": short(pubs[va]), "va": va, "use": i.address, "arg": tr[R(x.mem.index)],
                             "text": "%s %s" % (mn, i.op_str)}); tr.pop(R(x.mem.index)); break
        if mn == "mov" and len(o) == 2 and o[0].type == X86_OP_REG and R(o[0].reg) in tr and o[1].type != X86_OP_REG:
            tr.pop(R(o[0].reg))
hits.sort(key=lambda h: (not UI.search(h["fn"]), h["fn"]))
for h in hits:
    print("%08x %-48s use %08x arg+%x  %s" % (h["va"], h["fn"][:48], h["use"], h["arg"], h["text"]))
print(len(hits), "candidates")
if len(sys.argv) > 3: json.dump(hits, open(sys.argv[3], "w"), indent=1)
