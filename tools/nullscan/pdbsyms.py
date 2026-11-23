"""Minimal PDB (MSF 7.0) reader: returns {va: mangled_name} for S_PUB32 code symbols."""
import struct


def _streams(data):
    bs, = struct.unpack_from("<I", data, 32)
    dirsize, = struct.unpack_from("<I", data, 44)
    mapaddr, = struct.unpack_from("<I", data, 52)
    nblk = (dirsize + bs - 1) // bs
    blks = struct.unpack_from("<%dI" % nblk, data, mapaddr * bs)
    d = b"".join(data[b * bs:(b + 1) * bs] for b in blks)[:dirsize]
    n, = struct.unpack_from("<I", d, 0)
    sizes = struct.unpack_from("<%dI" % n, d, 4)
    pos = 4 + 4 * n
    out = []
    for s in sizes:
        if s == 0xFFFFFFFF:
            out.append(b"")
            continue
        nb = (s + bs - 1) // bs
        bl = struct.unpack_from("<%dI" % nb, d, pos)
        pos += 4 * nb
        out.append(b"".join(data[b * bs:(b + 1) * bs] for b in bl)[:s])
    return out


def load_publics(path, text_va=0x401000):
    data = open(path, "rb").read()
    st = _streams(data)
    dbi = st[3]
    symrec = struct.unpack_from("<H", dbi, 20)[0]
    syms = st[symrec]
    res = {}
    p = 0
    while p + 4 <= len(syms):
        ln, ty = struct.unpack_from("<HH", syms, p)
        if ty == 0x110E:  # S_PUB32
            flags, off, seg = struct.unpack_from("<IIH", syms, p + 4)
            name = syms[p + 14:p + 2 + ln].split(b"\0")[0].decode("latin1")
            if seg == 1 and flags & 2:  # function flag
                res[text_va + off] = name
        p += 2 + ln
    return res


if __name__ == "__main__":
    import sys
    r = load_publics(sys.argv[1])
    print(len(r))
    for va in sorted(r)[:10]:
        print(hex(va), r[va])
