# tools/pds — the optional `--pds-everything` variant

Developer tooling for `fix_pds_target_everything` in `ois_patcher.py`. None of
this is needed to *use* the patcher; the finished machine code is embedded there.

| File | Purpose |
|------|---------|
| `asm_pds.py` | The assembly source of the five caves, with comments. `--python` prints the byte tables embedded in the patcher; `--check` verifies the embedded bytes match this source; `-v` disassembles. Needs `pip install keystone-engine capstone`. |
| `test_pds.py` | Drives the caves on a patched exe inside a CPU emulator (`pip install unicorn pefile`) against a hand-built sector: selection order, stations/docked/own weapons excluded, torpedo destruction, hit roll, decoys, register preservation, and that every other caller of `getShipWithinDistance` is unchanged. Use `--server` for `ois_server.exe`. |

```
python ois_patcher.py <game dir> --pds-everything
python tools/pds/test_pds.py <game dir>/ois.exe
python tools/pds/test_pds.py <game dir>/ois_server.exe --server
```

The test proves the caves do what they claim in isolation. It does not run the
game: the field offsets it builds objects from come from the decompile, and the
end-to-end behaviour (a torpedo actually vanishing in flight) has to be seen in game.
