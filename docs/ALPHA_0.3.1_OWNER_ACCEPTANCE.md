# Alpha 0.3.1 owner acceptance

Prepared November 13, 2026. **Not yet run by the owner.** Record pass/fail and
observations below; no merge or release follows automatically.

Scope: FR-001–005, FR-011/015–018/030–033/050–054/057/060–063/071–073,
NFR-001–003. Use Valheim 1.0.21 (audited build 26249040); record the actual game,
OS, ULF commit and mods. A different game build needs compatibility review.

## Safe preparation

1. Use only a disposable character and disposable world. Quit Valheim before
   opening or replacing saves. Keep a backup of the complete disposable save
   pair outside the game's save directories. Do not test on a main character.
2. In Valheim's character selection, use **Manage saves** to identify the
   disposable character and make it Local if needed. Quit the game. On Windows,
   open `%USERPROFILE%\AppData\LocalLow\IronGate\Valheim\characters_local`.
   Locate the matching `.fch` and `.fch.old`, if present. If the character is
   absent or storage differs, stop and resolve its location through Manage saves;
   do not guess a cloud path or overwrite another character.
3. Copy the disposable `.fch` to a separate test folder as `input.fch`. Keep an
   untouched copy and record its SHA-256 with PowerShell
   `Get-FileHash -Algorithm SHA256 -LiteralPath '<full path to input.fch>'`.
   ULF must only export to different filenames in this test folder.
4. Launch `.venv\Scripts\python.exe run.py` from the checkout on
   `release/alpha-0.3.1-validation`. Check **Alpha 0.3.1**. Open `input.fch`;
   expect SHA-512 and byte-exact round-trip success. Record inventory/skill
   counts. Never add flags or other metadata to manufacture a test result.

## Desktop and export cases

Start each case by reopening `input.fch`, discarding only the prior test session.
Apply each edit before Review Changes. Unapplied drafts must block export.

| Case | Exact action | Expected result |
|---|---|---|
| No-op | Review Changes → Export Save As → `noop.fch` | No differences; verified export; source and output hashes equal. |
| Identity/statistics | Select Thunderblood Sword, Lightning Strike, Moose Hide Cape and Ice, if present; select both a weapon and armor | Correct names; current/max and percentage for equipment; Ice has stack cap 50 and no applicable durability. |
| Quality | On a q8 Thunderblood Sword, change Quality to 9; Apply; review; export `quality.fch` | Only quality 8→9; current durability unchanged; maximum 750→800; high-quality warning shown. |
| Single Repair | Select damaged q8 Thunderblood Sword; Repair; review; export `repair-one.fch` | Only current durability changes, e.g. 715→750. Quality, quantity, equipped state and skills unchanged. |
| Cancel bulk | Record review count; Repair All; inspect every proposed change and skipped reason; Cancel; export `cancel-all.fch` | Review count unchanged; output byte-identical to input when no earlier edits exist. |
| Bulk Repair | Repair All; record proposed count and targets; confirm; review; export `repair-all.fch` | Changed-record count equals preview; only eligible damaged items repaired. Over-maximum items remain unchanged. |
| Reopen | Open each output separately | Integrity checks pass; stored edits match review; no extra changes. |

For the supplied experimental baseline, bulk repair proposes **10** items and
skips **23**; one over-maximum item must stay at 1600, not fall to 800. A fresh
disposable character may have different counts. Record actual values.

Expected maxima (these are calculated, not stored maximum fields):

| Item | Quality | Maximum durability |
|---|---:|---:|
| Thunderblood Sword | 8 | 750 |
| Lightning Strike | 8 | 750 |
| Moose Hide Cape | 32 | 2750 |

Also check at an ordinary desktop size: all eight columns, readable labels,
scrollable inspector, visible Apply/Repair buttons, keyboard focus and precise
numeric input. Native accessibility reported numeric spinner values as zero
during agent inspection; verify actual displayed values and screen-reader
behavior separately. Offscreen tests do not establish native accessibility.

## Install, play, save and reopen each variant

1. With Valheim closed, move the **disposable** character's existing `.fch` and
   `.fch.old` out of `characters_local` into a uniquely named backup folder.
   Preserve them. Copy exactly one tested output into `characters_local`, using
   the disposable character's original file basename. Do not install several
   copies of the same character identity or replace a main character. Renaming
   an export does not change its internal character identity.
2. Start Valheim and select the disposable Local character. Enter the disposable
   world. Confirm inventory identities/counts and the expected quality. If an
   unexpected character appears, quit without playing and resolve the files.
3. Before using or repairing items in-game, inspect tooltips and record current
   and maximum durability. Compare the three examples above where available.
   Record game rounding rather than assuming text precision is identical.
4. For `repair-one`, verify only the chosen damaged item begins repaired. Use
   it once and verify durability decreases normally. For `repair-all`, verify
   all previewed items begin repaired and skipped items retain their values.
5. For `quality`, verify q9 sword maximum 800. Check the q32 cape and other
   high-quality gear: tooltip, equip/unequip, appearance and basic use should
   work without errors or disappearance. Do not infer that quality 65535 is
   gameplay-safe from its serialization support.
6. Log out normally to save, then quit Valheim. Copy the game-resaved `.fch`
   back into the test folder under a new name, e.g. `repair-all-game-resaved.fch`.
   Open it in ULF. Expect checksum/no-op validation, preserved identities and
   qualities, and plausible current durability after use. Game activity may
   legitimately change timers, position, skills and other metadata; do not
   demand byte identity after gameplay.
7. Repeat with each variant, preserving each game-resaved result separately.
   Restore the disposable backup only with the game closed. Retain test saves
   locally; do not attach them to GitHub or commit them.

Fail the affected case for load errors, checksum failure, disappearing/wrong
items, incorrect maxima, unexpected quality/quantity/metadata edits, missing
preview changes, cancellation that mutates state, source modification, runtime
exceptions or controls that prevent completion. Record step, expected/actual
values and sanitized error text; avoid names, IDs and real saves in reports.
Achievement eligibility is separate and can depend on world, mods, version and
server state. No eligibility guarantee or cheat-history removal is implied.

## Owner result sheet

Game/build: ______ OS/DPI: ______ ULF commit: ______ Mods: ______ Date: ______

- [ ] PASS / FAIL — native open, inventory, armor/weapon selection and controls
- [ ] PASS / FAIL — identities, statistics and three maximum examples
- [ ] PASS / FAIL — no-op and original hash unchanged
- [ ] PASS / FAIL — quality-only edit and high-quality gameplay
- [ ] PASS / FAIL — individual repair, export and game use
- [ ] PASS / FAIL — Repair All preview, count, skips and cancellation
- [ ] PASS / FAIL — all exported variants load in Valheim
- [ ] PASS / FAIL — game save, quit and ULF reopen
- [ ] PASS / FAIL — no unexplained changes or runtime exceptions
- [ ] PASS / FAIL / NOT RUN — native Linux offline workflow

Notes/failures: ______

Owner merge decision (separate from release approval): ______
