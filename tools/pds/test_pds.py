#!/usr/bin/env python3
"""CPU-emulation test of the --pds-everything caves (needs `pip install unicorn`).

    python3 ois_patcher.py <game dir> --pds-everything     # produces the patched exe
    python3 tools/pds/test_pds.py <game dir>/ois.exe        # then run this on it

The patched exe is loaded into Unicorn at its preferred base and the PDS
hooks are driven against a small synthetic sector (ships, torpedoes,
countermeasures built by hand with the field offsets the real code uses).
Nothing here runs the game: it checks that each cave does what its comment
says, and that stock behaviour is untouched for every other caller.
"""
import struct
import sys

from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE, UcError
from unicorn.x86_const import (UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_ECX, UC_X86_REG_EDX,
                               UC_X86_REG_EDI, UC_X86_REG_EIP, UC_X86_REG_ESI, UC_X86_REG_ESP,
                               UC_X86_REG_EBP, UC_X86_REG_XMM2)
import os
import pefile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
import ois_patcher  # the caves' fixup tables live here


def fixup_pos(fixups, name):
    return next(pos for pos, n in fixups if n == name)

IB = 0x400000
GSWD = 0x4A6D10 if "--server" not in sys.argv else 0x4A6BE0
SELECT = 0x4AF752 if "--server" not in sys.argv else 0x4AF602
STACK_TOP = 0x00300000
HEAP = 0x20000000


