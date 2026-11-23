"""GOG build support for ois_patcher.py.

The GOG build of ois.exe (PE timestamp 1557139745, 2,657,792 bytes) is the same game code as the Steam build, compiled
separately: most functions sit a few bytes to a few KB away from where the Steam build has them, and the .rdata/.data
globals and the import table moved too. ois_patcher.py hardcodes the Steam addresses, so on GOG most client fixes refuse to
apply ("byte mismatch").  (The GOG ois_server.exe is byte-for-byte the Steam one, so the server fixes need nothing.)

This module is what makes the GOG build work.  It was contributed in Issue #64 (a Claude-assisted port, reviewed and run on a
GOG install by the reporter) and adapted here.  How it works:

  * The build is recognised from ois.exe itself (the PE TimeDateStamp), not from which files sit in the folder.
  * For the GOG client exe only, each ported fix_* function is re-run with every Steam address in its source replaced by the
    GOG one (MAP below; an AST rewrite of the function's own source).  Every site is still byte-checked before anything is
    written, with the expected bytes translated the same way, so a wrong table entry makes a fix skip, never corrupt.
  * Fixes added after the port was made (UNPORTED) are skipped on GOG, with a message, until their GOG addresses are in MAP.
    A skipped fix is always safe; applying one at a Steam address in a different build is not.
  * Steam installs and the server exe never go through any of this.

Status: MAP covers the 34 client fixes of release 0.4.1 (the 25 in PORTED, plus 9 whose code happens to sit at the same
addresses in both builds).  tools/gog/test_gog_port.py checks the table against the current source.  The reporter ran the
port on a GOG install ("Applied 34 exe fix(es), skipped 0"); the least certain entry is ShipData::currentlyBoardedShip
(Steam 0x65D50C -> GOG 0x65C3D4), inferred from the same data shift as its neighbours.  The newer fixes cannot be added
without a GOG ois.exe to read the addresses from.
"""
import ast
import inspect
import struct
import textwrap

GOG_TIMESTAMP = 1557139745

