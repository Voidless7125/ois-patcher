# Steam vs GOG `ois.exe`: what actually differs

Both builds are the same game code compiled separately (PE stamps 11 minutes apart, build configuration strings
`Steam.win32` and `Release.win32`).  Compared with `tools/gog/align.py` plus an instruction-level diff of every
function that did not match exactly (branch targets and moved table addresses ignored).

## Result: no difference in game rules found

| What | Functions | Nature |
| :--- | :--- | :--- |
| Identical (same instruction shape, only addresses moved) | 4105 of 4325 | none |
| Steamworks glue only in the Steam exe | about 20, `0x51F050`-`0x5203B0` | `CSteamAPIContext::Init`, `SteamInternal_OnContextInit`, `Stats::storeStats`, `onUserStatsReceived`/`Stored`, `setStat`/`addStat`/`setBinaryStat`, the `CCallback` classes |
| Calls to `SteamAPI_Init` / `SteamAPI_Shutdown` | `AppDelegate::applicationDidFinishLaunching` and `applicationWillClose`, `doQuitToOS`, `PresentationInterface::exitGame`, `ServerPresentationInterface::quit` | the Steam exe starts Steam ("Steam initialisation error. Please ensure Steam is running") and shuts it down; GOG has no such calls |
| `Stats` object is bigger on Steam | about 25 game functions (`completeBounty`, `takeLoan`, `repayLoan`, `performBuyShip`, `doFireWeapon`, `takeHazardDamage`, `setSector`, `explosion`, `performContractCompletion`, ...) | one instruction each: `operator new(0x58)` vs `new(0x28)` and a field offset (`[eax+0x2c]` vs `[eax+4]`), because the Steam `Stats` also holds the Steamworks callbacks.  GOG still counts the same stats, it just never uploads them |
| Layout | the rest | moved lookup tables and jump tables, padding, function order, `std::map` instantiations, a few CRT helpers (`__chkstk`, `__report_gsfailure`, `__security_check_cookie`) |

Text in `.rdata`/`.data`: 47 strings only in the Steam exe (all Steamworks: interface names, `steam_api.dll`, "Received Steam
Stats", "Steam initialised.", ...), one only in the GOG exe (`Release.win32`).  Every command, menu and log string is identical.

Imports: the Steam exe has one extra DLL, `steam_api.dll`; nothing else differs.

## What was not checked line by line

About ten large switch/registry functions (`getShipCommandFunction` 1821 instructions, `getShipCheckDataPointer`,
`shipDataCanPrev`, `populateListData`, `Screen_Custom::configureElements`, `UIText::update`, `NetworkClient::runLogic`, ...)
match 83-97% instruction for instruction; the rest is switch lowering and register allocation.  Their string tables are
identical, so the command and data registries are the same.  A real rule change hiding in that remainder is unlikely but not
excluded.
