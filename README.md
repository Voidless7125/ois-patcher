# Objects in Space — Unofficial Bugfix Patch

**Author:** Leeway ([steamcommunity.com/id/l33way](https://steamcommunity.com/id/l33way/))  
**Major Contributor & QA:** [Voidless7125](https://github.com/Voidless7125)

An unofficial community patch for *Objects in Space*, the space-stealth game by Flat Earth Games. It fixes numerous crashes (including the Pirate Hunt crash and the station-to-ship transition crash), broken modules, autopilot bugs, power-drain math, UI glitches, and over 450 text/dialogue typos—while staying strictly faithful to the developers' original vision.

> **Safe by default:** Before anything is modified, the patcher automatically backs up your original `ois.exe` and `ois_server.exe` as `.original-backup` files, and you can uninstall with a single command at any time.

---

## Quick Start (Step-by-Step for Beginners)

### Step 1: Install Python (via Python Install Manager)

Python on Windows is installed using the official **Python Install Manager (`.msix`)** from [python.org/downloads](https://www.python.org/downloads/) ([official Python Windows docs](https://docs.python.org/3/using/windows.html)):

1. **Download and Run the Installer:**
   - Go to [python.org/downloads](https://www.python.org/downloads/) and click the yellow **Download Python Install Manager** button to download the `.msix` file.
   - Double-click the downloaded `.msix` file and click **Install**.
2. **Finish the Automatic Terminal Setup & Enable `PATH`:**
   - As soon as the `.msix` installation finishes, a terminal window will **launch automatically** to install the default Python runtime.
   - When prompted in that terminal window to **add the global commands directory (`%LocalAppData%\Pythonin`) to your `PATH`**, press **`y`** (Yes) so `python`, `py`, and `pip` work everywhere.
   - *(Note: If you didn't get the prompt or closed the window early, open PowerShell or Command Prompt and run `py install default --configure`. If you need to add the directory to `PATH` manually later, click Start, search for **"Edit environment variables for your account"**, and add `%LocalAppData%\Pythonin` to your user `Path`.)*
3. **The `pefile` Package:**
   - The patcher needs the `pefile` package to read and patch the game files. If it isn't installed yet, **`ois_patcher.py` will automatically ask if you want to install it** right when you run it and will handle it for you (or you can install it manually anytime via `py -m pip install pefile`).

### Step 2: Download and Extract the Patcher

**Choose your preferred installation method below:**

#### Method A: Download the ZIP (Recommended for most players)
1. Download the latest release `.zip` from the [Releases page](https://github.com/l33way/ois-patcher/releases) (or click the green **Code → Download ZIP** button on GitHub).
2. **Right-click** the downloaded `.zip` file in File Explorer and click **Extract All...**.
   - **Important:** Do not double-click `ois_patcher.py` from *inside* the unextracted `.zip` preview! Extract the entire folder first and keep all files (`ois_patcher.py`, `apply_data_fixes.py`, `text_fixes.py`, and the `mod/` folder) together inside the same folder.

#### Method B: Use Git Clone (Advanced — best for seamless auto-updates)
If you are comfortable using Git, cloning the repository directly enables the patcher's built-in self-update feature so you can pull new fixes instantly:
1. Open a terminal where you want to keep your patcher files and clone the repo:
   ```powershell
   git clone https://github.com/l33way/ois-patcher.git
   cd ois-patcher
   ```
   *(Note: If you are using a personal fork such as Voidless7125's repository, clone your fork's URL instead so auto-update fetches from your fork).*
2. The patcher will automatically verify your remote URL and check for updates on future runs.

### Step 3: Run `ois_patcher.py`

- **Easiest way (ZIP install):** Open your extracted folder in File Explorer and **double-click `ois_patcher.py`**.
  - A window will open, automatically find your Steam (or GOG) *Objects in Space* installation, back up your original files, apply all binary and mod fixes, and wait for you to **press any key to close** when finished.
- **From a Terminal:** You can also open a terminal in the patcher folder and run:
  ```powershell
  py ois_patcher.py
  ```

### Step 4: Verify the Output

At the end of the run, you should see a summary right above `Press any key to close this window...`:

```text
Applied 27 exe fix(es), skipped 0.
ois_server.exe: applied 5 fix(es), skipped 0.
Bugfix mod: installed
```

That's it! Launch *Objects in Space* through Steam as normal.

---

## Updating, Checking Status, & Uninstalling

### Updating to a Newer Release
- **If you used the ZIP:** Download and extract the new release over your existing folder (or re-run `ois_patcher.py`). It detects the older patch version, restores your clean `.original-backup` files automatically, and applies the newest fixes cleanly on top.
- **If you used `git clone`:** Simply run `py ois_patcher.py`. The script will automatically check GitHub for upstream updates, show you the commit changelog, and ask if you'd like to pull and re-run automatically.

### Command-Line Options
If you run `ois_patcher.py` from Command Prompt or PowerShell, you can pass these options:

| Command | What it does |
| :--- | :--- |
| `py ois_patcher.py` | Auto-detects your game install and applies/updates the patch. |
| `py ois_patcher.py "C:\Path\To\Objects in Space"` | Patches a specific game folder (use quotes if the path has spaces). |
| `py ois_patcher.py --status` | Shows whether your game is patched, which version is installed, and backup status without changing anything. |
| `py ois_patcher.py --uninstall` | Restores your original `ois.exe`, `ois_server.exe`, and `assets/` files from backups and removes the `oisbugfix` mod. Leaves save games untouched. |
| `py ois_patcher.py --force` | Forces a fresh re-patch from backup even if already on the current version. |
| `py ois_patcher.py --yes` | Skips confirmation prompts and exits immediately without waiting for a keypress (for scripts). |
| `py ois_patcher.py --pds-everything` | (this branch) Applies the point-defence variant described below. |
| `py ois_patcher.py --debug-iff` | (this branch) Diagnostic: logs NPC IFF changes to the debug log. |
| `py ois_patcher.py --weapon-spinup-fix` | (this branch) Weapon tube spin-up gets shorter with better parts instead of longer. |
| `py ois_patcher.py --mechanic-armaments` | (this branch) The station mechanic also sells the M-6 light torpedo and the TD-8 stellar probe. |
| `py ois_patcher.py --ui-extras` | (this branch, data only) Sensors AUTO button on every ship; depot buttons on the Enceladus docking screen. |
| `py ois_patcher.py --depots` | (this branch, data only, experimental) Places a DP-9 depot next to the first station of each main system. |
| `py ois_patcher.py --civilians-comply` | (this branch) Applies the civilian-demands variant described below. |

### Manual Uninstall (If Needed)
If you ever want to revert everything by hand without running the script:
1. Copy `ois.exe.original-backup` back over `ois.exe` (and `ois_server.exe.original-backup` over `ois_server.exe`).
2. Delete the `ObjectsInSpace/mods/oisbugfix` folder.
3. Copy the files from `oisbugfix_original_assets/` back into `assets/`, then delete `oisbugfix_original_assets/` (or run Steam's **"Verify integrity of game files"**).

---

## Troubleshooting

- **Double-clicking `ois_patcher.py` asks "How do you want to open this file?"**  
  Python isn't associated with `.py` files yet, or the first-time setup didn't finish. Open PowerShell or Command Prompt and run `py install default --configure` (or `py install --refresh`), or run the patcher from a terminal in the extracted folder with `py ois_patcher.py`.
- **`'py'` or `'python'` is not recognized:**  
  1. Make sure you opened a **new** terminal window after installing Python.
  2. If you had an older version of Python installed previously, uninstall the old **"Python Launcher"** from Windows **Installed Apps** and check **Settings → Apps → Advanced app settings → App execution aliases** to make sure the **`python.exe`** and **`py.exe`** aliases are toggled **On** ([Python Windows Troubleshooting docs](https://docs.python.org/3/using/windows.html#troubleshooting)).
  3. To check your `PATH` manually, click Start, search for **"Edit environment variables for your account"**, and ensure `%LocalAppData%\Pythonin` is listed under your user `Path`.
- **`This script needs 'pefile'`:**  
  Open PowerShell or Command Prompt and run `py -m pip install pefile`.
- **"Could not automatically find the game folder":**  
  When prompted in the window, copy and paste the path to your `Objects in Space` folder (e.g., `C:\Program Files (x86)\Steam\steamapps\common\Objects in Space`) and press Enter.

Still stuck? [Open an issue on GitHub](https://github.com/l33way/ois-patcher/issues) with what you tried and what message appeared.

---

## What Does This Patch Fix?

See **[CHANGELOG.md](CHANGELOG.md)** for the full release history, issue links, and detailed technical breakdown of all 33+ binary and data fixes. Highlights include:

- **Crash Fixes:** Fixes the **station-to-ship transition crash** ([#58](https://github.com/l33way/ois-patcher/issues/58)), **Pirate Hunt** scenario crashes on both client and co-op server ([#2](https://github.com/l33way/ois-patcher/issues/2)), **LADAR equip & save-load crashes** ([#13](https://github.com/l33way/ois-patcher/issues/13)), **PDA portrait-render crashes**, **post-hull-destruction monitor crashes** ([#22](https://github.com/l33way/ois-patcher/issues/22)), **engineering addon drag crashes** ([#16](https://github.com/l33way/ois-patcher/issues/16)), and **terminal `DEL` command crashes** ([#32](https://github.com/l33way/ois-patcher/issues/32)).
- **Gameplay & Ship Systems:** Point-defence lasers now actually shoot down incoming torpedoes ([#51](https://github.com/l33way/ois-patcher/issues/51)), autopilot no longer burns away after overshooting or drains batteries at max cruise speed, power drain UI and actual battery draw now respect component power modifiers ([#37](https://github.com/l33way/ois-patcher/issues/37)), standalone scenarios no longer overwrite campaign Save Slot 1, and Full Stop while docked no longer bypasses undocking fees/airlocks ([#11](https://github.com/l33way/ois-patcher/issues/11)).
- **Modules & Co-op:** Fixes broken GRA 5 and LADAR component slots ([#7](https://github.com/l33way/ois-patcher/issues/7)), prevents NPC-only modules from appearing in shops ([#50](https://github.com/l33way/ois-patcher/issues/50)), restores the 71 unused module-purchase welcome emails, fixes the unloadable *"Escort: Make a Break"* co-op scenario, and fixes *"Quit to Menu / Quit to OS"* freezing LAN clients.
- **Audio, UI & Text:** Fixes the music player handle-leak failure loop, missing station terminal beeps/clicks ([#21](https://github.com/l33way/ois-patcher/issues/21), [#35](https://github.com/l33way/ois-patcher/issues/35)), hidden *"Decrease Main Drive Power"* keybind ([#27](https://github.com/l33way/ois-patcher/issues/27)), cabin scroll-wheel zoom-out ([#24](https://github.com/l33way/ois-patcher/issues/24)), Enceladus button alignments ([#25](https://github.com/l33way/ois-patcher/issues/25), [#26](https://github.com/l33way/ois-patcher/issues/26)), console damage displays ([#45](https://github.com/l33way/ois-patcher/issues/45)), and ~450 spelling/grammar mistakes across ~320 game text files (including the broken `$amonut` reward token).

---

## Project Philosophy & Design Scope

### Goal: Restoring Original Intent, Not Adding New Features
*Objects in Space* is a genuine work of art that was sadly abandoned before completion. Every fix in this patch exists because something the developers clearly intended to work is broken, unreachable, or crashes. The scope is deliberately narrow: **restore the game to the state it evidently was meant to ship in—not redesign it, rebalance it, or extend it.**

- **Unambiguous bugs are in scope:** Typos, missing bounds-checks, leaked resource handles, use-after-free bugs, and identifiers one character too long for fixed-size network buffers.
- **Deliberate design choices are left alone:** Even if a mechanic feels restrictive, if it is enforced by an intentional developer filter (such as LADAR modules being deliberately excluded from shop purchase lists), this patch does not alter it.
- **No guesswork disguised as restoration:** Nothing here touches economy, difficulty, or content balance.

### Why a Python Script Instead of a Pre-Patched `ois.exe`?
Distributing a source script that patches your own installation rather than a pre-modified `.exe` is a deliberate security and copyright choice:
1. **Visibility & Security:** Anyone can read `ois_patcher.py` and `apply_data_fixes.py` to inspect every exact byte and file modified, rather than trusting an opaque binary from the internet.
2. **No Redistributed Game Assets:** Both the binary patches and data fixes are generated on the fly from your own local `Objects in Space` installation, so Flat Earth Games' copyrighted files are never bundled in this repository.

### What's in This Folder
Keep all of these files together in the same folder:
- **`ois_patcher.py`** — The main script you run (or double-click).
- **`apply_data_fixes.py`** — Imported automatically by `ois_patcher.py` to generate the `oisbugfix` mod from your local `assets/` files.
- **`text_fixes.py`** — Spelling and grammar correction snippets loaded automatically by `apply_data_fixes.py`.
- **`mod/oisbugfix/`** — Contains `modinfo.txt`; populated at install time by `apply_data_fixes.py`.

---

## Personal variants (this branch only)

This branch (`personal-variants`) is `master` plus the extras below. None of them are on `master`:
they are gameplay changes or fixes the upstream maintainer has not accepted.

- **Torpedo that loses its target drifts** (always applied on this branch): when the ship a torpedo
  is homing on is destroyed, the torpedo no longer re-targets the nearest contact; it drifts and can be
  re-targeted by hand (exe, client and server; `tools/torp/`).
- **`--debug-iff`** (diagnostic, off by default): logs every change of an NPC ship's IFF flag to the debug
  log as `IFFDBG <ship>: IFF <old> -> <new>, changed inside|outside the AI update`. Used to find out why some
  ships (e.g. Leslie Garbut's SS Jolly Rancher in the intro) arrive with their IFF off (`tools/iffdebug/`).
- **`--weapon-spinup-fix`** and **`--mechanic-armaments`** (optional, off by default): described below.
- **`--pds-everything`** and **`--civilians-comply`**: optional flags, described below. Without
  `--pds-everything` this branch applies the same point-defence fix as `master`; with it, the variant
  below replaces that fix.

### Optional variant: weapon spin-up gets shorter with better parts (`--weapon-spinup-fix`)

**Not a bug fix as far as the maintainers can prove, and off by default.** Every timer a module's
efficiency touches is `base x (2 - e)` (`e` = efficiency / 100): grapple, hack, comms sync, countermeasure
reload, point-defence reload, jump-drive spin-up, nav and helm boot. A weapon tube's spin-up is the one that
isn't: it is `spinuptime x e x 0.5`, so better parts make a torpedo spin up *slower*. The jump drive uses the
same field name and the same "spin up" button and does it the other way. There is no developer statement
either way, and the fix cuts spin-up to roughly a third, so it is an opt-in rather than part of the standard
patch.

```
python ois_patcher.py --weapon-spinup-fix
python tools/spinup/test_spinup.py <game dir>/ois.exe
```

Seven places compute the figure (the timer start in `ShipModule::runLogic`, the progress bar's denominator
in four UI/text functions and `doSetWeaponTarget`, and the timer restart in `Ship::fireWeapon`); all seven
must agree, so each one's call to `getEfficiencyPercent` goes through one 13-byte stub that returns
`200 - efficiency`. Client and server. Spin-up in game time units, by launcher:

| Launcher | Tubes | spinuptime | Stock build, before -> after | Best parts, before -> after |
|---|---|---|---|---|
| MPL-060 | 2 | 26.5 | 16 -> 10 | 17 -> 8 |
| PL-900 | 4 | 24 | 18 -> 5 | 20 -> 3 |
| PL-920 | 4 | 21.5 | 17 -> 3 | 19 -> 1 |
| SPL-5S | 6 | 17 | 11 -> 5 | 12 -> 4 |
| SPL-9S | 8 | 20 | 14 -> 5 | 15 -> 4 |

Efficiency of 200% or more would make the figure zero or negative; no weapons module reaches that with legal parts.

### Optional variant: the mechanic sells the M-6 and the TD-8 (`--mechanic-armaments`)

**Not a bug fix, off by default.** `weapons.txt` defines six launchable armaments (M-10, M-12, E-10, TD-4,
M-6, TD-8) but the station mechanic's Armaments tab only knows four. The game's own code indexes a four-entry
table of weapon ids, and the screen has one button per entry. The M-6 ("a small missile often used by
pirates") is only ever fitted to NPC ships; the TD-8 is only handed out by Dr Reiffel's quest. This variant
adds both to the Armaments tab and to the list of prices above its buttons.

```
python ois_patcher.py --mechanic-armaments
python tools/mech/test_mech.py <game dir>/ois.exe
```

What it changes:

- **Exe (client and server):** the four instructions that index the id table are redirected to caves that
  look the id up in a six-entry table, computed position-independently (the game does not load at its
  preferred base, so a table of absolute pointers would need relocations). The countermeasure line in the
  armament list, recognised by index 4, moves to index 6.
- **`ui_x7.txt`:** the "Mechanix" screen gets two buttons, and its armament buttons move up to make room
  (pitch 12, first one at y=140).
- **`weapons.txt`:** the TD-8 gets a price (**350**; this project's own number, the game ships it with none)
  and `canprobestar=true`. The game reads `canprobestar`, which makes a probe ignore heat damage, but the
  file spells it `probestar`, so the "stellar survey probe" was never heat-proof.

Selling pays half the base cost, so a TD-8 from Dr Reiffel now sells for 175. Not tested in the running game.

### Optional, data only: screen features the game still has (`--ui-extras`, `--depots`)

Neither changes the exe. Re-run with the same flags to keep them, like the other variants.

**`--ui-extras`**
- **Sensors AUTO button.** The commands `SENSOR_SET_AUTO` / `SENSOR_UNSET_AUTO` and the state `SENSORS_AUTO` are still in the exe,
  and the UI lines were commented out in the Ceres, Enceladus and Remora files. While AUTO is on, the sensor screen keeps the
  most dangerous contact selected (`getMostDangerousSensorObject`, "Auto-selected new object" in the debug log), and switching it on
  turns off the LINK button's "keep the nav selection" flag. The commented-out lines sat on top of the LADAR button (Enceladus) or
  inside the waveform display (the Ceres copy kept the Remora's row), so the button goes in the free space right of LADAR
  (x=101) on every ship, including the Proxima, which uses the Ceres screens. `python tools/ui/check_extras.py <mod folder>`
  checks that it overlaps nothing.
- **Depot buttons on the Enceladus docking screen** (Repair Systems, Repair Hull, Buy CM, Buy Torpedo), copied from the
  Ceres/Proxima screen, which already has them.

**`--depots` (experimental).** A depot is a `DP-9 Depot` station class (`type=depot`, "a standard support platform containing
repair drone systems") with a `begin depot` sector block, the docking-screen buttons above and the code behind them: hull repair
(5 credits per repair point), module repair, countermeasure refill, and a rearm that fills empty torpedo tubes with M-10s.
No sector file uses it, so the buttons never show. This flag places one depot, 25 Gm from the first listed station, in each of the
twelve main systems (`OP-DEPOT00` to `OP-DEPOT11`). The depot loader does not read `emissionstrength` the way stations and
jumpgates do, so whether a depot can be seen and docked with is a guess. Nothing in the stock game ever places one.

### Optional variant: a point-defence system that works (`--pds-everything`)

This is **not a bug fix and is off by default.** It changes gameplay balance, so
it is a separate opt-in rather than part of the standard patch.

Without the flag this branch applies the same point-defence fix as `master` (the laser can destroy
torpedoes, and still only shoots ships with their IFF off). With the flag, the variant below
**replaces** that fix; the two are never applied together.

```
python ois_patcher.py --pds-everything
```

**Why the stock PDS never stops a torpedo.** From the decompiled code, in order of
importance:

1. **The shot does nothing to a torpedo.** The PDS "hits" by calling the same
   `Ship::damage` routine used for ships, and that routine returns immediately for
   vessel type 4 (torpedoes, probes, mines). Torpedoes can be *selected* but never
   *hurt*. That is the real bug.
2. **It only picks the first thing in range.** Selection walks the sector's vessel
   list and returns the first one that has its IFF transponder off or is a weapon,
   so a nearer no-IFF ship wins over an incoming torpedo.
3. **Even when it can hurt something it usually misses.** It must roll a 1 on the
   module's hit dice (`hitchance=1d6` on the PDL 101), once per reload.

**What the variant changes**

- Targets, in priority order: **hostile torpedoes, probes and mines** first, then
  **ordinary ships whose IFF transponder is off**, then **enemy countermeasure decoys**.
- Never targeted: **ships with their IFF on**, **space stations and jump gates**, **ships that are docked**,
  **your own ship**, and **your own torpedoes/probes/mines/decoys**.
- A locked torpedo is simply destroyed (no hit roll, and no warhead blast at
  point-blank range). Ships still take the stock heat damage and still need the hit
  roll; a destroyed decoy's timer is expired so the game removes it.
- It applies to `ois.exe` **and** `ois_server.exe`, and to NPC ships' PDS modules too.

**Things to know before using it**

- It leaves ships with their IFF on alone, but fires on any ship with its transponder off,
  friendly or not. Docked ships and stations are also left alone.
- Throughput is still limited by the module's own range, power and reload time, so a
  large salvo can overwhelm it.
- The caves are emulation-tested (`tools/pds/test_pds.py`), but nobody has watched a
  torpedo get shot down in the live game yet. Report what you see.
- The variant is recorded in the exe's version marker (`v0.4.0+pds`). Running the
  patcher with or without the flag later switches between the two through the normal
  restore-and-repatch, after asking. `--uninstall` removes either.

### Optional variant: civilians who give in (`--civilians-comply`)

Also **not a bug fix and off by default.** It combines with `--pds-everything` (the
exe records both: `v0.4.0+pds+civ`).

```
python ois_patcher.py --civilians-comply
```

**What the stock game does** (decompiled `ShipBehaviour::respondToPirateDemand`, run
when you pick "Drop your cargo or be fired upon." on a hail):

- A civilian rolls `rand()%100+1 <= chance`. The base chance is looked up by the
  captain's **style** - the `captainstyle=` value in the scenario data, or a random one
  for generated traffic: **cautious 100 %, moderate 90 %, reckless 60 %, very reckless
  15 %**. (Style is a combat personality in the data files: how far the captain runs the
  battery down and at what firing solution. The developers reused it here.) **The roll
  does not look at how much cargo they carry, what it is worth, or whether they smuggle.**
- If your **IFF is on** it is forced to **2 %** ("You realise your IFF is on?"); beyond
  120 units it is cut to two thirds, beyond 180 units to 5 %. A very reckless captain at
  mid range is therefore about 10 %.
- If the civilian's *own sensors* hold a weapon contact within 100 units, the chance
  becomes the table value x 1.5 (max 100). Otherwise a failed roll says **"We'll
  believe it when we see a torpedo."** - whether or not you have just fired one that
  the civilian cannot see yet.
- The first thing it does is add your registration to a list kept on the civilian.
  `PrivateCommsManager::switchTo` refuses to open a conversation with any ship whose
  list contains you, so after **one** demand - complied with or not - **you can never
  hail that ship again.**
- When a civilian does comply it jettisons one random non-empty pod. With an empty hold
  it still says "We are complying" and drops nothing.

**What the variant changes**

1. The chance table becomes **cautious 100 %, moderate 90 %, reckless 70 %, very
   reckless 35 %** (reckless +10, very reckless +20; the two cautious tiers are already
   near-certain and are left alone).
2. A torpedo, probe or mine **you launched that is still in flight within 250 units**
   of the civilian counts as "seen", whatever the civilian's sensors say, so it gets
   the x 1.5 boost instead of the "believe it when we see a torpedo" refusal.
3. Your registration is **no longer added to the civilian's list**, so you can keep
   hailing it (and demanding again).

Unchanged: the dice, the IFF-on rule and distance penalties, pirates, authorities,
and everything about NPC ships that are not civilians. Applies to `ois.exe` and
`ois_server.exe`.

**Things to know**

- An earlier build of this variant used 100/100/90/60, which made nearly every
  civilian comply; this is the toned-down version.
- A torpedo that has already hit, been shot down or timed out does not count; only one
  still in flight does. With your IFF on and no torpedo near, the chance is still 2 %.
- Being able to re-hail means you can demand repeatedly and strip a civilian's cargo
  pods one by one. That is the point, but it is more generous than the stock design.
- Making the chance depend on cargo amount, value or smuggling would be a new mechanic
  rather than a tweak; it is not in this variant.
- Tested in a CPU emulator (`tools/civ/test_civ.py`), not yet seen in the live game.

## Limitations, Liability, & License

- **Tested Build:** Tested against the **Windows Steam** build of *Objects in Space* (**v1.0.8**). Every patch site verifies its exact original bytes before modifying anything and safely skips itself with a warning if a byte doesn't match.
- **Limitation of Liability:** This patch is provided "as is," without warranty of any kind. Use at your own risk. While `.original-backup` files are created automatically, you are responsible for keeping backups of your game and save files.
- **License:** [CC BY-NC 4.0](LICENSE) — Free to use, share, and adapt for non-commercial purposes with credit to the original author (**Leeway**). See [LICENSE](LICENSE) for full terms.