# Steam VA -> GOG VA. Each entry was located in the GOG exe and checked by disassembly (same instructions, same branch
# targets, same callers).
MAP = {
    # Pirate Hunt crash guard
    0x408c17: 0x408b07, 0x408c1d: 0x408b0d, 0x408ca3: 0x408b93,
    0x5e45f0: 0x5e3498,   # "Invalid ship tried to spawn."
    0x5cfcfc: 0x5cec44,   # log category string
    0x592da0: 0x591e60,   # logging function
    # Pirate Hunt #2 format string
    0x5e4620: 0x5e34c8,
    # Music player FMOD leak
    0x559fb0: 0x5590d0, 0x559fb6: 0x5590d6,
    0x5cf2dc: 0x5ce2e8,   # IAT: FMOD::Sound::release
    # Burn-vector #1 (code at identical addresses, only an IAT slot moved)
    0x506d2a: 0x506d2a, 0x506d35: 0x506d35, 0x506d44: 0x506d44, 0x506d67: 0x506d67,
    0x5cf4a4: 0x5ce480,   # IAT slot used inside the verified bytes
    # "Unknown room" log spam
    0x55a79d: 0x5598bd, 0x55a7b9: 0x5598d9,
    0x625fc8: 0x624af8,   # "Unknown room" format string (inside verified bytes)
    # PDA-open crash guard
    0x537cb0: 0x536dd0, 0x537cb5: 0x536dd5,
    0x538658: 0x537778, 0x538662: 0x537782,
    0x530b90: 0x52fcc0, 0x530b97: 0x52fcc7,
    # Mail terminal DEL
    0x548f34: 0x548064, 0x548f3a: 0x54806a, 0x548ff5: 0x548125,
    0x5490ae: 0x5481de, 0x5490b4: 0x5481e4, 0x54910c: 0x54823c,
    0x548530: 0x547660, 0x548535: 0x547665, 0x54859a: 0x5476ca,
    # Save-load with unresolvable module id
    0x4bf657: 0x4bf627, 0x4bf65c: 0x4bf62c, 0x4bf67d: 0x4bf64d,
    0x4c07ee: 0x4c07be, 0x4c0a0e: 0x4c09de,
    0x5cf288: 0x5ce288,   # IAT: fread
    # Trading terminal error args
    0x48a50f: 0x48a50f, 0x48a517: 0x48a517, 0x48a578: 0x48a578, 0x48a583: 0x48a583,
    0x5dfa98: 0x5de9e0,   # pod-type name table
    # Quit while LAN client
    0x5461bc: 0x5452dc, 0x5461c5: 0x5452e5, 0x5461d4: 0x5452f4, 0x54620e: 0x54532e,
    0x402550: 0x4024b0,   # NetworkClient::getInstance
    0x41b170: 0x41b190,   # NetworkClient::disconnectFromServer
    0x65e400: 0x65d2c8,   # singleton cache global
    # Addon drag crash
    0x4e103b: 0x4e100b, 0x4e1041: 0x4e1011, 0x4e1144: 0x4e1114,
    # Last key binding hidden
    0x58a6a3: 0x589763, 0x58a6b5: 0x589775, 0x58b2fc: 0x58a3bc, 0x58ac53: 0x589d13, 0x58b308: 0x58a3c8,
    # "Decrease Main Drive Power" label
    0x620ba4: 0x61f790,
    # Module purchase emails
    0x495ad8: 0x495ad8, 0x495add: 0x495add,
    0x402720: 0x402620,   # std::string copy constructor
    0x593b30: 0x592bf0,   # strUsingArgs
    0x4129d0: 0x4128c0,   # EmailManager::getInstance
    0x43acb0: 0x43acb0,   # EmailManager::addCustomEmail
    0x5b5018: 0x5b40c8,   # its SEH handler (inside verified bytes)
    # Scroll wheel zoom-out
    0x53220f: 0x53133f, 0x532257: 0x531387, 0x532266: 0x531396,
    0x537050: 0x536170,   # Room::getObjectClickedOn
    # Monitor click after ship destroyed
    0x532987: 0x531ab7, 0x532a45: 0x531b75, 0x532a67: 0x531b97, 0x532a7f: 0x531baf,
    0x528e60: 0x527fb0,   # LogSystem::renderWarning
    0x65d704: 0x65c5cc,   # g_gameData
    # "Docking"/"stationary" overlap
    0x4cf671: 0x4cf641, 0x4cf68a: 0x4cf65a, 0x4cf6a0: 0x4cf670,
    # Station sounds
    0x559d20: 0x558e40, 0x559d28: 0x558e48, 0x559d41: 0x558e61,
    0x65d50c: 0x65c3d4,   # "player is boarded" flag global
    # Scenario autosave
    0x4b8789: 0x4b8789,
    0x6119f4: 0x6108c8,   # string pushed on the not-saving path (inside verified bytes)
    # Power drain
    0x5246b0: 0x523800, 0x4ae2f0: 0x4ae2f0, 0x4ae260: 0x4ae260, 0x438200: 0x438200,
    0x523520: 0x522660,   # SystemManager::drawPower (both CALLs in drainPower target it)
    # Terminal power units
    0x54b361: 0x54a491, 0x524720: 0x523870,
    # News list
    0x4b5877: 0x4b5877, 0x4b587c: 0x4b587c,
    # PDS panel name overflow
    0x4f630b: 0x4f630b, 0x4f631e: 0x4f631e,
    # Nav map jump range
    0x583012: 0x5820f2, 0x583021: 0x582101, 0x583023: 0x582103, 0x4ae800: 0x4ae800,
    # Station -> ship crash
    0x52ef66: 0x52e096, 0x52ef6c: 0x52e09c, 0x52ef7a: 0x52e0aa,
    0x52f193: 0x52e2c3, 0x52e1f0: 0x52d320,
    0x536bba: 0x535cda, 0x536e5e: 0x535f7e, 0x536e6a: 0x535f8a,
    0x557320: 0x556440,   # ScreenInterface::update
}

