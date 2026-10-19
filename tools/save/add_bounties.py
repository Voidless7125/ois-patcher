#!/usr/bin/env python3
"""Adds bounties from galaxy.txt to the player's accepted-bounty list in an Objects in Space save (v12).

    python tools/save/add_bounties.py <ObjectsInSpace folder> <save in> <save out> [--per-sector N] [--seed S]

The folder is your game install (it must hold assets/galaxy.txt, assets/pirate_names.txt and ois.exe; the
exe is only read, for the captain-name tables).  Nothing is written but <save out>; the input save is untouched.

How the game treats an accepted bounty (from the decompile):
  * The save holds, per bounty: pirate ship name, captain name, registration, the target ship's id (0 until it
    has spawned), the rolled payout, then the bounty class (ship, config, weapon, experience, id, sector, style,
    taken flag, cooldown).  V12::writeBounty / V8::readBounty are the code this mirrors.
  * Whenever you are in the target sector and no ship with that registration is there, the game spawns the
    pirate (NPCShipManager::generateVesselFromBounty).  So EVERY bounty you hold for a sector spawns when you
    arrive; adding all 2,933 puts up to 270 pirates in one sector.  --per-sector N caps that.
"""
import argparse
import random
import re
import struct
import sys
from pathlib import Path

SAVE_MAGIC = 0x5F6AE9
EXPERIENCE = {"green": 0, "experienced": 1, "veteran": 2, "none": 3}      # getCaptainExperience table at 0x5E16B4
STYLE = {"cautious": 0, "moderate": 1, "reckless": 2, "vreckless": 3}      # getCaptainStyle table at 0x5E1694
# NameManager tables used by Sector::setNewBounties for captain names (first entry of each is a marker, skipped)
FIRST_A, COUNT_A = 0x5D07A8, 0x4C4          # 47% of captains
FIRST_B, COUNT_B = 0x5D1AB8, 0x10B3         # the rest
SURNAMES, COUNT_S = 0x5D5D98, 0x26F4


class Reader:
    def __init__(self, data, pos=0):
        self.d, self.p = data, pos

    def u32(self):
        v = struct.unpack_from("<I", self.d, self.p)[0]
        self.p += 4
        return v

    def f32(self):
        v = struct.unpack_from("<f", self.d, self.p)[0]
        self.p += 4
        return v

    def u8(self):
        v = self.d[self.p]
        self.p += 1
        return v

    def string(self):
        n = self.u32()
        if n > 200:
            raise ValueError("implausible string length")
        v = self.d[self.p:self.p + n]
        if len(v) != n or any(c < 32 or c > 126 for c in v):
            raise ValueError("not text")
        self.p += n
        return v.decode("latin1")


def read_bounty(r):
    b = {"name": r.string(), "captain": r.string(), "rego": r.string(), "ship_id": r.u32(), "value": r.u32()}
    b.update(ship=r.string(), config=r.string(), weapon=r.string(), exp=r.u32(), cid=r.u32(), sector=r.u32(),
             style=r.u32(), taken=r.u8(), cooldown=r.f32())
    if (not b["name"].strip() or " " not in b["captain"] or not re.fullmatch(r"[A-Z]{2}-\d{3,5}", b["rego"])
            or not b["ship"] or not b["config"] or not b["weapon"]):
        raise ValueError("not a bounty")
    if b["exp"] > 3 or b["style"] > 3 or b["taken"] > 1 or b["sector"] > 5000 or b["value"] > 1_000_000:
        raise ValueError("implausible bounty")
    return b


def pack_string(s):
    raw = s.encode("latin1")
    return struct.pack("<I", len(raw)) + raw


def pack_bounty(b):
    return (pack_string(b["name"]) + pack_string(b["captain"]) + pack_string(b["rego"])
            + struct.pack("<II", b["ship_id"], b["value"])
            + pack_string(b["ship"]) + pack_string(b["config"]) + pack_string(b["weapon"])
            + struct.pack("<IIIIBf", b["exp"], b["cid"], b["sector"], b["style"], b["taken"], b["cooldown"]))


def find_list(data):
    """Finds (count_offset, [existing bounties], end_offset) of the player's bounty list.

    The list follows the contracts block, whose layout varies, so look for a count whose entries all parse.
    Needs at least one bounty already held (an empty list is just a zero and cannot be told apart)."""
    if struct.unpack_from("<I", data, 0)[0] != SAVE_MAGIC:
        sys.exit("not an Objects in Space save")
    version = struct.unpack_from("<I", data, 4)[0]
    if version != 12:
        sys.exit(f"save version {version}: this tool understands version 12 only")
    found = []
    for off in range(64, len(data) - 8):
        n = struct.unpack_from("<I", data, off)[0]
        if not 1 <= n <= 5000:
            continue
        r = Reader(data, off + 4)
        try:
            items = [read_bounty(r) for _ in range(n)]
        except (ValueError, struct.error):
            continue
        found.append((off, items, r.p))
    if len(found) != 1:
        sys.exit(f"found {len(found)} places that look like the bounty list; accept one bounty in game first "
                 "(a save with none cannot be located reliably)" if not found else
                 f"found {len(found)} candidate bounty lists, refusing to guess")
    return found[0]


