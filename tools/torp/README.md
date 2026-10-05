# Torpedo that loses its target

`fix_torpedo_lost_target` in `ois_patcher.py` (client and server). Findings from the decompile and the
disassembly:

* `GameLogic::entirelyRemoveShip` has a loop over every ship in the sector. For a weapon (vessel type 4)
  it zeroes the launcher (`+0x39C`) and the target (`+0x38C`) when they point at the ship being removed.
  The Ghidra decompile drops this part of the loop; the machine code at 0x40D95F (client) has it.
* `Weapon::runHomeLogic` treats `target == 0` as "pick the nearest contact in my sensor list"
  (`+0x214` list, the `detected a target` debug line). That is meant for a torpedo fired with no target,
  but it also catches a torpedo whose target was just removed, so it locks onto a station, another
  weapon or the player.

The fix uses the byte at `+0x3DC` (the "have contact" flag, only ever 0 or 1 in stock code) as a marker:

| site | change |
| --- | --- |
| `entirelyRemoveShip`, where the target is zeroed | also set `[+0x3DC] = 2` and clear the aim point (`+0x12C/+0x130` = -9999) |
| `runHomeLogic` target test | `target == 0` and marker 2: skip the acquisition |
| `runHomeLogic` call to `runAimLogic` | `target == 0`, marker 2 and no aim point: do not steer, switch the engine flags off (the same idle state `runTravelLogic` uses) |

`setTarget` writes 1 to the flag again, and a target or aim point set from the weapon terminal makes
the conditions false, so a re-targeted torpedo homes as normal.

`python3 tools/torp/test_torp.py <game dir>/ois.exe` (or `ois_server.exe`) emulates the three patched
sites with Unicorn. Not tested in the live game.