PORTED = [
    "fix_pirate_hunt", "fix_pirate_hunt_format_string", "fix_music_leak",
    "fix_burnvector_strict_compare", "fix_unknown_room_spam", "fix_pda_render_guard",
    "fix_del_command", "fix_readshipmodule_unresolvable_identifier", "fix_trade_pod_error_args",
    "fix_quit_networked_disconnect", "fix_addon_move_oob", "fix_sheet_last_row",
    "fix_decrease_drive_label", "fix_module_purchase_email", "fix_scroll_back_cameraclick",
    "fix_movecamera_null_ship", "fix_stationary_while_docking", "fix_ship_sound_listener",
    "fix_scenario_autosave", "fix_power_drain_modifier", "fix_terminal_power_units",
    "fix_news_enter_without_selection", "fix_pds_panel_name_overflow",
    "fix_nav_jump_range_efficiency", "fix_station_to_ship_crash",
]

# Client fixes that need no table: their code and data sit at the same addresses in both builds (they applied on GOG before
# the port existed).
NATIVE = ["fix_burnvector_travelstate", "fix_burnvector_singularity", "fix_allstop_docked_writeguard",
          "fix_showlist_backup_clobber", "fix_pds_torpedoes", "fix_forced_conversation_first_option",
          "fix_autopilot_overshoot", "fix_autopilot_cruise_burn", "fix_behaviour_uninitialised_stealth"]

# Client fixes added after the port was made. Their Steam addresses are not known to be right for GOG, so on GOG they are
# skipped (label shown in the summary) instead of being applied blind.
UNPORTED = {
    "fix_pds_hit_chance_label": "Point-defence 'Hit Chce' shows the real chance",
    "fix_autopilot_overshoot_stop": "Autopilot: no endless burn at the last second of an approach",
    "fix_module_id_alias": "Saves with a LADAR open after the LADAR id rename",
    "fix_weapon_spinup": "Weapon spin-up time grows as efficiency drops",
    "fix_shop_stat_labels": "Shop labels: Detect Rng, Use Time",
    "fix_jump_range_rating": "Shop: jump-drive Range rating",
    "fix_solar_range_rating": "Shop: solar-wing Range rating",
    "fix_sensor_ratings": "Shop: sensor page ratings and software version",
    "fix_resolution_list_duplicates": "Options: one resolution entry per size",
    "fix_mail_select_out_of_range": "Mail terminal: opening a missing email no longer crashes",
    "fix_config_blank_line_log": "Config load: no log line for the trailing empty line",
    "fix_eng_move_empty_slot": "Repair screen: no crash dropping a component on an empty slot",
}

LO, HI = 0x401000, 0x700000
REVERSE = {v: k for k, v in MAP.items()}
SERVER_ONLY_OK = {0x522BE0, 0x4AE1B0, 0x4AE120, 0x438020, 0x521A50}  # server branch of power drain


def is_gog_client(pe):
    return pe.FILE_HEADER.TimeDateStamp == GOG_TIMESTAMP


def translate_bytes(b, at_va=None, gog_va=None):
    """Rewrites a Steam byte string for GOG: absolute addresses found in MAP are replaced, and (when the position is known)
    rel32 CALL/JMP operands whose Steam target is in MAP are recomputed for the GOG position."""
    b = bytearray(b)
    i = 0
    while i < len(b):
        if at_va is not None and b[i] in (0xE8, 0xE9) and i + 5 <= len(b):
            tgt = at_va + i + 5 + struct.unpack_from("<i", b, i + 1)[0]
            if tgt in MAP:
                struct.pack_into("<i", b, i + 1, MAP[tgt] - (gog_va + i + 5))
                i += 5
                continue
        if i + 4 <= len(b):
            v = struct.unpack_from("<I", b, i)[0]
            if v in MAP and v != MAP[v]:
                struct.pack_into("<I", b, i, MAP[v])
                i += 4
                continue
        i += 1
    return bytes(b)


