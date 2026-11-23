# Bugs fixed

Every bug this patch fixes, grouped by what you would notice in the game. The version is the release that first fixed it, "exe" means
the game program is patched (`ois.exe`, and `ois_server.exe` where it says server), "mod" means a game data file is corrected. The full
history with issue and pull-request links is in [CHANGELOG.md](CHANGELOG.md); what was looked at and deliberately left alone is at the
end of that file.

Nothing here has been checked by the game's developers, and fixes found by reading the code are marked *(code only)* when nobody has
confirmed them in a live game yet.

## Crashes and freezes

| Bug | Cause | Fix | Since |
| :--- | :--- | :--- | :--- |
| Pirate Hunt scenario crashes at the start (client and co-op server) | A ship spawn was picked without checking the list bounds | The check was added | 0.1.0 (server 0.3.0) |
| A second Pirate Hunt crash | A "duplicate ship-sets" log message passed 2 values to a 3-value format | Argument supplied | 0.3.1 (client and server) |
| Crash when opening the PDA while a character portrait is being drawn | A null check was missing in the engine's batch renderer | Tab is ignored for that instant | 0.2.0 |
| Crash returning from a station to your ship on longer-played saves | Station monitors were drawn after being freed (two ordering bugs) | The update and fade steps run in a safe order | 0.4.1 |
| Crash when clicking or backing out of a monitor after the primary hull is destroyed | A null ship was used | Guarded | 0.3.8 |
| Crash dropping a part onto an empty slot in the repair screen (for example right after unmounting parts) | The swap read the empty slot's null component | The drop is refused like any other invalid slot | 0.4.2 |
| Crash dragging an installed addon to another slot on the repair screen | An out-of-range read | The move is refused cleanly | 0.3.6 |
| Crash or hang loading a save that has a module the game no longer knows | A null module was used and the save stream got out of step | The slot loads empty | 0.3.5 |
| Mail terminal crash with `DEL`, `DEL DIR`, `DEL VIEW` and other names with no extension | Missing extension handling | Guarded, and `.COM` files still cannot be deleted | 0.1.0 (refined 0.4.0) |
| Game crash on equipping a MKX-LADAR-A-2 or MKX-LADAR-A-T, and on connecting in co-op with one | Their 10-character ids were cut off in a 10-byte network field | Ids shortened (`mkxladr2`, `mkxladrt`) | 0.3.3 |
| Saves with those LADARs no longer opened after the rename | The old ids were unknown | The old ids are accepted as aliases (client and server) | 0.4.2 |
| Mail terminal crashed opening an email that does not exist | The email list was indexed with no bounds check | An out-of-range index is ignored | 0.4.2 |
| Enter on an empty News list showed `Invalid article number: 747614849` | Out-of-range read | Range checked | 0.4.0 |
| "Escort: Make a Break" co-op scenario would not load | A one-character typo in an include | Corrected | 0.1.0 |
| "Quit to Menu" or "Quit to OS" froze or did nothing when you were a LAN client | The client was never disconnected | Disconnects first | 0.3.6 |

## Autopilot and flight

| Bug | Cause | Fix | Since |
| :--- | :--- | :--- | :--- |
| Steering and burn vector recomputed about 125 times a second (log spam, wasted time) | Three separate causes | All three fixed | 0.1.0 |
| Autopilot burned away from its destination after overshooting with a fast engine | The retro burn ignored the direction of travel | Uses the velocity and waypoint direction | 0.4.0 |
| Autopilot kept the drive burning at top speed and drained the batteries | A float comparison too strict to ever be true | Tolerance added | 0.4.0 |
| Autopilot kept burning forever at the last second of an approach and never docked (for example GX Delta at 100%) *(code only)* | The "overshot" branch ended the autopilot without switching the drive off | It now hands over to All Stop; "stopped" now means 0.3 Gm/s or less | 0.4.2 |
| Full Stop while docked let you fly away without paying fees or closing the airlock | It cleared the docking state | The docking state is left alone | 0.3.5 |
| Some NPC ships turned up with IFF off and reactors off ("Unknown" in red), such as the SS Jolly Rancher | A flag was never cleared and held leftover memory | Cleared in the constructor | 0.4.1 |

## Weapons and defence

