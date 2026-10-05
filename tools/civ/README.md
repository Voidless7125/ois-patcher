# tools/civ — the optional `--civilians-comply` variant

Developer tooling for `fix_civilians_comply` in `ois_patcher.py`; not needed to use it.

| File | Purpose |
|------|---------|
| `asm_civ.py` | Assembly source of the torpedo-in-flight cave. `--python` prints the embedded tables, `--check` verifies the patcher's bytes match this source (needs `keystone-engine capstone`). |
| `test_civ.py` | CPU-emulation test on a patched exe (needs `unicorn pefile`): the chance table, that a demand no longer records the demander and execution still reaches the following code, and the cave's "seen"/"not seen" decisions. `--server` for `ois_server.exe`. |

```
python ois_patcher.py <game dir> --civilians-comply
python tools/civ/test_civ.py <game dir>/ois.exe
```
Like the PDS tests, this exercises the changed code in isolation against a hand-built
world; it does not run the game.