class Emu:
    def __init__(self, exe):
        self.uc = Uc(UC_ARCH_X86, UC_MODE_32)
        pe = pefile.PE(exe, fast_load=True)
        raw = open(exe, "rb").read()
        for s in pe.sections:
            va = IB + s.VirtualAddress
            size = (max(s.Misc_VirtualSize, s.SizeOfRawData) + 0xFFF) & ~0xFFF
            self.uc.mem_map(va, size)
            self.uc.mem_write(va, raw[s.PointerToRawData:s.PointerToRawData + s.SizeOfRawData])
        self.uc.mem_map(STACK_TOP - 0x100000, 0x100000)
        self.uc.mem_map(HEAP, 0x100000)
        self.heap_ptr = HEAP + 0x100
        self.stops = {}
        self.uc.hook_add(UC_HOOK_CODE, self._hook)
        self.pe = pe
        self.stopped_at = None

    # -- tiny allocator / struct builders ----------------------------------
    def alloc(self, size):
        p = self.heap_ptr
        self.heap_ptr += (size + 0xF) & ~0xF
        return p

    def w32(self, addr, v):
        self.uc.mem_write(addr, struct.pack("<I", v & 0xFFFFFFFF))

    def r32(self, addr):
        return struct.unpack("<I", self.uc.mem_read(addr, 4))[0]

    def wd(self, addr, v):
        self.uc.mem_write(addr, struct.pack("<d", v))

    def wf(self, addr, v):
        self.uc.mem_write(addr, struct.pack("<f", v))

    def rf(self, addr):
        return struct.unpack("<f", self.uc.mem_read(addr, 4))[0]

    def rb(self, addr):
        return self.uc.mem_read(addr, 1)[0]

    def string(self, addr, text):
        """MSVC std::string (SSO or heap) at addr."""
        b = text.encode()
        if len(b) < 16:
            self.uc.mem_write(addr, b + b"\0")
            self.w32(addr + 0x14, 0xF)
        else:
            p = self.alloc(len(b) + 1)
            self.uc.mem_write(p, b + b"\0")
            self.w32(addr, p)
            self.w32(addr + 0x14, len(b))
        self.w32(addr + 0x10, len(b))

    def make_ship(self, sector, x, y, vtype=0, iff_on=True, docked=False, rego="Ship",
                  launcher=0, destroyed=False):
        o = self.alloc(0x500)
        cls = self.alloc(0x200)
        sysm = self.alloc(0x100)
        self.w32(cls + 0x158, vtype)
        self.w32(o + 0x254, cls)
        self.w32(o + 0x40, sysm)
        self.uc.mem_write(sysm + 0x34, bytes([1 if iff_on else 0]))
        self.w32(o + 0x20, self.r32(sector))
        self.w32(o + 0x24, sector)
        self.wd(o + 0x28, x)
        self.wd(o + 0x30, y)
        if docked:
            self.w32(o + 0xD4, 3)
            self.w32(o + 0xF8, 2)
        self.string(o + 0x238, rego)
        self.w32(o + 0x39C, launcher)
        self.uc.mem_write(o + 0x3CC, bytes([1 if destroyed else 0]))
        vt = self.alloc(0x40)
        self.w32(o, vt)
        return o

    def make_cm(self, sector, x, y, rego):
        o = self.alloc(0x100)
        self.w32(o + 0x60, 3)
        self.string(o + 0x68, rego)
        self.wf(o + 0xF4, 90.0)
        self.wd(o + 0x28, x)
        self.wd(o + 0x30, y)
        return o

    def make_world(self):
        gd = self.alloc(0x200)
        raw = bytes(self.uc.mem_read(GSWD + 0x30, 0x20))
        gdata = struct.unpack_from("<I", raw, raw.index(b"\xa1") + 1)[0]   # mov eax, [g_gameData]
        self.w32(gdata, gd)
        sec = self.alloc(0x200)
        self.w32(sec, 7)                                  # sector id
        vec = self.alloc(16)
        self.w32(vec, sec)
        self.w32(gd + 0x3C, vec)
        self.w32(gd + 0x40, vec + 4)
        self.sector = sec
        self.ships, self.syn = [], []
        return sec

    def commit(self):
        sec = self.sector
        arr = self.alloc(4 * (len(self.ships) + 1))
        for i, s in enumerate(self.ships):
            self.w32(arr + 4 * i, s)
        self.w32(sec + 0xCC, arr)
        self.w32(sec + 0xD0, arr + 4 * len(self.ships))
        arr2 = self.alloc(4 * (len(self.syn) + 1))
        for i, s in enumerate(self.syn):
            self.w32(arr2 + 4 * i, s)
        self.w32(sec + 0x9C, arr2)
        self.w32(sec + 0xA0, arr2 + 4 * len(self.syn))

    # -- execution -----------------------------------------------------------
    def _hook(self, uc, address, size, user):
        # SEH frame bookkeeping (fs:[0]) -- skipped, nothing here throws
        if size >= 6 and address >= IB and self.uc.mem_read(address, 1)[0] == 0x64:
            b = bytes(self.uc.mem_read(address, 7))
            if b[1] == 0xA1:
                uc.reg_write(UC_X86_REG_EAX, 0)
                uc.reg_write(UC_X86_REG_EIP, address + 6)
                return
            if b[1] == 0xA3:
                uc.reg_write(UC_X86_REG_EIP, address + 6)
                return
            if b[1] == 0x89 and b[2] in (0x0D, 0x15, 0x05):
                uc.reg_write(UC_X86_REG_EIP, address + 7)
                return
        if address in self.stops:
            self.stopped_at = self.stops[address]
            uc.emu_stop()
            return
        # getShipWithinDistance's FPU distance call and its fstp
        if address == GSWD + 0x126 - 0x50:
            pass
        sd = self.dist_hooks
        if address == sd[0]:                               # call [Vec2::getDistanceSq]
            ecx = uc.reg_read(UC_X86_REG_ECX)
            esp = uc.reg_read(UC_X86_REG_ESP)
            other = self.r32(esp)
            ax, ay = self.rf(ecx), self.rf(ecx + 4)
            bx, by = self.rf(other), self.rf(other + 4)
            self.last_d2 = (ax - bx) ** 2 + (ay - by) ** 2
            uc.reg_write(UC_X86_REG_ESP, esp + 4)
            uc.reg_write(UC_X86_REG_EIP, sd[0] + 6)
        elif address == sd[1]:                             # fstp dword [ebp+0x10]
            ebp = uc.reg_read(UC_X86_REG_EBP)
            self.wf(ebp + 0x10, self.last_d2)
            uc.reg_write(UC_X86_REG_EIP, sd[1] + 3)
        elif address == getattr(self, "eff_addr", None):  # getEfficiencyPercent
            esp = uc.reg_read(UC_X86_REG_ESP)
            uc.reg_write(UC_X86_REG_EAX, self.efficiency)
            uc.reg_write(UC_X86_REG_EIP, self.r32(esp))
            uc.reg_write(UC_X86_REG_ESP, esp + 4)

    def locate_dist_hooks(self):
        raw = bytes(self.uc.mem_read(GSWD, 0x120))
        call = raw.find(bytes.fromhex("ff15")) + GSWD       # call dword ptr [IAT]
        fstp = raw.find(bytes.fromhex("d95d10")) + GSWD
        assert call > GSWD and fstp > GSWD
        self.dist_hooks = (call, fstp)

    def call_stdcall(self, addr, args, xmm2=None, ecx=None, regs=None, max_insn=20000):
        """Runs addr as a function until it returns to a sentinel; returns EAX."""
        sentinel = 0x7FEFFF00
        self.uc.mem_map(0x7FEFF000, 0x1000) if not hasattr(self, "_sent") else None
        self._sent = True
        self.uc.mem_write(sentinel, b"\xf4")                # hlt marker
        esp = STACK_TOP - 0x1000
        for a in reversed(args):
            esp -= 4
            self.w32(esp, a)
        esp -= 4
        self.w32(esp, sentinel)
        self.uc.reg_write(UC_X86_REG_ESP, esp)
        self.uc.reg_write(UC_X86_REG_EBP, 0)
        if ecx is not None:
            self.uc.reg_write(UC_X86_REG_ECX, ecx)
        if xmm2 is not None:
            self.uc.reg_write(UC_X86_REG_XMM2, int.from_bytes(struct.pack("<f", xmm2) + b"\0" * 12, "little"))
        for r, v in (regs or {}).items():
            self.uc.reg_write(r, v)
        self.stops[sentinel] = "returned"
        self.stopped_at = None
        self.uc.emu_start(addr, 0, count=max_insn)
        return self.uc.reg_read(UC_X86_REG_EAX), self.uc.reg_read(UC_X86_REG_ESP) - (esp + 4)


