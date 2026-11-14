# Alpha 0.4 inventory management

Development branch: `feature/alpha-0.4-inventory-management`, based on approved
Alpha 0.3.1 `afd9bd8`. Owner instruction schedules advanced inventory work for
this milestone; REQUIREMENTS.md remains unchanged. Owner acceptance is complete;
the release candidate awaits pull request review and explicit merge/release approval.

## Owner acceptance — recorded 2026-11-14

The project owner reports Alpha 0.4 development and manual acceptance testing
complete, including successful Windows manual testing and successful Valheim
in-game load and save verification for the tested workflow. These are
owner-reported results, separate from the automated checks below. The acceptance
statement does not provide a per-case log or a complete hardware/DPI matrix;
it is not treated as evidence for every catalog item, extreme-quality edge case
or unsupported equipment/metadata policy. The targeted game format remains
Valheim 1.0.21; no broader version compatibility is claimed.

Native Linux testing remains pending. Owner acceptance authorizes preparation
of the PR, not merging, tagging or publishing. All three remain gated on a
subsequent explicit owner approval.

## Acceptance gates

- FR-019/091: move/swap atomically within verified writable pockets, preserve
  every non-coordinate byte, reject occupied/unknown/ambiguous targets.
- FR-020/043/072: undo restores exact serialized state and record identity;
  redo restores the validated result; bulk edits are one action; invalid edits
  do not enter history; drafts block history travel instead of being committed.
- FR-012–016/018/032/054: duplicate/replace/fill use verified limits, preserve
  unrelated records, show all effects, and reject opaque metadata policies.
- FR-090: preview supported equipment conflicts from pinned game evidence;
  do not guess unsupported hand/slot rules.
- FR-050–053/060, NFR-005: retain full safety regressions and export/reopen
  multi-operation results with unknown and cheat metadata intact.
- FR-017/071/073: visible actions, keyboard alternatives and drag/drop invoke
  the same transactions; review and selection follow undo/redo.

## Architecture and initial policies

`core/inventory_ops.py` implements core movement, swaps, duplicate, replacement
and fill. The desktop session validates commands on private candidates before
publishing. `core/history.py` is a widget-independent history of validated
transactions; command descriptions accompany private before/after mementos so
undo preserves raw encodings, source identities and skill float bits. It does
not decode a serialized snapshot and accidentally rebase source identities.
History is session-local and in memory. Export revision tracking is separate.

Movement changes only x/y. Unknown and ambiguous records cannot move or swap.
Existing out-of-pocket records are preserved, not relocated. Export independently
checks changed coordinates against source/destination bounds and still protects
all other metadata. New APIs do not grant arbitrary metadata mutation.

Duplication requires v110, verified identity/limits, legal quality/quantity and
nonnegative representable durability. It preserves quality, quantity, durability,
crafter ID/name, picked-up state and supported raw optional encodings; the copy
is unequipped with new identity and zero trailing flags. Source stays untouched.
Custom data, nonzero variant/world level or any trailing flag blocks duplication;
flags are never scrubbed to make an item eligible.

Replacement uses an explicit fresh-item policy: verified target, selected
quality/quantity, computed target maximum durability (zero for inapplicable
durability), unequipped, picked up, zero variant/world/trailing flags, empty
crafter/custom data. Opaque/custom/variant/world/flagged sources are rejected.
Crafter attribution loss must be visible in the preview. No metadata is assumed
transferable across prefabs. Fill Stack never reduces a preserved oversized stack.

Undo/redo is blocked while any form drafts exist. Invalid commands leave both
history directions intact; divergent accepted commands clear redo. Dependent
organization changes use Undo or Discard All; targeted discard fails explicitly
instead of replaying a partial swap/replacement. Existing simple discard remains.

## Implemented workflow

Visible Undo/Redo buttons and Ctrl+Z, Ctrl+Y and Ctrl+Shift+Z cover item quality,
quantity, durability, creation, removal, Repair, Repair All, skill edits and all
new inventory operations. Multi-record equipment changes and bulk operations
are single history entries. Selection remains on a surviving selected record or
a valid slot after history travel. History is not persisted across reopen.

Move/Swap, Duplicate, Replace, Fill Stack and Equip/Unequip appear in the selected
item inspector. Disabled actions explain their eligibility constraints. A
keyboard-accessible destination chooser provides the same operations as grid
drag/drop. Internal drags show the item name and highlight valid destinations;
external, stale and invalid drops are rejected. Occupied targets require a swap
preview. Qt's implicit model movement is never used.