class _Translate(ast.NodeTransformer):
    def __init__(self):
        self.unknown = set()

    def visit_Constant(self, node):
        v = node.value
        if type(v) is int and LO <= v < HI:
            if v in MAP:
                return ast.copy_location(ast.Constant(MAP[v]), node)
            self.unknown.add(v)
        return node

    def visit_Call(self, node):
        self.generic_visit(node)
        f = node.func
        if isinstance(f, ast.Name) and f.id == "verify_site":
            node.func = ast.copy_location(ast.Name("_gog_verify_site", ast.Load()), f)
        # bytes.fromhex("...") literals that embed absolute addresses
        if isinstance(f, ast.Attribute) and f.attr == "fromhex" and node.args and isinstance(node.args[0], ast.Constant):
            s = node.args[0].value.replace(" ", "")
            t = translate_bytes(bytes.fromhex(s)).hex().upper()
            if t != s.upper():
                node.args[0] = ast.Constant(t)
        return node


def build_ported(P, names=None):
    """{name: GOG version of P.<name>} for every fix that could be translated; {name: reason} for the ones that could not."""
    ported, failed = {}, {}
    for name in (names or PORTED):
        try:
            orig = getattr(P, name)
            tree = ast.parse(textwrap.dedent(inspect.getsource(orig)))
            tr = _Translate()
            tree = tr.visit(tree)
            # bytes([0x.., ...]) lists: translate embedded absolute addresses
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "bytes" \
                        and node.args and isinstance(node.args[0], ast.List) \
                        and all(isinstance(e, ast.Constant) and type(e.value) is int for e in node.args[0].elts):
                    raw = bytes(e.value for e in node.args[0].elts)
                    new = translate_bytes(raw)
                    if new != raw:
                        node.args[0].elts = [ast.Constant(x) for x in new]
            leftover = tr.unknown - SERVER_ONLY_OK
            if leftover:
                raise RuntimeError(f"no GOG address for {sorted(hex(x) for x in leftover)}")
            ast.fix_missing_locations(tree)
            ns = P.__dict__
            exec(compile(tree, f"<gog:{name}>", "exec"), ns)
            ported[name] = ns[name]
            setattr(P, name, orig)  # exec rebound the name; restore it, dispatch happens in the wrappers
        except Exception as e:       # a fix that changed since the table was made: skip it on GOG, don't take the patch down
            failed[name] = str(e)
            setattr(P, name, orig)
    return ported, failed


def install(P):
    """Makes the fix_* functions of module P build-aware. Call once, before the fixes run, for a GOG ois.exe."""
    def _gog_verify_site(data, pe, va, expected, label):
        # `va` is already a GOG address (translated in the source); recover the Steam address only to recompute
        # relative operands in `expected`.
        steam_va = REVERSE.get(va)
        exp = translate_bytes(expected, steam_va, va) if steam_va is not None else translate_bytes(expected)
        return P.verify_site(data, pe, va, exp, label)
    P._gog_verify_site = _gog_verify_site

    ported, failed = build_ported(P)

    def skipper(name, label):
        orig = getattr(P, name)

        def wrapper(data, pe, *a, **kw):
            if kw.get("server") or not is_gog_client(pe):
                return orig(data, pe, *a, **kw)
            print(f"  [SKIP] {label}: not available for the GOG build of ois.exe yet")
            P.FIXES_SKIPPED.append(f"{label} (GOG build: not ported yet)")
            return a[2] if len(a) >= 3 else None
        wrapper.__name__ = name
        setattr(P, name, wrapper)

    for name, gog_fn in ported.items():
        orig = getattr(P, name)

        def wrapper(data, pe, *a, _orig=orig, _gog=gog_fn, **kw):
            gog = (not kw.get("server")) and is_gog_client(pe)
            return (_gog if gog else _orig)(data, pe, *a, **kw)
        wrapper.__name__ = name
        setattr(P, name, wrapper)
    for name, why in failed.items():
        skipper(name, f"{name} ({why})")
    for name, label in UNPORTED.items():
        if hasattr(P, name):
            skipper(name, label)
    return ported, failed
