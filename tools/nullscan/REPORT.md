# Null-dereference scan of ois.exe (Steam build)

Tool: `python3 scan.py <ois.exe> <ois.pdb> [hits.json]` (needs capstone + pefile).
`pdbsyms.py` reads the PDB public symbols; `show.py <exe> <va>...` disassembles around an address.

## Method
1. Pointer-returning functions (return type read from the MSVC mangled name) that have a
   `xor eax,eax; ret` path are "nullable" (34 found, all "find by id/name" lookups).
2. For every direct call, follow the returned pointer and flag a dereference that comes before any
   `test`/`cmp` of it.
3. Rank by call-graph distance from UI handlers (onMouse*, dragOnto, ...).

60 candidates, 6 reachable from UI handlers. Triaged by hand against the decompile below.

## Honest result
The game is better guarded than expected. Almost every candidate is a lookup by an id that comes
from *data* (menu ids, good names, sector ids, faction numbers) or from *state the game itself
sets*, so it can only fail on broken data or a stale id, not from a normal player action.
The scanner did **not** find the Fix 45 crash (a null *slot* in the module's component array,
not a failed lookup), so slot arrays need their own scan (below).

### Real but low-probability (unguarded, no known trigger)
| Where | Lookup | Note |
|---|---|---|
| `ScreenInterface::updateMousePosition` 0x556d5d | `Room::getObject(room+0x38)` | the sibling branch at line ~1242 of ScreenInterface.c uses `getObjectForScreenID` *with* a null test; this one has none |
| `ShipInterface::doEngUnmountComponent` 0x4e1229, 0x4e132f | `getModule(ship+0x1e4)` | the function that sets the selected slot (ShipInterface.c ~2574) does test it |
| `ShipTextData::getEngAddonFilename/getEngComponentFilename` and the addon-slot text builder 0x4edef8, 0x4eddef | `getModule(ship+0x1e4)` | |
| `UI_ModuleRepair::mouseHoverUpdate` 0x573cb8, `getDragLook` 0x5745b5 | `getModule(...+0x1d8 / +0x1e4)` | uses **two different** "open module" fields (0x1d8 vs 0x1e4); worth finding out why |
| `Weapon::runHomeLogic/runTravelLogic` | `getSensorDataForShipID` | the target-gone case; the personal-variants "torpedo lost target" patch already covers the torpedo path |
| `ShipData::checkModuleBatt*` / `checkPwrCurrentModule*` | `getBattery/getModule` | mission-script conditions on ships without that module |

### Probably fine / data-driven (not worth patching)
`GameData::getGood` (TradeEngine, ShipTextData, goodCost), `getSectorWithID`, `getFactionForNumber`,
`getMenu`, `getTab`, `getSyntheticObjectWithID`, RakNet `GetRemoteSystemFromSystemAddress`.
Several hits are `cmp [reg+0x14],0x10` which is a std::string capacity test, i.e. the lookup
returns a pointer to a struct whose first member is a string: still a deref.

## Next scans worth doing
* Component slot arrays: loads from `module+0xc` `[4+slot*4]` / `[0x54+slot*4]` used without a test
  (36 sites; the ones in `NetworkServer` run on the server and would be remote-triggerable).
* Unchecked `vector[index]` (the mail crash): `(end-begin)>>2` computed nearby but never compared.
