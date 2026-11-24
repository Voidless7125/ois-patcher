"""Aligns the Steam and GOG ois.exe so Steam addresses can be translated to GOG ones.

    python3 tools/gog/align.py <steam ois.exe> <gog ois.exe>

Both builds are the same game code compiled separately.  Functions are split at the int3 padding between them,
reduced to a "shape" (every instruction with its absolute-address and relative-branch operands masked), and
matched by shape.  Inside a matched pair the instructions line up one to one, which gives:
  * code_map: Steam instruction address -> GOG instruction address,
  * data_map: Steam absolute operand (global, string, IAT slot) -> GOG absolute operand, with conflicts dropped.
Functions whose shape occurs more than once are matched only if their order among the duplicates agrees.
"""
import collections
import hashlib
import struct
import sys

import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from capstone.x86 import X86_OP_IMM, X86_OP_MEM

md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True


class Image:
    def __init__(self, path):
        self.pe = pefile.PE(path)
        self.base = self.pe.OPTIONAL_HEADER.ImageBase
        sec = [s for s in self.pe.sections if s.Name.startswith(b".text")][0]
        self.tva = self.base + sec.VirtualAddress
        self.text = sec.get_data()[:sec.Misc_VirtualSize]
        self.lo, self.hi = self.base, self.base + self.pe.OPTIONAL_HEADER.SizeOfImage

    def functions(self):
        """[(start_va, end_va)] split at runs of int3 padding."""
        t, out, i, n = self.text, [], 0, len(self.text)
        while i < n:
            while i < n and t[i] == 0xCC:
                i += 1
            if i >= n:
                break
            j = i
            while j < n:
                if t[j] == 0xCC and t[j:j + 2] == b"\xcc\xcc":
                    break
                if t[j] == 0xCC and j + 1 < n and t[j + 1] != 0xCC and j - i > 0 and t[j - 1] in (0xC3, 0xC2, 0xE9, 0xEB):
                    break
                j += 1
            out.append((self.tva + i, self.tva + j))
            i = j
        return out

    def insns(self, a, b):
        return list(md.disasm(self.text[a - self.tva:b - self.tva], a))

    def abs_operands(self, ins):
        """Absolute 32-bit values the instruction carries that point into the image (candidate relocations)."""
        vals = []
        for op in ins.operands:
            if op.type == X86_OP_MEM and not op.mem.base and not op.mem.index and self.lo <= op.mem.disp < self.hi:
                vals.append(op.mem.disp)
            elif op.type == X86_OP_MEM and op.mem.index and self.lo <= (op.mem.disp & 0xFFFFFFFF) < self.hi \
                    and not op.mem.base:
                vals.append(op.mem.disp & 0xFFFFFFFF)
            elif op.type == X86_OP_IMM and ins.mnemonic in ("push", "mov", "cmp", "test") and self.lo + 0x1000 <= op.imm < self.hi \
                    and ins.mnemonic != "call":
                vals.append(op.imm)
        return vals


def shape(img, a, b):
    h = hashlib.sha1()
    ins = img.insns(a, b)
    for i in ins:
        if i.mnemonic in ("call", "jmp") or i.mnemonic.startswith("j"):
            key = i.mnemonic
        else:
            raw = bytes(i.bytes)
            # mask the operand bytes that hold an absolute address
            for v in img.abs_operands(i):
                p = struct.pack("<I", v & 0xFFFFFFFF)
                k = raw.find(p)
                if k >= 0:
                    raw = raw[:k] + b"\0\0\0\0" + raw[k + 4:]
            key = raw.hex()
        h.update(key.encode())
        h.update(b";")
    return h.digest(), len(ins)


def _norm(img, ins):
    raw = bytes(ins.bytes)
    if ins.mnemonic in ("call", "jmp") or ins.mnemonic.startswith("j"):
        return ins.mnemonic
    for v in img.abs_operands(ins):
        p = struct.pack("<I", v & 0xFFFFFFFF)
        k = raw.find(p)
        if k >= 0:
            raw = raw[:k] + b"\0\0\0\0" + raw[k + 4:]
    return raw.hex()


def fuzzy_extend(s, g, sf, gf, pairs, code_map, data_votes):
    """For Steam functions that did not match exactly: find the GOG function sitting between the neighbouring matched
    pairs and align instruction by instruction with a sequence diff (equal blocks only)."""
    import bisect
    import difflib
    pairs = sorted(pairs)
    pstarts = [p[0][0] for p in pairs]
    matched = {p[0][0] for p in pairs}
    gstarts = [a for a, b in gf]
    added = 0
    for a, b in sf:
        if a in matched:
            continue
        i = bisect.bisect_right(pstarts, a) - 1
        lo = pairs[i][1][1] if i >= 0 else g.tva
        hi = pairs[i + 1][1][0] if i + 1 < len(pairs) else g.tva + len(g.text)
        cands = [(c, d) for c, d in gf if lo <= c and d <= hi + 1]
        if not cands:
            continue
        si = s.insns(a, b)
        sn = [_norm(s, x) for x in si]
        best = None
        for c, d in cands:
            gi = g.insns(c, d)
            gn = [_norm(g, x) for x in gi]
            r = difflib.SequenceMatcher(None, sn, gn, autojunk=False)
            ratio = r.ratio()
            if best is None or ratio > best[0]:
                best = (ratio, gi, r)
        if best is None or best[0] < 0.6:
            continue
        _, gi, r = best
        for blk in r.get_matching_blocks():
            for k in range(blk.size):
                x, y = si[blk.a + k], gi[blk.b + k]
                code_map[x.address] = y.address
                for u, v in zip(s.abs_operands(x), g.abs_operands(y)):
                    data_votes[u][v] += 1
        added += 1
    return added


def align(steam_path, gog_path):
    s, g = Image(steam_path), Image(gog_path)
    sf, gf = s.functions(), g.functions()
    gshapes = collections.defaultdict(list)
    for a, b in gf:
        gshapes[shape(g, a, b)[0]].append((a, b))
    sshapes = collections.defaultdict(list)
    for a, b in sf:
        sshapes[shape(s, a, b)[0]].append((a, b))
    code_map, data_votes, matched = {}, collections.defaultdict(collections.Counter), 0
    pairs = []
    for h, sl in sshapes.items():
        gl = gshapes.get(h, [])
        if len(sl) == len(gl):
            pairs += list(zip(sorted(sl), sorted(gl)))
    for (a, b), (c, d) in pairs:
        si, gi = s.insns(a, b), g.insns(c, d)
        if len(si) != len(gi):
            continue
        matched += 1
        for x, y in zip(si, gi):
            code_map[x.address] = y.address
            for u, v in zip(s.abs_operands(x), g.abs_operands(y)):
                data_votes[u][v] += 1
    fz = fuzzy_extend(s, g, sf, gf, pairs, code_map, data_votes)
    matched += 0
    data_map = {}
    for u, c in data_votes.items():
        v, n = c.most_common(1)[0]
        if n == sum(c.values()):
            data_map[u] = v
    return s, g, code_map, data_map, (len(sf), len(gf), matched, fz)


if __name__ == "__main__":
    s, g, cm, dm, st = align(sys.argv[1], sys.argv[2])
    print("steam functions %d, gog functions %d, exactly aligned %d, fuzzy %d, code addresses %d, data addresses %d" % (st + (len(cm), len(dm))))
