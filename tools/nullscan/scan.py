"""Static null-dereference scanner for ois.exe.

1. Pointer-returning functions (return type from the MSVC mangled name) that
   contain a path returning 0  => "nullable".
2. Every direct call to a nullable function: follow the returned pointer (eax,
   copies of it in registers / stack slots) and report when it is dereferenced
   before any test/cmp of it  => candidate bug.
3. Rank candidates by whether they are reachable from UI event handlers.

Usage: scan.py <ois.exe> <ois.pdb> [out.json]
"""
import re, sys, json, collections
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from capstone.x86 import X86_OP_REG, X86_OP_MEM, X86_OP_IMM
from pdbsyms import load_publics

exe, pdb = sys.argv[1], sys.argv[2]
out = sys.argv[3] if len(sys.argv) > 3 else None

pe = pefile.PE(exe)
base = pe.OPTIONAL_HEADER.ImageBase
text = [s for s in pe.sections if s.Name.startswith(b".text")][0]
tva = base + text.VirtualAddress
tdata = text.get_data()
tend = tva + len(tdata)

pubs = load_publics(pdb, tva)
starts = sorted(pubs)
ends = {}
for i, s in enumerate(starts):
    ends[s] = starts[i + 1] if i + 1 < len(starts) else tend

md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True


def returns_pointer(m):
    if "$" in m:
        return False
    mm = re.match(r"\?[^@]+@(?:[^@]+@)*?@(.*)$", m)
    if not mm:
        mm = re.match(r"\?[^@]+@@(.*)$", m)
    if not mm:
        return False
    r = mm.group(1)
    if not r:
        return False
    c = r[0]
    if c == "Y":
        rest = r[2:]
    elif c == "S":
        rest = r[2:]
    elif c in "QUAIMEOCKGW":
        rest = r[3:]
    else:
        return False
    return rest[:2] in ("PA", "PB")


def disasm(va):
    off = va - tva
    return list(md.disasm(tdata[off:ends[va] - tva], va))


def short(m):
    mm = re.match(r"\?([^@]+)@([^@]+)@@", m)
    return "%s::%s" % (mm.group(2), mm.group(1)) if mm else m


# ---- pass 1: nullable pointer returners -----------------------------------
nullable = {}
calls = collections.defaultdict(set)
insns = {}
for va in starts:
    if va < tva or va >= tend:
        continue
    ins = disasm(va)
    insns[va] = ins
    for i in ins:
        if i.mnemonic == "call" and i.operands and i.operands[0].type == X86_OP_IMM:
            calls[va].add(i.operands[0].imm)
for va, ins in insns.items():
    if not returns_pointer(pubs[va]):
        continue
    for k, i in enumerate(ins):
        zero = (i.mnemonic == "xor" and i.op_str == "eax, eax") or (
            i.mnemonic == "mov" and i.op_str == "eax, 0")
        if not zero:
            continue
        for j in ins[k + 1:k + 5]:
            if j.mnemonic == "ret" or (j.mnemonic == "jmp" and j.operands[0].type == X86_OP_IMM):
                nullable[va] = True
                break
            if "eax" in j.op_str.split(",")[0] and j.mnemonic in ("mov", "xor", "lea", "call", "add", "sub"):
                break
        if va in nullable:
            break

# ---- pass 2: caller analysis -----------------------------------------------
REGS32 = {"eax", "ebx", "ecx", "edx", "esi", "edi", "ebp"}


def mem_regs(op):
    s = set()
    if op.type == X86_OP_MEM:
        if op.mem.base:
            s.add(md.reg_name(op.mem.base))
        if op.mem.index:
            s.add(md.reg_name(op.mem.index))
    return s