| Bug | Cause | Fix | Since |
| :--- | :--- | :--- | :--- |
| Point-defence lasers could not shoot torpedoes, contrary to the Infopedia | Torpedoes were not valid targets | They are now, with weapons first | 0.4.0 |
| Weapon spin-up got *faster* when a tube was damaged or low-efficiency | The factor was inverted compared with reload | Now `spinuptime * (2 - efficiency)` (client and server) | 0.4.2 |
| "Hit Chce" on the point-defence page showed the average die roll, not a chance | The wrong formula | Shows 100 / sides | 0.4.2 |
| Long point-defence names overlapped the ENABLE button | The name wrapped | Only the model name is shown when too long | 0.4.0 |

## Power

| Bug | Cause | Fix | Since |
| :--- | :--- | :--- | :--- |
| The power screen and the actual battery drain disagreed | Component power modifiers were applied to one and not the other, and active modules were counted twice | Both agree | 0.4.0 (client and server) |
| Terminal power figures were in `mw` instead of `kw`, and STATUS showed generation as drain | Wrong unit string and wrong variable | `kw`, and drain is drain | 0.4.0 |

## Saves, scenarios and the mail terminal

| Bug | Cause | Fix | Since |
| :--- | :--- | :--- | :--- |
| Docking or jumping in a stand-alone scenario overwrote campaign save slot 1 | The autosave ignored the scenario type | Only story games autosave | 0.4.0 |
| A deleted email came back after leaving the MAIL terminal | A stale copy of the list stayed on screen | Refreshed | 0.3.7 |
| `DEL` could delete `.COM` system commands (briefly, 0.3.0 to 0.3.8) | An over-wide fix | Reverted to the original "cannot delete system file" | 0.4.0 |
| Intercom conversations (for example Asterin Allas) ignored Enter until you pressed an arrow key | Option 0 was assumed valid | The first valid option is chosen | 0.4.0 |
| Module purchase welcome emails never arrived (71 unused emails) | The code never queued them | Queued on purchase, with the maker and model in the opening line | 0.4.0 |

## Shops, mechanic and ship screens

| Bug | Cause | Fix | Since |
| :--- | :--- | :--- | :--- |
| Remora RCS and sensor could be bought in shops | They had a shop price | `basevalue=0` (the RM-SNS), restored for the RCS after a later clean-up dropped it | 0.4.0, restored 0.4.2 |
| Garbled error buying radiation-shielded or temperature-controlled goods without pod space | Wrong arguments to the message | Fixed | 0.3.6 |
| Nav map distance showed reachable sectors red for jump drives above 100% efficiency | It compared the base range, not base times efficiency | Uses the current range | 0.4.0 |
| Jump-drive "Range" rating read V. Bad or Bad for every drive | Cut-offs above every real drive | New cut-offs 180 / 205 / 225 / 245 | 0.4.2 |
| Solar wing "Range" rating was Bad for every wing | Cut-offs above every real wing | New cut-offs 1.1 / 1.15 / 1.28 / 1.4 | 0.4.2 |
| Sensor "Range : 0Gm" on every sensor | It read a field sensors never fill in | The line now shows the software version | 0.4.2 |
| Sensor "Detect Rng" and "Sns. Ghsts" ratings never reached the top bands | Cut-offs did not fit the real sensors | New cut-offs (see below) | 0.4.2 |
| Sensor "Strength" label | It is how far out a sensor hears, not a strength | Renamed "Detect Rng" | 0.4.2 |
| Grappling arm "Speed" read backwards | The number is the time a use takes | Renamed "Use Time" | 0.4.2 |
| Mechanic's Buy/Sell Module button sat on top of the status text | Button at y=209 under text that runs further down | Moved to y=221 | 0.4.2 |
| "Docking" and "stationary" drew on top of each other | Both were printed | Fixed | 0.3.8 |
| Options > resolution needed several clicks per visible change | One entry per refresh rate | One entry per width x height | 0.4.2 |

## Interface and controls

