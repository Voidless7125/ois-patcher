#!/usr/bin/env python3
"""Emulation test for the non-story-scenario autosave fix (needs `pip install unicorn pefile`).

    python3 tools/save/test_save.py <game dir>/ois.exe

Runs the patched guard in SaveHandler::saveGame for every combination of scenario
mode and category and checks that only (mode full, category story) reaches the save path.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "pds"))
import test_pds as tp
from unicorn.x86_const import UC_X86_REG_EAX

SITE, SAVE_PATH, NOT_SAVING = 0x4B8789, 0x4B8793, 0x4B89DD


def main():
    emu = tp.Emu(sys.argv[1])
    emu.dist_hooks = (0, 0)
    emu.stops[SAVE_PATH], emu.stops[NOT_SAVING] = "SAVES", "no save"
    scen = emu.alloc(0x200)
    bad = 0
    # category: 0 tutorial, 1 story, 2 single (the default), 3 multi, 4 meta; mode: 2 = full
    for mode in (0, 1, 2, 3):
        for cat in range(5):
            emu.w32(scen + 0x70, mode)
            emu.w32(scen + 0x6C, cat)
            emu.stopped_at = None
            emu.call_stdcall(SITE, [], regs={UC_X86_REG_EAX: scen})
            want = "SAVES" if (mode, cat) == (2, 1) else "no save"
            ok = emu.stopped_at == want
            bad += not ok
            if not ok or (mode, cat) in ((2, 1), (2, 2)):
                print(("  PASS " if ok else "  FAIL ") + f"mode {mode} category {cat}: {emu.stopped_at}")
    print("all 20 combinations behave" if not bad else f"{bad} FAILED")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
