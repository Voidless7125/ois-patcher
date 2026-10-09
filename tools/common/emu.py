#!/usr/bin/env python3
"""Tiny Unicorn harness shared by the emulation tests in tools/save and tools/pds
(needs `pip install unicorn pefile`).

The patched exe is loaded into Unicorn at its preferred base and a patched site is run
against a synthetic structure built by hand with the field offsets the real code uses.
Nothing here runs the game.
"""
import struct
import sys

from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE, UcError
from unicorn.x86_const import (UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_ECX, UC_X86_REG_EDX,
                               UC_X86_REG_EDI, UC_X86_REG_EIP, UC_X86_REG_ESI, UC_X86_REG_ESP,
                               UC_X86_REG_EBP, UC_X86_REG_XMM2)
import pefile

IB = 0x400000
GSWD = 0x4A6D10   # GameData::getShipWithinDistance (client)
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
