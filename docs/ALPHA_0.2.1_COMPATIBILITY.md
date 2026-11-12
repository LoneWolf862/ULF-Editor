# Alpha 0.2.1 Valheim 1.0.21 compatibility

**Date** 2026-11-12

**Status** READY FOR OWNER TESTING on `fix/alpha-0.2.1-valheim-1.0.21`. The local sample passed exact round-trip and disposable-copy export checks. In-game acceptance remains open.

## Format evidence

The local Steam manifest and installed managed assembly identify Valheim 1.0.21, Steam build 26249040. The SHA-256 of `assembly_valheim.dll` is `9f959c0396ec4240d47fcbe5d0d062c428cc627244506db5ea567f9d77b2b769`. Static inspection used dnfile 0.18.0 and dncil 1.0.2 outside the application. The real save was read locally and only aggregate diagnostics are recorded below. [Iron Gate patch notes](https://www.valheim.com/news/patch-1-0-21/), [prior installed-build research](ITEM_STAT_SCALING.md).

| Component | Existing ULF support | Current combination | Evidence and decision |
|---|---|---|---|
| Outer framing | Int32 body length, body, int32 hash length, SHA-512 | Same | `PlayerProfile.LoadPlayerDataFromDisk`, `SavePlayerToDisk`, and the actual file. ULF validates length, complete framing and checksum before parsing. |
| Profile | 44 or 46 | 47 | `LoadPlayerFromDisk` uses the same structured-stat and profile-reading path for 46 and 47. Its 47 comparison controls the game's version-change backup behavior. The actual v47 file has 205 scalar slots across 10 statistic groups, with the same ordered sections through the player package. Preserve the raw profile prefix, including world/maps and history. |
| Player | 23–33 | 34 | `Player.Load` and `Player.Save` confirm that the inventory and skills remain in their prior positions. After skills, the current structure is counted string-pair custom data, three float32 vitals, a length-prefixed build UI blob, a counted table of int32 pseudo-counter pairs, and a counted table of int32 upgrade seed pairs. The last two tables are gated at player v34 in the game reader. ULF validates framing through the end of this tail and preserves the original bytes. Legacy tails retain their established opaque handling. |
| Inventory | 109 | 110 | `Inventory.Load` and `Inventory.Save` use an int32 section version and uint16 record count. `ItemDrop.ItemData.Load/Save` confirm the same compact record layout for the fields ULF edits. Durability is a signed int32 in hundredths, x/y/world level and the presence flags are bytes, and optional quality/stack are uint16 with implicit 1. Variant, crafter, prefab hash, custom strings, and the trailing flag byte retain their wire positions. The trailing byte's interpretation changes at v110. |
| Skills | 2 | 2 | `Skills.Save/Load` confirm the counted skill ID, level, and accumulator records. The ID is int32 and the two values are float32. ULF retains the original bytes of untouched values. |

The approved legacy combinations remain supported with their original guards. Profile 47 requires player 34, inventory 110 and skills 2. Other combinations involving the new versions and unknown future versions are rejected. ULF retains the source layout when exporting. The existing codec remains Qt-independent. The prior published fch-decoder layout corroborates the v46 baseline. [fch-decoder](https://github.com/lanchelms/fch-decoder).

### Pocket capacity

The installed `Humanoid` constructor starts with 8×4. `Player.OnSpawned` obtains the `invrows` unique entry and calls `SetInventorySize`, which clamps game height and can drop invalid positions. The inventory record count itself does not establish usable capacity. For v110, ULF uses four writable rows when the entry is absent, caps an unambiguous verified value at the existing six-row creation limit, and disables creation when the saved value is ambiguous or unsupported. The desktop catalog and export preflight enforce the same bound. Existing records retain their positions and higher rows remain inspectable. Legacy creation behavior stays in scope as before.

## Cheat metadata and achievements

- `PlayerProfile.SavePlayerToDisk` writes the profile cheat boolean after the start seed, plus statistic-group history including command records. These sections and related world data are covered by the exact protected profile comparison at export.
- `ItemData.Load` consumes the trailing byte for v109. It assigns bit 0 to `m_cheated` at v110 or later. The desktop therefore describes the legacy byte as preserved and shows set/clear only for v110. All trailing bits and unrelated optional encodings are preserved by the normal edit path. A newly created record starts with the trailing byte clear, and export rejects attempts to modify retained flag bytes.
- The 1.0.20 game patch describes changes to the game's treatment of cheat flags. ULF makes no eligibility prediction from its preservation checks. In-game load/resave behavior and achievement outcomes depend on the game, character, world, mods and server conditions. No console commands, runtime patches, or achievement-related writes were used. [Iron Gate 1.0.20 patch notes](https://www.valheim.com/news/patch-1-0-20/).

## Local sample verification

| Check | Result |
|---|---|
| Size and framing | 280,235 bytes total. 4-byte body length, 280,163-byte body, 4-byte digest length, 64-byte digest. No additional bytes. |
| Versions | 47 / 34 / 110 / 2 |
| Inventory and skills | 33 item records, 22 skill records. The existing catalog identified 30 items with verified limits. Three unknown records remained protected and read-only. |
| SHA-512 and byte-for-byte round trip | Passed both. The original file digest matched before and after the checks. |
| Unexpected fields | None within the inspected schema. The 3,954-byte post-skills region was fully accounted for by the current tail structure. Its contents remained byte-identical. |
| Disposable copy | Used a separate temporary source and destination. Applied high quality 65,535, quantity and durability edits, removal, creation, and a fractional skill edit. Safe Save As reopened successfully and validated intended changes, protected regions, unknown item bytes and untouched skill bytes. The temporary copies were removed. |
| Repository | The original is ignored by the existing `*.fch` rule and no character save is tracked. No path, name, hash identifiers, or personal contents are included in this report. |

## Automated verification and scope

Windows 10 build 19045, Python 3.12.3, PySide6 6.12.0. The full suite passed **78 tests**, with **0 failures and 0 skips**. The original Alpha 0.2 baseline passed all 69 before implementation. Run `.venv\Scripts\python.exe -B -m unittest discover -s tests`.

- **FR-001–005, FR-007, FR-080, proposed FR-100.** Exact no-op on both version families, independent local format verification, current malformed and truncated data rejection, mixed/future version rejection, and source immutability.
- **FR-010–018, FR-030–032, FR-060.** Quality and stack limits, durability, valid creation, removal and replacement, position/crafter/equipment metadata, flags, unknown/custom bytes and write-capacity enforcement. Duplication is outside the existing feature set. Catalog completeness remains partial.
- **FR-040–044, FR-071–072.** Atomic skill batches, unchanged XP and unknown skill bytes, graphical controls, explicit drafts and review. Offscreen Qt covers current-format load, item and skill editing, review, export and reopen through the file worker.
- **FR-050–053, FR-056–057, NFR-001/005.** Separate Save As, alias checks, source-change detection, protected-region comparisons, disk read-back and atomic publication. The v110 failure injection verifies cleanup and retention of a pre-existing destination when temporary-file bytes fail checksum.
- **FR-061/063, NFR-002/003.** No achievement conclusion or native Linux runtime claim. The application remains offline and the native platform and game tests are outstanding.

Core changes are in `core/fch.py` and `core/export.py`. Desktop adjustments are confined to slot availability and version-aware flag text in `desktop/session.py` and `desktop/inventory.py`. Regression coverage is in `tests/synthetic.py`, `tests/test_current_format.py` and `tests/test_desktop.py`. The README and item-stat research link to this report. The approved requirements remain unchanged.

## Owner acceptance checklist

1. Close Valheim, keep an independent copy of the original outside the game's character folders, and use a disposable local character. Use a separate offline world for the test.
2. Open the disposable input in ULF. Confirm versions 47 / 34 / 110 / 2, SHA-512 and byte-exact round trip. Check that inventory, skills, and existing equipped items are visible.
3. Apply a verified stack edit, a practical quality or durability edit, a removal and an addition within the eligible slots. Edit one skill level and explicitly edit XP on a second skill. Review changes and use Save As to a separate file.
4. Reopen the output in ULF. Confirm intended edits, untouched XP, and checksum. Compare the original's digest. Give the disposable export a separate test slot before loading it in Valheim 1.0.21.
5. Load, play briefly, exit and reopen the game-resaved test copy. Check positions, items, equipment, skills and format. Exercise unusually high quality only in a separate disposable test.
6. Repeat native open/export and offline checks on Windows 10 and Linux. Keep any achievement eligibility tests separate and record the exact build and world/mod conditions. Keep all real test files local.