Every quick action shows complete before/after records in a scrollable preview,
including coordinates, quality, quantity, durability/max, equipment state,
crafter, picked-up state, variant, world level, custom data and trailing flags.
Cancel leaves the working state untouched. Preview generation and expected
serialization are checked again before applying. Review Changes shows the final
field differences, both swapped records and all affected equipment flags; it is
a net-change view, not a chronological audit log. Replacement appears as the
removed original and the new replacement, with metadata on both records.

The raw equipped checkbox is read-only. Equipment changes use the complete
conflict preview. Equipped cells have an E badge and accessible text; a compact
overview lists saved slots and existing conflicts. Existing unsupported or
contradictory states are preserved on load rather than silently normalized.

## Equipment evidence and supported scope

Rules were independently inspected from the locally installed Valheim 1.0.21
build 26249040, `Humanoid.EquipItem` and the item-type enum. Assembly SHA-256:
`9f959c0396ec4240d47fcbe5d0d062c428cc627244506db5ea567f9d77b2b769`.
The local bundle `c4210710` SHA-256 is
`84f55cfb24af51b9f0494fd9d1a355bf009e08545ff8ccf607c7d88d2e4e1ec8`.
The existing bundled factual item snapshot supplies each prefab's type.
No game code, assembly, decompiled output, assets or personal saves are included.
Viking Editor research informed preview and float-preservation safeguards; no
third-party implementation was copied.

| Verified item type | Saved slot conflicts modeled |
|---|---|
| One-handed weapon (3) | Right hand; compatible with a supported shield |
| Shield (5) | Left hand; compatible with a supported one-handed weapon |
| Bow (4), two-handed weapon (14), tool (19), two-handed-left (22) | Both hands |
| Helmet (6), chest (7), legs (11), shoulder (17) | Helmet, chest, legs, cape respectively |
| Utility (18), trinket (24) | One item in each respective slot |
| Ammo (9), non-equipable ammo (23) | Shared ammunition selection slot |

Equip previews all conflicting supported records becoming unequipped. Broken
durability-using items are rejected. Torch (15) has context-dependent hand
behavior and is excluded, as are unverified categories. A scan of all 927
verified inventory candidates found DLC metadata on HelmetOdin, CapeOdin and
TankardOdin; offline ownership cannot be established. The two supported-slot
Odin items cannot be equipped by this workflow; TankardOdin has no supported
equipment slot. Unknown equipped records, custom metadata and positive or
otherwise nonzero world-level contexts block new equip proposals. Known
equipped items can explicitly be unequipped without clearing other flags.

These are saved-slot constraints, not an emulation of live game state. World
settings, DLC ownership and transient swimming/attacking/death restrictions are
not available from this editor. Equipment management requires inventory v110.
The owner has accepted the tested gameplay workflow; untested contexts remain
outside that acceptance scope.

## Validation results — rerun 2026-11-14

**126 tests passed; zero failures, zero skips**, using Windows Python/PySide6:
`.venv/Scripts/python.exe -m unittest discover -s tests -q`.
The original 101 tests remain included. Core/history added 12 tests; equipment
added 6 and desktop workflow added 7. Parameterized subcases exercise additional
combinations without inflating the test count.

Coverage includes all supported transaction history, move/swap preservation,
invalid coordinates, unknown records, full inventory, copy policy, replacement
limits/maxima, divergent edits, drafts, long sequences, late failures, equipment
conflicts, cancellation, stale previews, keyboard shortcuts, drop-handler
routing, source protection and multi-operation export/reopen. Unknown record
bytes, unrelated character sections and existing trailing flags are asserted
unchanged. Existing checksum, no-op, version, alias, atomic export and external
source-change safety regressions remain passing.

Desktop tests run with Qt's **offscreen** platform. A synthetic 1366×768 render
was visually inspected for the new inspector actions and history controls.
These automated checks alone do not constitute native mouse-drag, accessibility
or DPI acceptance. The separate Alpha 0.4 owner report above establishes
successful Windows manual and in-game load/save acceptance for the tested
workflow. Native Linux and the broader accessibility/DPI matrix remain unverified.

## Pre-PR review — 2026-11-14