def site_target(emu, va, opcode_len):
    off = emu.r32(va + opcode_len)
    off = off - (1 << 32) if off & 0x80000000 else off
    return va + opcode_len + 4 + off


def cave_operand_target(emu, operand_va):
    """Target of the rel32 operand stored at operand_va (inside a cave)."""
    rel = emu.r32(operand_va)
    rel = rel - (1 << 32) if rel & 0x80000000 else rel
    return operand_va + 4 + rel


def main():
    exe = [a for a in sys.argv[1:] if not a.startswith("--")][0]
    emu = Emu(exe)
    emu.efficiency = 100
    emu.locate_dist_hooks()
    failures = []

    def check(name, cond, detail=""):
        print(("  PASS " if cond else "  FAIL ") + name + (f"   {detail}" if detail and not cond else ""))
        if not cond:
            failures.append(name)

    select_cave = site_target(emu, SELECT, 1)
    print(f"select cave at {select_cave:#x}")

    # ---------------------------------------------------------------- selection
    print("selection (weapons first, then ships; stations/docked/own excluded)")
    sec = emu.make_world()
    me = emu.make_ship(sec, 100.0, 100.0, rego="ME")
    station = emu.make_ship(sec, 101.0, 100.0, vtype=1, iff_on=True)
    docked = emu.make_ship(sec, 100.5, 100.0, docked=True)
    trader = emu.make_ship(sec, 103.0, 100.0, iff_on=True, rego="Trader")
    no_iff = emu.make_ship(sec, 102.0, 100.0, iff_on=False, rego="Dark")
    far_ship = emu.make_ship(sec, 190.0, 100.0, iff_on=False)
    own_torp = emu.make_ship(sec, 100.2, 100.0, vtype=4, launcher=me)
    dead_torp = emu.make_ship(sec, 100.3, 100.0, vtype=4, launcher=0x1234, destroyed=True)
    enemy_torp = emu.make_ship(sec, 104.0, 100.0, vtype=4, launcher=0x1234)
    emu.ships = [me, station, docked, trader, no_iff, far_ship, own_torp, dead_torp, enemy_torp]
    emu.commit()

    def pick(flag_sel=True, rng=5.0, excl=None):
        args = [7, me if excl is None else excl, 1, struct.unpack("<I", struct.pack("<f", 100.0))[0],
                struct.unpack("<I", struct.pack("<f", 100.0))[0]]
        keep = {UC_X86_REG_EBX: 0x11111111, UC_X86_REG_ESI: 0x22222222, UC_X86_REG_EDI: 0x33333333,
                UC_X86_REG_EBP: 0x44444444}
        eax, popped = emu.call_stdcall(select_cave, args, xmm2=rng, regs=keep)
        pick.preserved = all(emu.uc.reg_read(r) == v for r, v in keep.items())
        return eax, popped

    got, popped = pick()
    check("returns a hostile torpedo before a nearer ship", got == enemy_torp, f"got {got:#x}")
    check("callee pops exactly its 5 arguments (stdcall ret 0x14)", popped == 0x14, f"popped {popped:#x}")
    check("EBX/ESI/EDI/EBP are preserved", pick.preserved)
    emu.ships.remove(enemy_torp)
    emu.commit()
    got, _ = pick()
    check("then a ship with its IFF off (not the nearer one with IFF on, the station, the docked ship or own torpedo)", got == no_iff, f"got {got:#x}")
    emu.ships.remove(no_iff)
    emu.commit()
    got, _ = pick()
    check("nothing else qualifies in range (IFF-on ship, station, docked, own and destroyed weapons, far ship)", got == 0, f"got {got:#x}")
    got, _ = pick(rng=100.0)
    check("a larger range reaches the far ship", got == far_ship, f"got {got:#x}")

    # stock behaviour for every other caller (flag 0) is unchanged: first ship in range wins
    emu.ships = [me, station, docked]
    emu.commit()
    eax, popped = emu.call_stdcall(GSWD, [7, me, 0, struct.unpack("<I", struct.pack("<f", 100.0))[0],
                                          struct.unpack("<I", struct.pack("<f", 100.0))[0]], xmm2=5.0)
    check("flag 0 (all other callers) still returns the first ship in range, stations included", eax == station,
          f"got {eax:#x}")

    # ------------------------------------------------------------------- damage
    print("damage delivery")
    damage_cave = site_target(emu, 0x4AF8BF + 1, 1) if "--server" not in sys.argv else site_target(emu, 0x4AF76F + 1, 1)
    emu.ships = [me]
    torp = emu.make_ship(sec, 0, 0, vtype=4, launcher=0x1234)
    ship = emu.make_ship(sec, 0, 0, vtype=0)
    called = []
    stub = 0x7FEFFE00
    emu.uc.mem_write(stub, b"\xc2\x10\x00")              # ret 0x10: stands in for Ship::damage
    emu.w32(emu.r32(ship) + 0xC, stub)
    emu.stops[stub] = "ship-damage"
    eax, _ = emu.call_stdcall(damage_cave, [45, 0x42C80000, 2, me], regs={UC_X86_REG_EDI: torp})
    check("a locked torpedo is destroyed", emu.rb(torp + 0x3CC) == 1 and emu.stopped_at == "returned")
    emu.stopped_at = None
    eax, _ = emu.call_stdcall(damage_cave, [45, 0x42C80000, 2, me], regs={UC_X86_REG_EDI: ship})
    check("a ship still goes through Ship::damage (virtual slot 3)", emu.stopped_at == "ship-damage", emu.stopped_at)
    check("...and is not flagged destroyed by the cave", emu.rb(ship + 0x3CC) == 0)

    # ---------------------------------------------------------------- hit roll
    print("hit roll")
    roll_site = SELECT + 0xE7
    roll_cave = site_target(emu, roll_site, 1)
    hit, miss = roll_site + 10, cave_operand_target(emu, roll_cave + fixup_pos(ois_patcher.ROLL_FIXUPS, "MISS"))
    emu.stops[hit], emu.stops[miss] = "hit", "miss"
    frame = emu.alloc(0x100) + 0x80

    def roll(target, value):
        emu.w32(frame - 0x3C, target)
        emu.w32(frame - 0x40, value)
        emu.stopped_at = None
        emu.call_stdcall(roll_cave, [], regs={UC_X86_REG_EBP: frame})
        return emu.stopped_at
    check("torpedo: no roll needed", roll(torp, 6) == "hit")
    check("ship, roll 1: hit", roll(ship, 1) == "hit")
    check("ship, roll 5: miss (stock behaviour)", roll(ship, 5) == "miss")

    # ------------------------------------------------------------ countermeasures
    print("countermeasures")
    cm_site = SELECT + 0x0A
    cm_cave = site_target(emu, cm_site, 2)
    after_shot = site_target(emu, 0x4AF8BF + 19 if "--server" not in sys.argv else 0x4AF76F + 19, 2)
    no_target = cave_operand_target(emu, cm_cave + fixup_pos(ois_patcher.COUNTERMEASURE_FIXUPS, "NO_TARGET"))
    emu.stops[after_shot], emu.stops[no_target] = "after-shot", "no-target"
    emu.eff_addr = cave_operand_target(emu, cm_cave + fixup_pos(ois_patcher.COUNTERMEASURE_FIXUPS, "EFFICIENCY"))
    mod = emu.alloc(0x100)
    mcls = emu.alloc(0x200)
    emu.w32(mod + 8, mcls)
    emu.w32(mod + 0xC, emu.alloc(0x40))
    emu.wf(mcls + 0x104, 5.0)
    me2 = emu.make_ship(sec, 100.0, 100.0, rego="ME")
    emu.ships = [me2]
    ours = emu.make_cm(sec, 101.0, 100.0, "ME")
    theirs_far = emu.make_cm(sec, 160.0, 100.0, "THEM")
    theirs = emu.make_cm(sec, 103.0, 100.0, "A-VERY-LONG-REGISTRATION-NAME-001")
    emu.syn = [ours, theirs_far, theirs]
    emu.commit()

    def run_cm():
        emu.stopped_at = None
        emu.call_stdcall(cm_cave, [], regs={UC_X86_REG_ESI: me2, UC_X86_REG_EBX: mod, UC_X86_REG_EDI: 0})
        return emu.stopped_at
    where = run_cm()
    check("an enemy decoy in range is shot and the PDS then fires (shake/sound/reload)", where == "after-shot", where)
    check("...its timer is zeroed so the game removes it", emu.rf(theirs + 0xF4) == 0.0)
    check("our own decoy is untouched", emu.rf(ours + 0xF4) == 90.0)
    check("an out-of-range decoy is untouched", emu.rf(theirs_far + 0xF4) == 90.0)
    where = run_cm()
    check("with only our decoy / far ones left it stands down (no shot, no reload)",
          where == "no-target", where)

    print()
    if failures:
        print(f"{len(failures)} FAILED: {failures}")
        sys.exit(1)
    print("all caves behave")


if __name__ == "__main__":
    main()