def analyze(ins, k):
    """call at ins[k] to a nullable function; return (kind, insn) or None."""
    tracked = {"eax"}
    for i in ins[k + 1:k + 60]:
        mn = i.mnemonic
        ops = i.operands
        ops_s = i.op_str
        # tests clear tracking
        if mn in ("test", "cmp") and len(ops) == 2:
            if ops[0].type == X86_OP_REG and md.reg_name(ops[0].reg) in tracked:
                return None
            if ops[0].type == X86_OP_MEM:
                pass
        # dereference of a tracked reg
        for op in ops:
            if op.type == X86_OP_MEM and (mem_regs(op) & tracked):
                if mn == "lea":
                    break
                # [reg] with reg only as index of absolute? still a deref
                return ("deref", i)
        if mn == "call":
            # thiscall with tracked ecx is a deref of 'this' (virtual call [reg+x] handled above)
            if "ecx" in tracked:
                return ("this-call", i)
            tracked -= {"eax", "ecx", "edx"}
            if not tracked:
                return None
            continue
        if mn in ("ret", "jmp"):
            return None
        # copies
        if mn == "mov" and len(ops) == 2 and ops[1].type == X86_OP_REG:
            src = md.reg_name(ops[1].reg)
            if ops[0].type == X86_OP_REG:
                dst = md.reg_name(ops[0].reg)
                if src in tracked:
                    tracked.add(dst)
                else:
                    tracked.discard(dst)
                if not tracked:
                    return None
                continue
        if mn == "mov" and len(ops) == 2 and ops[0].type == X86_OP_REG:
            tracked.discard(md.reg_name(ops[0].reg))
            if not tracked:
                return None
        elif mn in ("xor", "pop", "lea", "movzx", "movsx") and ops and ops[0].type == X86_OP_REG:
            tracked.discard(md.reg_name(ops[0].reg))
            if not tracked:
                return None
        if mn == "push" and ops and ops[0].type == X86_OP_REG and md.reg_name(ops[0].reg) in tracked:
            pass  # passed as argument: unknown callee, ignore
    return None


hits = []
for va, ins in insns.items():
    for k, i in enumerate(ins):
        if i.mnemonic == "call" and i.operands and i.operands[0].type == X86_OP_IMM \
                and i.operands[0].imm in nullable:
            r = analyze(ins, k)
            if r:
                hits.append({"in": va, "in_name": short(pubs[va]), "callee": i.operands[0].imm,
                             "callee_name": short(pubs[i.operands[0].imm]), "call_site": i.address,
                             "kind": r[0], "use": r[1].address, "use_text": "%s %s" % (r[1].mnemonic, r[1].op_str)})

# ---- pass 3: reachability from UI handlers ----------------------------------
UI = re.compile(r"(onMouse|onTouch|onClick|dragOnto|onKey|onButton|handle|mouseUp|mouseDown|"
                r"clicked|touch)", re.I)
roots = [v for v, m in pubs.items() if UI.search(short(m)) and (
    "UI_" in m or "Screen" in m or "Interface" in m or "ComputerSystem" in m)]
dist = {r: 0 for r in roots}
q = collections.deque(roots)
while q:
    f = q.popleft()
    for c in calls.get(f, ()):
        if c in insns and c not in dist and dist[f] < 6:
            dist[c] = dist[f] + 1
            q.append(c)
for h in hits:
    h["ui_depth"] = dist.get(h["in"])
hits.sort(key=lambda h: (h["ui_depth"] is None, h["ui_depth"] or 0, h["in_name"]))

print("functions: %d  pointer-returning nullable: %d  hits: %d  (reachable from UI: %d)" % (
    len(insns), len(nullable), len(hits), sum(1 for h in hits if h["ui_depth"] is not None)))
for h in hits:
    d = h["ui_depth"]
    print("%-3s %08x %-48s <- %-40s use %08x %s" % (
        "-" if d is None else d, h["call_site"], h["in_name"][:48], h["callee_name"][:40], h["use"], h["use_text"]))
if out:
    json.dump(hits, open(out, "w"), indent=1)
