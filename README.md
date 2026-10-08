# Objects in Space — Unofficial Bugfix Patch

**Credit:** Leeway ([steamcommunity.com/id/l33way](https://steamcommunity.com/id/l33way/))

An unofficial bugfix patch for *Objects in Space*, an incredible (but
sadly abandoned) space-stealth game by Flat Earth Games. Fixes several
crashes and one long-standing spam bug, and adds a small mail-terminal
feature.

This is a community patch, not an official release. Use at your own
discretion — a backup of your original `ois.exe` and `ois_server.exe`
(the co-op server binary, which ships alongside `ois.exe` in every
Windows Steam install) is made automatically before anything is touched
(see below).

## Why I built this

*Objects in Space* is a genuine work of art. It just never got finished.
This patch is my attempt to change that — fixing what's broken, so it
can be closer to what it was meant to be.

## Goal: restoring original intent, not adding new features

Every fix in this patch exists because something the developers clearly
intended to work is instead broken, unreachable, or crashes. The scope
is deliberately narrow: **restore the game to the state it evidently was
meant to ship in — not redesign it, rebalance it, or extend it.**

In practice, that means:

- **A typo, a missing bounds-check, a leaked resource handle,
  an identifier one character too long for a fixed-size
  buffer** — these are unambiguous bugs. Restoring the evidently
  intended behavior is squarely in scope.
- **Deliberate design choices are left alone, even ones that feel
  restrictive or arbitrary.** If something is disabled by a hardcoded
  developer list rather than broken by accident, that's a design
  decision, not a bug — no matter how tempting a "fix" might be. (One
  investigated example: LADAR modules turned out to be intentionally
  excluded from the in-game shop's purchase list, confirmed via
  disassembly of the actual filter the developers wrote — not a data
  bug, not touched by this patch.)
- **When a fix can't be pinned to a specific, proven original
  behavior, this README says so plainly instead of presenting a guess
  as a restoration.** Releases 0.3.0–0.3.8 broke this rule once: they
  made the mail-terminal `DEL` command able to delete commands on the
  theory that the developers had meant it to. The original game never
  did that (it only ever answers "cannot delete system file"), so 0.3.9
  removed the feature and keeps only the crash fix.
- **Nothing here touches economy, difficulty, or content balance.**
  Every fix corrects something that was never supposed to happen in the
  first place, not something the developers shipped on purpose but that
  plays out unfavorably.

None of this is a judgment against going further — it's just not what
*this* patch is for. If someone wants to build a rebalance, a difficulty
overhaul, new content, or anything else on top of what's fixed here, I
fully support that effort. This code is here to be built on for exactly
that kind of work, within the terms of the license below.

## Why a Python script instead of a pre-patched `ois.exe`?

This patch is distributed as source — a script you run against your own
copy of the game — rather than as an already-patched `ois.exe` you'd
just drop in. That's a deliberate choice, not a convenience shortcut:

- **Visibility.** You can read exactly what the patcher does before you
  run it: every patch site, every byte it checks and changes, every
  file it copies. A pre-built exe hides all of that behind an opaque
  binary diff.
- **External verification.** Anyone can independently check the
  patcher's claims against the real game binary — disassemble the
  patch sites, confirm the before/after bytes, verify nothing beyond
  what's documented here actually changes. That's not practical against
  a binary you're just told is safe.
- **Lower security risk.** A modified game executable from an
  unofficial source is exactly the kind of thing that's easy to hide
  something unwanted inside. A plain, readable script that only ever
  touches the specific bytes it prints and explains is a much smaller,
  much more inspectable trust surface — you (or anyone else) can verify
  it does only what it says, instead of taking a stranger's binary on
  faith.

The same reasoning is why the data-only fixes (see `apply_data_fixes.py`
below) aren't shipped as ready-made files either — they're generated
from your own game install at run time, so this repo never bundles a
copy of Flat Earth Games' own content.

## What's in this folder

Only one file here is ever run directly — the others are support
files it needs sitting alongside it. **They must all stay together in
this same folder structure** (don't move or rename them individually):

- **`ois_patcher.py`** — **this is the one you actually run.** A single
  invocation locates your game, patches `ois.exe` and `ois_server.exe`,
  and generates and installs the bugfix mod, all in one pass (see
  "Installation" below).
- `apply_data_fixes.py` — not something you run yourself. `ois_patcher.py`
  imports and calls it automatically to build the data-only fixes
  (typo/data corrections, generated fresh from *your own* `assets/`
  folder rather than shipped as ready-made files — see the file's own
  header for why).
- `text_fixes.py` — data, not something you run. The spelling and grammar
  corrections for the game's text files, in the same short-snippet form as
  the other data fixes; `apply_data_fixes.py` loads it automatically and
  warns and skips it if it's missing. Generated by `tools/textcheck/`, which
  is optional and not needed to patch.
- `mod/oisbugfix/` — a folder, not a single file. Contains `modinfo.txt`
  (this mod's own metadata, original content). `apply_data_fixes.py`
  fills in the rest of this folder's contents at install time; keep the
  folder itself intact and in place.

## Requirements

- **Python 3.8 or newer.**
  - **Check if you already have it:** open a terminal (see step 2 under
    "Installation" below for how) and run `python --version`. If that
    prints something like `Python 3.11.4`, you're set — skip ahead to
    Installation.
  - **If it's not found, install it:** go to
    [python.org/downloads](https://www.python.org/downloads/), download
    the Windows installer, and run it. **On the installer's very first
    screen, check the box "Add python.exe to PATH"** before clicking
    Install — this is the single most commonly-missed step, and without
    it none of the commands below will work. (Don't install Python from
    the Microsoft Store instead — it uses a different mechanism that
    can behave inconsistently for a script like this one.)
  - **After installing,** close any terminal window you already had
    open and open a new one (a terminal opened before installing Python
    won't see the update), then confirm it worked with `python --version`
    again.
- **The `pefile` package.** Once Python itself is installed, open a
  terminal and run:

  ```
  pip install pefile
  ```

  `pip` comes bundled with Python when installed from python.org, so
  this should just work right after the step above. If `pip` also isn't
  recognized, try `py -m pip install pefile` instead (see the `py`
  launcher note under Troubleshooting below).
- **`git` (optional).** Only needed if you want the patcher to check for
  and pull its own updates from a `git clone` of this repo (see
  "Checking for updates" below). Not required for anything else — a
  plain downloaded-and-unzipped copy works fine for patching, checking
  status, and uninstalling; the patcher just won't be able to update
  itself and will say so.

## Installation

**1. Download and unzip the patcher.** Get the latest release from the
[GitHub repo](https://github.com/l33way/ois-patcher) — either the
Releases page, or the green "Code → Download ZIP" button — then extract
it: right-click the downloaded `.zip` file in File Explorer and choose
"Extract All...". Don't try to run anything straight out of the zip;
extract it to a real folder first. `ois_patcher.py`, `apply_data_fixes.py`,
and the `mod/oisbugfix/` folder (see "What's in this folder" above) all
need to end up together in that one extracted folder.

(If you'd rather clone the repo with `git` instead of downloading a
zip, that works too — and it's what lets the patcher check for and pull
its own updates later. See "Checking for updates" below.)

**2. Open a terminal in that folder.** In File Explorer, open the
folder you just extracted (the one containing `ois_patcher.py`), then
either type `cmd` into the address bar and press Enter, or
Shift+right-click empty space in the folder and choose "Open PowerShell
window here" / "Open in Terminal."

**3. Run this one command:**

```py
python ois_patcher.py
```

That's it — no path required. The patcher looks for your game the same
way Steam itself would: Steam's own registry entries and default
install folders, and every Steam library (including ones on other
drives). It also checks GOG's registry records as a best-effort
addition — that part is less thoroughly tested (see "Limitations"
below), so a GOG install may not always be found automatically. If it
finds exactly one install, it uses it and tells you which one. If it
finds more than one, it lists all of them and asks which to patch —
nothing is ever silently picked for you between two installs. If it
can't find one at all, it asks you to paste the path.

If you'd rather point it at a specific copy yourself — say, you have
more than one install and want to skip the prompt, or auto-detection
doesn't find yours for some reason — you can still give it the path
explicitly, same as before:

```py
python ois_patcher.py "C:\Path\To\Objects in Space\ois.exe"
```

or, equivalently:

```py
python ois_patcher.py --game-dir "C:\Path\To\Objects in Space"
```

- Either the folder itself or the `ois.exe` inside it works — the
  patcher figures out which you gave it.
- **Keep the quotes around the path.** The default Steam install path
  contains a space (`Objects in Space`), and an unquoted path with a
  space in it will fail or silently target the wrong thing.
- A typical default path looks like:
  `C:\Program Files (x86)\Steam\steamapps\common\Objects in Space\ois.exe`
- Running it repeatedly with an environment variable instead — say,
  from your own script — is also supported: set `OIS_TARGET_DIR` to
  your install folder and just run `python ois_patcher.py` with no
  argument. An explicit path or `--game-dir` always overrides it.

**That's it — one command, one run.** You do not need to run
`apply_data_fixes.py` yourself, and there is no separate mod-install
step: the single command above does everything described below
automatically, in order:

1. Finds your game install (auto-detected, or the path you gave it).
2. Backs up your original `ois.exe` as `ois.exe.original-backup`
   (created once — running the patcher again reuses the existing
   backup rather than overwriting it).
3. Applies the binary fixes listed below, in place.
4. Backs up and patches `ois_server.exe` the same way — it ships
   alongside `ois.exe` in every Windows Steam install and is needed for
   hosting/joining co-op games (singleplayer never runs it, but it's
   still there). Its own separate backup, checked and skipped just as
   safely if anything doesn't match. If it's genuinely missing (e.g. a
   modified install), this step is skipped quietly rather than erroring.
5. Generates and installs the `oisbugfix` mod into
   `ObjectsInSpace/mods/oisbugfix/`, reading the affected files fresh
   out of your own `assets/` folder.
   The one exception is the `news_*` and `info_*` article files: the game
   reads those straight from `assets/` and the mod system can't override
   them, so their spelling fixes are applied to the files in place. The
   untouched originals are saved first in `oisbugfix_original_assets/`
   (next to `ois.exe`, deliberately *outside* `assets/`, where a copy would
   be picked up as a second article).

**4. Check the summary printed at the end.** A successful run ends with
a block like:

```
Applied 9 exe fix(es), skipped 0.
ois_server.exe: applied 2 fix(es), skipped 0.
Bugfix mod: installed
```

If anything shows as skipped, scroll up — the patcher explains exactly
why (usually a different game version, or something already patched).
Skipped items don't stop the rest of the run; every other fix still
applies normally.

Every patch checks the exact bytes it's about to change first, and
skips itself with a warning (rather than guessing) if anything doesn't
match — a different game version, or a file already modified some other
way. It's safe to re-run against an *unpatched* backup at any time.

### Checking what's installed

```py
python ois_patcher.py --status
```

Reports, for your detected (or given) install: whether each exe is
patched and by which version, whether its backup is present and usable,
and whether the bugfix mod is installed. Doesn't check for updates and
doesn't change anything — safe to run any time out of curiosity.

### Updating

Running `python ois_patcher.py` again picks this up on its own — no
separate command needed:

- **Already at the current version:** the exe(s) are left alone, and
  only the data-only mod is refreshed (handy if you ever deleted the
  `oisbugfix` folder by hand and want it back without touching the exe).
- **Patched by an older version of this tool:** you'll be asked to
  confirm, then the patcher restores the original from
  `<name>.original-backup` and re-applies the current fixes on top of
  that clean original — never on top of an already-patched file. Your
  existing backup is kept and reused; nothing is re-downloaded or
  re-copied for this.
- **Patched by a newer version than the copy of the script you're
  running:** the patcher refuses, rather than downgrading you. Get the
  current release and run that instead (see "Checking for updates for
  the patcher itself" below), or pass `--force` if you genuinely want
  to go backward.

You can also force a from-scratch re-patch even when already current
with `--force`, and skip all the "are you sure?" prompts (for scripted
or unattended runs) with `--yes`.

### Checking for updates for the patcher itself

If you got this patcher via `git clone` (rather than a downloaded zip),
a plain `python ois_patcher.py` run also checks whether a newer version
of the *script itself* is available upstream, before it does anything
to your game:

- If your checkout is current, it says so and moves straight on to
  patching.
- If an update is available, it shows what's changed and asks before
  doing anything — this never pulls new code without your say-so, even
  if you passed `--yes` (that only answers the game-patching prompts).
  Say yes with `--update` on the command line to skip that ask (e.g.
  for a scripted update-and-patch run), or decline and it just patches
  with the version you already have.
- If you pulled a newer version, the patcher restarts itself
  automatically to make sure the new code is actually the code that
  runs — you don't need to re-run anything yourself.
- If you downloaded a zip instead of cloning with git, or if `git`
  itself isn't installed, this check is skipped automatically and
  patching proceeds normally with your local copy. Check the
  [GitHub repo](https://github.com/l33way/ois-patcher) yourself now and
  then if you want to know about new releases.

Skip this check entirely (e.g. if you're offline and don't want the
delay) with `--no-update-check`.

### Troubleshooting

- **Double-clicking `ois_patcher.py` makes a window flash and
  disappear instantly.** This usually means Windows closed the console
  before you could read what happened — auto-detection may have needed
  to ask you a question (which one of several installs, or a path to
  paste) that a double-click can't answer. Run it from a terminal
  instead, as shown above, so you can see and respond to any prompts.
- **`'python' is not recognized...`, or a Microsoft Store page opens
  when you try to run it.** Python isn't installed, or isn't on your
  system's PATH. Install it from
  [python.org/downloads](https://www.python.org/downloads/) (not the
  Microsoft Store version, which can behave differently on Windows) —
  and make sure to check **"Add python.exe to PATH"** on the installer's
  first screen. If Python is already installed this way and `python`
  still doesn't work, try `py` in its place (Windows' own Python
  launcher, installed alongside python.org's Python) — e.g.
  `py ois_patcher.py`.
- **`ModuleNotFoundError: No module named 'pefile'`.** You're missing
  the one required package — run `pip install pefile` (or
  `py -m pip install pefile`) in a terminal, then try again.
- **"Could not automatically find the game folder."** Auto-detection
  covers standard Steam installs, plus a best-effort check for GOG (see
  "Limitations" below); an unusual setup (a non-default install path, a
  Steam library it couldn't see, a storefront other than Steam/GOG) can
  miss yours. Paste the path when asked, or run it with the path
  directly: `python ois_patcher.py "C:\Path\To\Objects in Space"`.
- **It found more than one install and I don't recognize one of
  them.** Old installs (a previous drive, an old Steam library you
  haven't cleaned up) can still show up here even if you don't play
  from them anymore. Pick the one you actually use; the others are just
  left alone.
- **It says some fixes were "skipped."** Scroll up in the output — the
  patcher always explains why (usually a different game version than
  this patch targets, 1.0.8, or that file already having been patched
  by an earlier run). This is expected, safe behavior, not a failure —
  every other fix still applies normally.

Still stuck? Open an issue on the
[GitHub repo](https://github.com/l33way/ois-patcher/issues) with what
you tried and exactly what you saw.

### Reverting

```py
python ois_patcher.py --uninstall
```

Run against your detected (or given) install, this puts the game folder
back the way it was: restores `ois.exe` and `ois_server.exe` from their
`.original-backup` files (each one verified to be a genuine pristine
original before it's used, and the restore itself verified byte-for-byte
after writing), removes the `oisbugfix` folder from
`ObjectsInSpace/mods/`, and puts the original `news_*` / `info_*` article
files back from `oisbugfix_original_assets/`. Asks for confirmation first, showing exactly
what it's about to do; add `--yes` to skip that if you're scripting it.
Your save games and every other game file are left untouched.

By default the `.original-backup` files are deleted once they've been
successfully restored from (their job is done). Pass `--keep-backups`
if you'd rather they stick around.

If you'd prefer to do it by hand instead, that still works exactly as
before:

- **Client exe:** copy `ois.exe.original-backup` back over `ois.exe`.
- **Server exe:** if `ois_server.exe.original-backup` exists, copy it back
  over `ois_server.exe` the same way.
- **Mod:** delete the `oisbugfix` folder from `ObjectsInSpace/mods/`.
- **News/info text:** copy the files in `oisbugfix_original_assets/` back
  into `assets/`, then delete that folder. (Steam's "Verify integrity of
  game files" also restores them.)

## Fixes included

- **Pirate Hunt scenario crash** — two independent causes, both fixed on
  both `ois.exe` and `ois_server.exe`: a missing bounds-check in the
  ship spawn-selection loop, and a separate log
  call with too few arguments for its own format string a little
  further down the same code path. Either one alone can crash the
  game/server during ship spawning; the server binary has the
  identical bugs and crashes the same way for anyone hosting or
  joining a co-op game.
- **Music player permanent failure loop** — the music player leaked a
  sound-engine handle on every track change; eventually the pool was
  exhausted and music stopped for the rest of the session.
- **Ship steering recompute spam** (three separate causes) — ships were
  recomputing and re-logging their course correction up to ~125
  times/second in bursts, instead of only when their course actually
  changed. Real wasted CPU work, not just log noise.
- **Mail/PC terminal `DEL` command crash** — typing `DEL <name>` with no
  extension (`DEL DEL`, `DEL DIR`, `DEL VIEW`, `DEL NEWS`, ...) crashed the
  game, because the handler read the extension part of the argument past
  the end of what was actually typed. It now prints the game's own
  "cannot delete system file" message, the same as `DEL DEL.COM` always
  did. `DEL` never deletes anything, exactly as in the original game. The `DIR` listing also skips emptied entries, a harmless
  guard that has no visible effect while nothing can be deleted.
  (Versions 0.3.0–0.3.8 also let `DEL` delete some commands; that was a
  mistake, not original behavior, and was removed in 0.3.9.)
- **Co-op scenario "Escort: Make a Break" fails to load** — a one-character
  typo in a scenario file made it silently unloadable. (Mod-only fix, no
  exe patch needed.)
- **"CLASH between additions" log spam** — background NPCs' data files
  listed a hairstyle after a helmet in the same character-cosmetics
  list, so the (already-correctly-rejected) hairstyle logged a noisy
  error every boot. Purely a log fix — those items were never actually
  shown. (Mod-only fix, no exe patch needed.)
- **"unknown mesh" error for a specific beard style** — a one-field typo
  in a character-cosmetics data file shifted every value after it,
  breaking the mesh lookup for background NPCs wearing a particular
  beard. (Mod-only fix, no exe patch needed.)
- **"Unknown room" log spam cycling past a ship's last room** — the
  room-lookup function logged an error on every miss, even though the
  room-cycling code already correctly handles reaching the end of the
  list; mashing "next room" there just re-triggered the log every
  press.
- **Rare crash opening the PDA while a character's portrait is
  mid-render** — a race between two rendering operations in the
  game's engine could crash the game if the PDA/tablet was opened at
  the exact wrong instant. Fixed by ignoring the "open PDA" key press
  for that instant instead — press it again a moment later and it
  opens normally.
- **GRA 5 grappling arm installs broken and unsellable** — its data was
  missing 8 of 10 components whenever a shop rolled it in Stealth or
  Low Power Use condition. (Mod-only fix, no exe patch needed.)
- **6 LADAR modules show every component in the wrong repair-screen
  slot** (`MKX-LADAR-A-2`, `MKX-LADAR-A-T`, `MTL-C100`, `MTL-C150`,
  `MTL-CC`, `TBL-B42`) — a stray extra value in their configuration
  data shifted every real component one slot off from where it's
  actually declared. (Mod-only fix, no exe patch needed.)
- **`MKX-LADAR-A-2`/`MKX-LADAR-A-T` crash the game on equip** — their
  identifiers were exactly one character too long for a fixed-size
  network packet field; the resulting mangled identifier failed to
  resolve with no fallback. Fixed by shortening both ids. (Mod-only
  fix, no exe patch needed.)
- **Full Stop, while docked, lets you fly away for free** — triggering
  Full Stop while docked cleared the same internal field every other
  system checks to tell if a ship is docked, without the real Undock
  command ever running — so the ship could immediately start its
  reactor, plot a course, and leave with no undocking fee, no
  permission check, and no requirement to close the airlock first. The
  ship's actual docked-with relationship (used by everything else,
  including the real Undock command) is untouched by this fix.
- **A save (or hand-edited ship data) referencing a retired module
  identifier crashes the game on load** — including this same patch's
  own earlier LADAR identifier shortening, if an existing save still
  references a module by its old, longer id. Two independent bugs
  fixed together: a missing check let the crash happen at all, and a
  save-file read-position bug (already latent, just never triggered
  by anything reaching it) would have turned that crash into a hang
  instead if only the first were fixed. With both fixed, the ship
  loads normally with that one module slot left empty.
- **Commodities Trading Terminal shows a garbled error buying a
  shielded/temperature-controlled good with no pod space left** — the
  pod type name and the market-price note were being substituted into
  the wrong slots of the error message, so text like "radiation
  shielded" ended up jammed in front of "Error:" and the price note
  ended up stuck in the middle of "not enough ___ space in your hold."
  Now shows the intended, readable message.
- **"Quit to OS"/"Quit to Menu" never close the game while connected as
  a LAN client** — clicking either button from an active client session
  silently routed the command to the server instead of running it
  locally, so the server shut down cleanly while your own client sat
  frozen on the pause menu forever, needing a force-kill from Task
  Manager/Steam every time. Both commands now disconnect properly and
  close/return to the menu on the client itself, exactly like they
  already do in singleplayer.
- **Client crash dragging an installed addon between module slots in the
  engineering repair screen** — only shield and adapter components use
  the addon-slot mechanism this bug lives in, and both are content the
  developers themselves disabled — you can't normally obtain one through
  regular play, so most players will never encounter this. The drag's
  source slot index was never bounds-checked (only the destination was),
  so dragging one from its addon-icon slot could read 400+ bytes past the
  module's component array and crash on the garbage it found there. That
  specific addon-to-addon/addon-to-main move was never implemented for
  any slot in the first place, so this fix just rejects it cleanly
  (silently ignored, matching what already happens when the
  *destination* is an addon slot) instead of crashing. **This does not
  re-enable or restore shield components** — it only stops the crash if
  one is ever present.
- **Deleted email reappears in the PC terminal's mail app after
  quitting** — deleting an email and then quitting the mail app left a
  frozen copy of the whole email list on screen, with the email you just
  deleted back at the top. The terminal saves its existing text before
  showing the list and puts it back when you quit, but deleting an email
  redraws the list and was overwriting that saved text with the
  pre-delete list. Quitting now returns the terminal to exactly how it
  was before you opened the mail app.
- **Last key binding hidden in the Input Configuration list** —
  "Decrease Main Drive Power", the last entry in the key-binding list
  (both the PDA's and the main menu's), could never be scrolled into
  view; you could only bind it by clicking the blank space under the
  list. The list was counting its "Command | Key" header as one of its
  visible rows, so it always stopped scrolling one row short. Also
  removes a stray space in that entry's label that made it sit one
  character to the right of the others once it was visible.
- **Comms terminal "?" (help) and log buttons do nothing** — the Comms
  Download / Sync terminal is a square (192×192) screen, and the game only
  has help/log pages for 4:3 and 16:9 screens, so the buttons can never
  work there on any ship. The Enceladus and Proxima versions set
  `hasmenu=true`; that is now cleared so all three ships match (Ceres III
  never set it) and no dead help/log buttons are shown. (Mod-only fix, no
  exe patch needed.)
- **Docking in a stand-alone scenario overwrites save slot 1** - the game's
  save routine only checked that the scenario's mode was "full". Convoy Attack,
  Survival, Stealth, Escape, Defend, the quickstart and other stand-alone
  scenarios are also "full", so docking or jumping in any of them auto-saved over
  your campaign. Only the story scenario (whose description says it "auto-saves
  whenever you dock/undock or use a jumpgate") saves now. Side effect: statistics
  from other scenarios are no longer stored at those moments. (Exe patch, client only.)
- **Ship terminal shows power in "mw" and STATUS prints generation as drain** - the terminal's
  `STATUS`, `POWER` and ship-text lines say "mw" while the power screen and power bar show the same
  numbers in kW, so they are now "kw". The `STATUS` line "Current Power Drain" also printed the
  ship's *generation* (the code computed the drain, then discarded it); it now prints the drain,
  like the same line in the ship text does. (Exe patch, client.)
- **Intercom/forced conversations: Enter does nothing until you press an arrow key** - a conversation
  the game starts by itself selected option 0 even when that option is hidden by its requirements
  (Asterin Allas has two "Ok?" options, one for each state of `blr_knowsaboutleague`), so Enter was
  refused as an invalid option. It now selects the first valid option, as every other way of starting
  or advancing a conversation already does. (Exe patch, client.)
- **News list: Enter with nothing selected shows "Invalid article number: 747614849"** - the news
  list indexes its slot table without a range check (the e-mail list handles "nothing selected"),
  so slot -1 read the heap word in front of the table and printed it as the article number. Out-of-range
  slots are now ignored. (Exe patch, client. The missing selection marker on first opening is not
  fixed.)
- **Nav map: a jump drive above 100% efficiency shows sectors as out of range** - the "Dist." line of the
  selected sector is blue when the sector is within jump range and red when not, but it compared the distance
  with the drive class's base range. The real range (used by the Set Dest. button and the jump itself) is that
  range times the drive's efficiency, so a drive above 100% was shown red for sectors it can reach. The line now
  uses the real range. (Exe patch, client.)
- **Console tabs: the Weapons and Cargo tabs never showed damage** - on the Enceladus, Ceres (and the Proxima,
  which uses the Ceres screens) and Remora consoles, the Helm Control / Orbital tabs carry `linkto=helm`, which
  is what shows a module's damage static and offline state, but the Weapons tab (a commented-out
  `#linkto=weapon`) and the Cargo tab had no link. They now follow the helm like the other tabs of the console.
  Side effect: with the helm unpowered or destroyed those tabs are unavailable too. (Mod only.)
- **NPC-only modules are sold in shops** - the game's debug log shows the Remora's RCS ("AP-RCS1", basevalue
  2505) and the "Probe Sensor" (basevalue 1872) in station stock: the shop stock generator picks any module
  class with a `basevalue` of at least 1, and these two had one while the rest of `modules_npc.txt` (and the
  Remora sensor, 0) did not. Set to 0 so they are not sold; the Remora and probes keep using them. (Mod only.)
- **Infopedia list: the last row is cut in half** - the article list is 238 (4:3) / 268 (16:9)
  units tall but its rows are 8 units high and start 2 units down, so the next entry's top edge showed
  under the last full row. The list is trimmed to a whole number of rows plus a unit of margin (235 / 259). (Mod only, no exe patch.)
- **Autopilot keeps burning the main drive at top speed, draining the batteries** - in the "accelerate to the
  final waypoint" state the drive is switched off when `top speed <= speed`. The speed is capped by rescaling the
  velocity vector to exactly the top speed, but the rescaled vector's length is a float that comes out a hair
  under the cap about every other tick, so the test fails and the drive keeps burning at the cap. A GX Delta at
  100% draws 14 kW/s, so a long cruise empties the batteries, and a ship with no power left cannot brake for
  its destination. The other autopilot state that does this test already allows 1e-5; this one now does too.
  (Exe patch, client and server; applies to NPC ships as well.)
- **Autopilot: after overshooting its destination a ship burns away from it** - when the autopilot
  brakes for its last waypoint it faces (angle to the waypoint + 180 degrees) and burns while the stopping
  distance is at least the distance left. That is a retro burn only while the ship is still heading for
  the waypoint. A fast engine (the GX Delta at 100% power) can fly past it; the angle to the waypoint then
  flips, the same heading points along the ship's velocity, and the "brake" burn accelerates the ship away,
  draining the batteries until the turn-back test fires (a debug log of a failed docking shows the
  "Overshot our mark" message, then no braking for over a minute). The heading now uses the dot product of
  the velocity and the vector to the waypoint: moving away from it, the ship faces it and burns; otherwise
  the heading is the stock one. The cause of the overshoot itself (the braking margin adds a turn time in
  seconds to distances) is not changed, so a fast ship can still overshoot, but it now brakes instead
  of running away. Applies to NPC ships on the server as well. (Exe patch, client and server;
  `tools/autopilot/`.)
- **Point-defence panel: a long manufacturer + name wraps and overlaps the buttons** - the panel's
  first line is "manufacturer name" and the panel is about 16 columns wide, so something like
  "Pritchard PSL 10X" wrapped to a second line and pushed the State/Range/CD lines into the
  ENABLE button. When the two do not fit on one line the name alone is printed (here "PSL 10X").
  The 16-column limit is inferred from a screenshot, not measured. (Exe patch, client.)
- **The point-defence laser can never destroy a torpedo** - the Infopedia says
  point-defence lasers "rapidly shoot laser blasts at nearby torpedoes when they are close
  enough to your ship", but the PDS "hits" through the same damage routine ships use, and
  that routine does nothing for torpedoes, probes and mines, so a locked torpedo was never
  harmed. It also took the first candidate in the sector's list, so a torpedo behind any ship
  with its IFF off was never reached, and it would have counted your own torpedoes as targets
  once they could be hurt. Now it looks for weapons first (never your own, never one already
  destroyed), a locked weapon is destroyed (no warhead blast), and ships are chosen by the
  unchanged stock rule (only ships with their IFF off). The module's own hit roll
  (`hitchance`, 1d6 on the PDL 101) still applies. (Exe patch, client and server;
  `tools/pds/`, client-only emulation test.)
- **Power drain: the numbers disagree, and the components' power modifiers never
  applied to the real drain** - every component has a `powermodifier` (extra power
  use, in percent) and the game shows it on the module screens, the module tooltips,
  the terminal's `POWER DRAIN` list and the "Actual" lines of the Power Management
  page ("Theoretical" is the unmodified figure). But the power actually taken from the
  batteries ignored it, and so did the "Drain" figure at the top of that page and the
  power bar, which also counted an active module's idle drain on top of its active drain
  (the batteries only ever lose the active drain, as the module screens say). Now the
  "Drain" total is the sum of what each module says it draws (off = 0, idle = idle drain,
  active = active drain x setting, all x (1 + modifier)), and the batteries lose exactly
  that. **This makes the batteries drain faster on ships whose components carry a power
  modifier**, by the amount the game already showed as "Actual". The "Drain (Normal)" and
  "Drain (High)" lines remain "everything idle" / "everything active" figures, so they still
  differ from the total in EMCON mode. (Exe patch, client and server; `tools/power/`.)
- **A torpedo whose target dies picks the nearest thing instead** - when the
  ship a torpedo is homing on is destroyed or removed (for example by another
  torpedo), the game clears the torpedo's target, and the torpedo's homing code
  treats "no target" as "go and find one": it locks onto the nearest sensor
  contact, which can be a station, another weapon or your own ship. Now a torpedo
  that loses its target this way does not look for a new one and stops steering and
  thrusting, so it drifts on. You can still re-target it from the weapon terminal (by
  target or by a position) and it homes again. A torpedo fired without any target
  still behaves as before, and the proximity fuse still works, so a drifting torpedo can
  still go off if something flies close to it. (Exe patch, client and server.)
- **Spelling and grammar in the game's text** — about 450 corrections
  across roughly 320 text files (news articles, dialogue, emails, info
  pages): misspellings such as "manouvres", "scavanging", "tarrifs" and
  "priviliges", a few place names against their on-map spelling, and
  unambiguous grammar slips such as "I'll back back very shortly" and "it's
  importance". One is a real bug: a misspelled `$amonut` substitution token
  in `passengers.txt` made an email show the literal text "$amonut". Dialect,
  deliberately garbled messages and invented names are left alone, and no
  person-name spellings are changed. (No exe patch needed. Most of it goes
  in the mod; the `news_*`/`info_*` articles are corrected in place in
  `assets/` with the originals kept, because the game's mod system can't
  override those. Review notes: `tools/textcheck/REPORT.md`.)
- **Buying a module never sends its welcome email** — every module's data
  file has an `email=` text ("Congratulations on purchasing your Kruger
  Interstellar DRAK Grappling Arm! ..."; 71 of them), and the game loads it,
  but no code ever reads it, so buying a module at Mechanixx never delivers
  it. The purchase now queues that email through the game's own custom-email
  call (the one used for passenger and smuggler-reward mail), so it arrives
  on your next comms sync like those do. It is addressed from the module's
  own manufacturer with the subject "Your new <module name>", and modules
  with no email text are skipped. Most categories shared one email text
  across every model, so the first sentence of those 56 (countermeasures,
  hacking, jump drives, point defence, solar wings, weapons) now says which
  maker and model it is about, the way the grapple-arm and battery emails
  already did. Only the buying path is covered: modules a ship starts with
  or gets from a broker still send nothing. Not confirmed in the running
  game; I could only test the generated code in a CPU emulator.
- **Scroll wheel can't zoom back out of cabin close-ups** — clicking the
  posters in the Ceres Mk III cabin (or the desk PC in the Enceladus
  cabin, or the Proxima's equivalent) zooms the camera in, but scrolling
  up didn't zoom back out like it does everywhere else — only right-click
  or Escape worked. These are the only close-ups in the game that don't
  focus a screen, and the scroll wheel only knew how to back out of
  screens. It now backs out of these too, the same way Escape does.
- **Crash clicking a monitor right after your ship is destroyed** — when
  your ship's Primary Hull was destroyed, clicking a monitor (or backing
  out of one) in the moments before the game-over sequence could crash the
  game. The code that hands the new screen to the warning display reached
  it through your ship, which no longer exists by then. It now checks first
  and skips that step, as the other places doing the same thing already
  did.
- **"Docking" and "stationary" drawn on top of each other** on the ship
  status screen — the status line is several labels stacked in one place,
  and the "stationary" label (speed is zero) didn't step aside while you
  were docking, so both could show at once as garbled text. It now does.
- **Station sounds inaudible depending on where you've been** — the game
  only plays sounds tied to a ship if that ship is the one it's
  "listening" to, but station terminals tie their sounds to different
  ships: terminal button beeps to your own ship, typing clicks to the
  station you're standing on. So which sounds you heard depended on
  whether you'd loaded your save at the station or walked over from your
  ship (on the Admin Terminal, typing clicks and the [change details]
  beep swapped). Now both kinds play, every time, on every terminal.
- **Enceladus airlock buttons respond slightly below where they're drawn**
  — the invisible click areas for the Inner and Outer airlock door buttons
  sat 1–2 units low, so pointing at the top of the lower button picked the
  upper one. Moved up to line up with the buttons. (Mod-only fix, no exe
  patch needed.)
- **Enceladus "Undock" button out of place on the Dock Con screen** — a
  one-number typo put it noticeably left of every other ship's Undock
  button and out of line with the JUMP button above it. Moved back.
  (Mod-only fix, no exe patch needed.)

## Optional variant: a point-defence system that works (`--pds-everything`)

This is **not a bug fix and is off by default.** It changes gameplay balance, so
it is a separate opt-in rather than part of the standard patch.

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

## Optional variant: civilians who give in (`--civilians-comply`)

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

## Limitations

Only tested against the **Windows Steam** build of `ois.exe` and
`ois_server.exe` (game version 1.0.8, the last Steam release before the
developers stopped supporting it). Every patch site checks its exact
bytes before changing anything and skips itself with a warning rather
than guessing, so running this against a different build should fail
safely rather than corrupt anything — but it hasn't been verified
against GOG, other storefronts, other game versions, or non-Windows
builds, if any exist. Auto-detection can *locate* a GOG install, but the
binary fixes themselves are only confirmed against the Steam 1.0.8
build either way — the same "check first, skip safely if it doesn't
match" behavior applies regardless of where the exe came from.

## Limitation of liability

This patch is provided "as is," with no warranty of any kind, express
or implied — including, without limitation, any warranty of fitness for
a particular purpose or merchantability. You run it entirely at your
own risk. The author is not liable for any damages or losses arising
from its use, including but not limited to save-file corruption, lost
progress, an unstable or unlaunchable game install, or any other issue
with your game or system. Modifying game files may also violate the
terms of service of the platform you purchased the game through —
checking that is on you. A backup of your original `ois.exe` and
`ois_server.exe` is made automatically, but you're responsible for
keeping it, and for your own save backups, before running this.

## License

[CC BY-NC 4.0](LICENSE) — free to use, share, and adapt for
non-commercial purposes, as long as you credit the original author
(Leeway). See [LICENSE](LICENSE) for the full terms.

## Version history

### 0.4.0 - 2026-10-03

- **New fixes:** nav map distance colour uses the real jump range (exe, client); console Weapons/Cargo tabs show the helm's damage (Enceladus, Ceres/Proxima, Remora); the Remora RCS is no longer sold in shops (mod).
- **New fix (exe, client and server):** the autopilot no longer burns away from its destination after overshooting it.
- **New fix (mod):** the Infopedia article list no longer shows half a row at the bottom.
- **New fix (exe, client):** a long point-defence name no longer wraps over the panel's buttons.
- **New fixes (exe, client):** terminal power units mw -> kw and `STATUS` printing generation as drain; forced/intercom conversations select the first valid option; news-list Enter with nothing selected no longer prints a garbage article number.
- **New fix:** the point-defence laser can now destroy torpedoes, as the Infopedia says it does (exe, client and server). It still only shoots ships with their IFF off.
- **New fix:** the power drain shown on the Power screen and the power really taken from the batteries now agree: component power modifiers are applied to both, and active modules are no longer counted at idle + active (exe, client and server). Batteries drain faster on ships whose components have a power modifier.
- **New fix:** a torpedo whose target is destroyed before impact no longer re-targets the nearest contact (a station, another weapon or you); it drifts, and can be re-targeted by hand (exe, client and server).
- **New fix:** docking or jumping in a stand-alone (non-story) scenario no longer auto-saves over save slot 1. Only the story scenario saves (exe).
- **New optional variant, off by default:** `--civilians-comply` makes civilians give in to a cargo demand far more readily (chance by captain style 100/90/60/15 % -> 100/90/70/35 %), counts your own torpedo still in flight as a credible threat, and no longer locks you out of hailing a civilian after one demand. See "Optional variant: civilians who give in" above.
- **New optional variant, off by default:** `--pds-everything` makes the point-defence system shoot torpedoes, probes, decoys and ships with their IFF off (never ships with IFF on), and actually destroy torpedoes (the stock PDS can select a torpedo but its shot has no effect on one). See "Optional variant" above for what it does and does not shoot.
- **New fix (Fix 22):** module purchase emails were never sent. Buying a
  module from Mechanixx now queues its welcome email for your next comms
  sync, and the shared category emails name their own maker and model
  (e.g. "Kruger Interstellar DRAK Grappling Arm" instead of a generic
  one) (exe + mod).
- **New fix:** about 435 spelling and grammar corrections across roughly 320 text files, including a misspelled `$amount` token that showed the player "$amonut". The game can't mod `news_*`/`info_*` files, so those 179 articles are corrected in place in `assets/`, with originals saved in `oisbugfix_original_assets/` (restored by `--uninstall`). Three lines flagged in review as intentional (a character's "wordhole", a repeated "Than the …?" construction, "it striked me" slang) are left as written.
- **Fixed a regression:** the mail-terminal `DEL` command could delete
  commands. The original game never let you; it now only refuses, as
  before, and no longer crashes on a name with no extension (`DEL DEL`,
  `DEL DIR`, `DEL VIEW`).
- **New fix:** Comms Download / Sync terminal no longer shows dead help
  and log buttons on the Enceladus and Proxima (mod).

### 0.3.9 - 2026-10-03

- **Fixed a sound regression from 0.3.8:** station terminal beeps
  (docking computer, commodities, contracts and other terminals) stopped
  playing correctly. 0.3.8's fix for the Admin Terminal sounds (GitHub
  issue #21) changed which ship the game listens to for sounds while
  you're on a station, but nearly every terminal's beeps are tied to your
  own ship, so they went quiet. That change is gone; instead the game now
  plays a ship's sounds if they belong to the ship it's listening to,
  your own ship, or the vessel you're standing on. Typing clicks, the
  [change details] beep, and every other terminal's beeps now all play
  correctly. If you're on 0.3.8, re-run the patcher to upgrade.

### 0.3.8 - 2026-10-01

- **New fix: crash clicking a monitor right after your ship is destroyed**
  (GitHub issue #22).
- **New fix: "docking" and "stationary" overlapping on the ship status
  screen** (GitHub issue #23).
- **New fix: station sounds going wrong after visiting your own ship.** On
  the Admin Terminal, typing clicks and the [change details] beep now both
  play correctly, whether or not you've been back to your ship (GitHub
  issue #21).
- **New fix: Enceladus airlock door buttons responding below where they're
  drawn** (GitHub issue #25).
- **New fix: Enceladus Dock Con "Undock" button out of place** (GitHub
  issue #26).

### 0.3.7 - 2026-09-26

- **New fix: deleted email reappears after quitting the mail app.** Quitting
  the PC terminal's mail app right after deleting an email no longer leaves
  a frozen copy of the list (with the deleted email back in it) on screen;
  the terminal goes back to exactly how it was before you opened mail.
- **New fix: last key binding hidden in the Input Configuration list**
  (GitHub issue #27). "Decrease Main Drive Power" now scrolls into view in
  both the PDA and main-menu key-binding lists, and its label lines up
  with the others.
- **New fix: scroll wheel can't zoom back out of cabin close-ups** (GitHub
  issue #24). Scrolling up now zooms back out after clicking the posters in
  the Ceres Mk III cabin, the desk PC in the Enceladus cabin, or the
  Proxima's cabin equivalent.

### 0.3.6 - 2026-09-24

- **New fix: garbled trading-terminal error for shielded/temperature-
  controlled goods.** Buying a good that needs a special cargo pod (e.g.
  Radioactive Waste) with not enough free pod space used to show a
  scrambled message with the pod type name and a price note mashed into
  the wrong places. Now shows the intended, readable error.
- **New fix: "Quit to OS"/"Quit to Menu" never closing the game as a LAN
  client.** Both buttons now actually disconnect and close/return to the
  menu on the client, instead of silently doing nothing and leaving you
  to force-kill the process every time.
- **New fix: crash dragging an installed addon between module slots** in
  the engineering repair screen. Only affects shield/adapter components
  (content the developers already disabled, so most players will never
  hit this) — that move was never implemented for any slot, so it's now
  cleanly rejected instead of crashing. Doesn't re-enable shields.

### 0.3.5 - 2026-09-12

- **New fix: Full Stop docked-state exploit.** Triggering Full Stop
  while docked no longer lets the ship fly away for free — the write
  that made every other system think the ship had undocked is now
  skipped while it's still genuinely docked.
- **New fix: save-load crash/hang on a retired module identifier.** A
  save (or hand-edited ship data) referencing a module id that no
  longer resolves — including this patch's own earlier LADAR id
  shortening — now loads normally with that module slot left empty,
  instead of crashing or, with only half the underlying bug fixed,
  hanging instead.

### 0.3.4 - 2026-09-02

- **No path required.** Running `python ois_patcher.py` with no
  arguments now auto-detects your Steam (and, best-effort, GOG)
  install, asking if it finds more than one or none at all. Explicit
  paths, `--game-dir`, and `OIS_TARGET_DIR` still work as before.
- **Added `--uninstall`**, which restores both exes from their backups
  and removes the `oisbugfix` mod folder in one step, after confirming.
  `--yes` skips confirmation; `--keep-backups` keeps the backup files.
- **Added `--status`**, reporting what's currently installed (patch
  state, backup availability, mod status) without changing anything.
- **Updating is now automatic.** Re-running the patcher against an
  older-patched install restores the original and re-applies current
  fixes; an up-to-date install just gets its mod refreshed. Running an
  older patcher against a newer-patched install is refused unless you
  pass `--force`.
- **Added a self-update check** for `git clone` setups: a normal run
  checks for a newer patcher upstream and offers to pull it before
  touching your game. Skipped automatically for a downloaded zip or
  without `git`. `--update` accepts without asking; `--no-update-check`
  skips it.
- **More reliable failure handling.** Corrupted exes are reported
  cleanly instead of crashing, a broken `ois_server.exe` no longer
  blocks patching `ois.exe`, the mod install degrades to a warning
  instead of failing outright, and file writability is checked before
  any changes are made.

( credit to Voidless7125 for this amazing usability update! )

### 0.3.3 - 2026-09-01

- Fixed the GRA 5 grappling arm installing non-functional and unsellable when bought in Stealth or Low Power Use condition — its data was missing 8 of 10 components in those two states (issue #7).
- Fixed 6 LADAR modules (`MKX-LADAR-A-2`, `MKX-LADAR-A-T`, `MTL-C100`, `MTL-C150`, `MTL-CC`, `TBL-B42`) installing with every component shown in the wrong slot in the repair screen, due to a stray extra value in their data.
- Fixed `MKX-LADAR-A-2` and `MKX-LADAR-A-T` crashing the game outright when equipped — their identifiers were exactly one character too long for a fixed network-packet field, and the game didn't handle the resulting failed lookup gracefully.

(credit to Voidless7125 for bringing these issues to my attention)

### 0.3.2 - 2026-08-31

- Quick fix for versioning on the mod.

(credit to Voidless7125 for creating the fix for this)

### 0.3.1 — 2026-08-30

- Fixed a second Pirate Hunt crash cause on **both** `ois.exe` and `ois_server.exe`: a log call formatting a "duplicate ship-sets" message was missing an argument for its own format string, crashing with the same signature as the spawn-selection bug above. Found while live-testing 0.3.0's server fix — it correctly stopped the first crash, but a Pirate Hunt session could still hit this second, independent one a few lines later in the same code path.

### 0.3.0 — 2026-08-30

- Also patches `ois_server.exe`, the co-op server binary that ships
  alongside `ois.exe`: the same Pirate Hunt spawn-selection crash fixed
  on the client also exists in the server binary. Singleplayer never
  runs `ois_server.exe`, so this only matters for hosting or joining a
  co-op game — but it's a hard crash there every time, reported and
  confirmed by a co-op host after 0.2.0 shipped.

(credit to Voidless7125 for bringing this to my attention)

### 0.2.0 — 2026-08-30

- "unknown mesh" error for a specific beard style (mod)
- "Unknown room" log spam cycling past a ship's last room
- Rare crash opening the PDA while a character's portrait is mid-render

### 0.1.0 — 2026-08-28

First packaged release.

- Pirate Hunt scenario crash (client-side)
- Music player permanent failure loop
- Ship steering recompute spam (three independent causes)
- Mail/PC terminal `DEL` command crash + delete-a-command feature
- Co-op scenario "Escort: Make a Break" load failure (mod)
- "CLASH between additions" log spam (mod)