Reviewed the complete feature-branch diff against `origin/main` (`afd9bd8`),
including export coordinate validation, transaction identity/history, preview
staleness checks, drag/drop routing, equipment constraints and regression tests.
No blocking defect or unintended unrelated modification was identified. The
branch preserves the original 101 tests and adds 25 tests with parameterized
subcases. Automated native OS drag-loop coverage and exhaustive slot/category
combinations remain gaps; the suite is not claimed exhaustive.

REQUIREMENTS.md, the binary codec, catalog and dependency definitions are
unchanged. The reviewed files contain application code, synthetic tests and
documentation only: no personal saves, research dumps, binaries, credentials or
temporary files. No unrelated research branch is included. Compatibility
limitations remain explicit: copy/replacement and equipment require v110,
unknown records cannot be organized, and raw equipped-checkbox editing is
replaced by the validated preview workflow.

Owner review should confirm the documented conservative copy/fresh-replacement
policies and acceptance of pending Linux coverage for the intended release.
Formal baseline requirement amendments remain proposals, not implied changes
from this acceptance record. No new feature implementation is required by this
review; release authorization is still outstanding.

## Requirements status and proposed amendments

Implemented and regression-tested for the supported scope: FR-019 movement,
swap and drag/drop; FR-020 history/review; FR-012–016/018 inventory editing;
FR-032 metadata preservation; FR-043 skill transactions; FR-050–054 and
FR-060 export/validation; FR-072 staged mutation. FR-017/071/073 have automated
UI coverage but native accessibility/platform acceptance remains partial.
FR-090 equipment is partial outside the verified slot subset. FR-091 remains
partial because automatic sorting is outside this assignment. NFR-005 safety
regressions pass; platform-wide acceptance is not claimed.

The owner explicitly scheduled this post-MVP inventory milestone. The following
policy amendments are **proposals for owner review**, not edits to REQUIREMENTS.md:

- Ratify the conservative duplicate policy above. Extension to nonzero variants,
  custom metadata or world levels requires per-field compatibility evidence.
  Flagged-source copies remain blocked; never clear the source's flags.
- Ratify replacement as a fresh-item operation with explicit attribution loss
  and computed full durability, rather than implicit cross-prefab transfer.
- Define future torch/unsupported-category, DLC and world-context equipment
  rules before expanding the slot model; keep unknown records immutable.
- Decide whether persisted history/recovery and dependency-aware selective
  discard should be a later milestone. Current history is session-local and
  dependent organization transactions use Undo or Discard All.

## Acceptance checklist retained for repeat testing

Windows and game acceptance are recorded above. This list remains available for
repeat testing; it is not a claim that each subcase has an individually logged
owner result. Step 7 remains pending.

Use a disposable copy, retain an independent backup and keep Valheim closed
while editing. Do not replace the original through the editor.

1. On native Windows, move and swap by dragging and by keyboard destination
   selection; cancel previews and attempt invalid destinations. Check focus,
   selection, scrolling and ordinary/high-DPI desktop layouts.
2. Duplicate a supported high-quality item; verify crafter, quantity, exact
   durability, unequipped copy and untouched source. Check a full inventory and
   blocked custom/variant/flagged sources.
3. Replace with a different verified prefab/stack limit. Confirm the displayed
   durability/max and every metadata reset before staging. Fill a partial stack.
4. Equip one-handed plus shield, then a two-handed weapon; verify the preview
   and resulting flags. Exercise armor/cape/utility/ammo and unsupported items.
5. Interleave all actions with Repair/Repair All and skills; undo/redo repeatedly,
   branch after undo and attempt history travel while drafts exist. Inspect the
   net review and pending/exported indicators.
6. Save As to a separate file, reopen in ULF, load the disposable export in
   Valheim 1.0.21, inspect the items/equipment, save in-game and reopen in ULF.
   Confirm original and unrelated metadata remain unchanged.
7. Repeat the supported workflow natively on Linux, including offline operation,
   file dialogs, keyboard navigation, drag/drop and export. Record results
   separately; Linux remains pending until performed.

**OWNER ACCEPTED — READY FOR PR REVIEW** within the documented conservative
scope. This is not merge or release approval. Remaining limitations include
native Linux and broader accessibility/DPI coverage, untested gameplay edge
cases, opaque copy/replacement policies, unsupported equipment categories,
legacy copy/equipment support, unbounded in-memory history and inherited
extreme-quality/build-specific statistic limitations. No merge or release tag
is authorized by this development milestone.