| Bug | Cause | Fix | Since |
| :--- | :--- | :--- | :--- |
| The last key binding, "Decrease Main Drive Power", could not be scrolled to and had a stray space | Row count one short | Fixed in the PDA and main menu | 0.3.7 |
| Mouse wheel could not zoom back out of cabin close-ups (posters, desk PC) | Only screens handled it | Handled | 0.3.7 |
| Station terminal typing clicks and beeps swapped depending on where you loaded | Sounds were attached to the wrong object | Fixed, then refined for button beeps | 0.3.8, 0.3.9 |
| Audible "Unknown room" `[ERROR]` spam when cycling past a ship's last room | Logged as an error | Silenced | 0.2.0 |
| `Unable to parse line '' in config file` in the log on every launch | The file's trailing newline made an empty last "line" | Empty lines are skipped, real bad lines still reported | 0.4.2 |
| Music player stopped working after a few tracks | Leaked sound handles | Released | 0.1.0 |
| Infopedia list and text pane cut the bottom row in half | Heights not a whole number of rows | Trimmed | 0.4.0 |
| Dead `?` and log buttons on the square Comms Download terminal | `hasmenu=true` on a screen with no menu | Cleared | 0.4.0 |
| Console Weapons and Cargo tabs ignored helm damage on three ships | Missing `linkto=helm` | Added | 0.4.0 |
| Enceladus airlock door buttons did not line up with their plates | Colliders 1-2 units off | Moved | 0.3.8 |
| Enceladus Dock Con "Undock" button was 30 px left | `x=128` | `x=158` | 0.3.8 |

## Data and text

| Bug | Cause | Fix | Since |
| :--- | :--- | :--- | :--- |
| Aki Hasagawa tells you to use "blue nebulae only", but the starting nav screens draw every nebula the same colour (all blue on the NM/60 and SNM/50, all green on the NM/80, NM/99, SNM/40 and SNM/66) | Only the CNM and NV/T nav computers show the kinds apart | Two lines added to his conversation saying which nav computer you need | 0.4.2 |
| "unknown mesh" error for background NPCs with one beard style | A typo in one cosmetics field | Corrected | 0.2.0 |
| "CLASH between additions" log spam on boot | Dead hairstyle tokens after headgear in 13 NPC files | Removed | 0.1.0 |
| GRA 5 grappling arm missing 8 of 10 components in some conditions | Short `configuration=` arrays | Completed | 0.3.3 |
| Six LADAR modules showed every component one slot off | A stray leading value in `configuration=` | Removed | 0.3.3 |
| About 450 spelling and grammar mistakes in about 320 text files; a broken `$amonut` reward token; dialogue flags that could never advance | Typos | Corrected (news and info files in place, with backups) | 0.4.0 |

## Sensor rating cut-offs (a 0.4.2 change)

These are the bands the shop and mechanic now use. Only the label changes, never the sensor. They were picked so the eleven shop sensors
spread across the five bands as evenly as their values allow: several sensors share exactly the same figure (for example D4 and T9, or
C1 and T0), and tied sensors always land in the same band, so a perfect 2-2-2-2-2 is not possible.

| Rating | V. Bad | Bad | Medium | Good | V. Good |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Detect Rng** (sensor quality) | below 0.7 | 0.7 to 0.85 | 0.85 to 1.05 | 1.05 to 1.25 | 1.25 and above |
| sensors | D2, D4, T9 | C1, T0 | M1, M2, SL | SM, C5 | SQ (RM-SNS) |
| was before 0.4.2 | below 0.8 | 0.8 to 1.0 | 1.0 to 1.2 | 1.2 to 1.4 | 1.4 and above |

| Rating | V. High | High | Moderate | Low | V. Low |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Sns. Ghsts** (average ghosts) | below 215 | 215 to 245 | 245 to 310 | 310 to 375 | 375 and above |
| sensors | D2, D4 (Probe) | C1, C5 | SL, SM, SQ (RM-SNS) | T0 | M1, M2, T9 |

## Build support

| Problem | Fix | Since |
| :--- | :--- | :--- |
| 25 of the 34 client fixes refused to apply on the GOG build of `ois.exe` (a separate compile, so every address differs) | Recognised by its build stamp and patched at the GOG addresses ([Issue #64](https://github.com/l33way/ois-patcher/issues/64)); the newest 9 are skipped there for now | 0.4.2 |

## Known and not yet fixed

Reported, but not fixed in this patch: changing rooms with critical hull damage can crash; emission-control states are not remembered across docking; civilians do not react to torpedoes; hailing and dropping cargo for
civilians; the default IFF; sensor ghosts stay after sensors are disabled; the skip-intro white screen; the config file being
regenerated; audio device changes needing a restart; the touch input offset in fullscreen at 100% and 150% scaling.