def read_name_tables(exe_path):
    data = Path(exe_path).read_bytes()
    e_lfanew = struct.unpack_from("<I", data, 0x3C)[0]
    nsec = struct.unpack_from("<H", data, e_lfanew + 6)[0]
    opt = struct.unpack_from("<H", data, e_lfanew + 20)[0]
    base = struct.unpack_from("<I", data, e_lfanew + 24 + 28)[0]
    secs = []
    for i in range(nsec):
        s = e_lfanew + 24 + opt + i * 40
        vsize, va, rawsize, raw = struct.unpack_from("<IIII", data, s + 8)
        secs.append((base + va, max(vsize, rawsize), raw))

    def off(va):
        for sva, size, raw in secs:
            if sva <= va < sva + size:
                return raw + va - sva
        raise ValueError(f"address {va:#x} not in the exe")

    def table(va, count):
        out = []
        for i in range(1, count):                    # entry 0 is a marker
            p = off(struct.unpack_from("<I", data, off(va) + 4 * i)[0])
            out.append(data[p:data.index(b"\0", p)].decode("latin1"))
        return out
    return table(FIRST_A, COUNT_A), table(FIRST_B, COUNT_B), table(SURNAMES, COUNT_S)


def parse_dice(text):
    m = re.fullmatch(r"\s*(\d+)d(\d+)\+(\d+)\s*", text)
    if not m:
        raise ValueError(f"unreadable payout {text!r}")
    return int(m[1]), int(m[2]), int(m[3])


def read_galaxy(path):
    out = []
    for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.startswith("bounty="):
            continue
        f = [x.strip() for x in line[len("bounty="):].split(",")]
        if len(f) != 6:
            raise ValueError(f"unexpected bounty line: {line}")
        ship, _, config = f[4].partition(":")
        out.append({"dice": parse_dice(f[0]), "sector": int(f[1]), "exp": EXPERIENCE[f[2]], "style": STYLE[f[3]],
                    "ship": ship, "config": config or ship, "weapon": f[5]})
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("game_dir")
    ap.add_argument("save_in")
    ap.add_argument("save_out")
    ap.add_argument("--per-sector", type=int, default=0, help="at most this many bounties per target sector (0 = all)")
    ap.add_argument("--seed", type=int, default=None)
    args = ap.parse_args()

    game = Path(args.game_dir)
    assets = game / "assets" if (game / "assets").is_dir() else game
    exe = next((p for p in (game / "ois.exe", game / "ois.exe.original-backup") if p.is_file()), None)
    if exe is None:
        sys.exit("ois.exe not found in the game folder")
    defs = read_galaxy(assets / "galaxy.txt")
    ship_names = [n for n in (assets / "pirate_names.txt").read_text(encoding="utf-8").split("\n") if n.strip()]
    first_a, first_b, surnames = read_name_tables(exe)

    data = Path(args.save_in).read_bytes()
    off, existing, end = find_list(data)
    if b"".join(pack_bounty(b) for b in existing) != data[off + 4:end]:
        sys.exit("internal check failed: re-writing the existing bounties does not reproduce the save")

    rng = random.Random(args.seed)
    used = {b["rego"] for b in existing}
    next_id = 100000 + max([b["cid"] for b in existing] + [0])
    per_sector = {}
    new = []
    for d in defs:
        if args.per_sector and per_sector.get(d["sector"], 0) >= args.per_sector:
            continue
        per_sector[d["sector"]] = per_sector.get(d["sector"], 0) + 1
        count, sides, base = d["dice"]
        value = base + sum(rng.randrange(sides) + 1 for _ in range(count))
        while True:
            rego = "%s%s-%d" % (rng.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ"), rng.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ"),
                                rng.randrange(1000, 10000))
            if rego not in used:
                used.add(rego)
                break
        first = rng.choice(first_a if rng.randrange(100) < 47 else first_b)
        next_id += 1
        new.append({"name": rng.choice(ship_names), "captain": f"{first} {rng.choice(surnames)}", "rego": rego,
                    "ship_id": 0, "value": value, "ship": d["ship"], "config": d["config"], "weapon": d["weapon"],
                    "exp": d["exp"], "cid": next_id, "sector": d["sector"], "style": d["style"], "taken": 1,
                    "cooldown": -1.0})

    total = len(existing) + len(new)
    out = (data[:off] + struct.pack("<I", total) + data[off + 4:end]
           + b"".join(pack_bounty(b) for b in new) + data[end:])
    Path(args.save_out).write_bytes(out)

    print(f"held before: {len(existing)}   added: {len(new)}   now: {total}")
    biggest = sorted(per_sector.items(), key=lambda kv: -kv[1])[:5]
    print("most per sector (sector: count):", ", ".join(f"{s}: {n}" for s, n in biggest))
    print(f"wrote {args.save_out} ({len(out) - len(data):+d} bytes)")


if __name__ == "__main__":
    main()
