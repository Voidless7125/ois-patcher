# tools/ — emulation tests

All tests load a patched exe into Unicorn through the shared harness `tools/common/emu.py`
(`pip install unicorn pefile capstone`). Run: `python3 tools/<dir>/test_<x>.py <game dir>/ois.exe`.

## Tests for code that is in this branch (all pass on a freshly patched exe)
`autopilot/test_ap`, `behaviour/test_behaviour`, `mech/test_mech`, `pds/test_pds` (point-defence torpedo fix),
`pds/test_hitchance` (shop label), `power/test_power`, `save/test_save`, `torp/test_torp`, `ui/test_ui`,
`ui/test_resolution_list`, `hail/test_hail` (hail guard, client and server; `--server` for `ois_server.exe`),
`news/test_local_news` (local news; needs no game files).

## Orphaned tests — the code they test is NOT in this branch any more
They fail (or error on a missing `ois_patcher` attribute) until the variant is restored:

| Test | Tests | Why it is orphaned |
|---|---|---|
| `pds/test_pds_everything` | `--pds-everything` | variant removed upstream ("not the purpose of this patcher") |
| `civ/test_civ` | `--civilians-comply` | removed in the same commit |
| `spinup/test_spinup` | spin-up timer formula | implementation not in this branch |
| `iffdebug/test_iff` | IFF debug cave | `IFF_DEBUG_CAVE` no longer in `ois_patcher.py` |
- `tools/dll/test_dll_plugin.py [game folder]`: the plugin's optional DLL step (decline / accept / `--yes` / damaged package / uninstall) on a scratch copy. Passing.
