# ULF Editor Alpha 0.3.1

November 13, 2026 · Owner-approved alpha release · `v0.3.1-alpha`

Alpha 0.3.1 combines comprehensive vanilla item catalog improvements with
equipment statistics and safe repair workflows for Valheim 1.0.21.

## Included

- **1,049 catalog entries**, including all **927 verified ordinary inventory
  candidates** from the 1,522-prefab registry audit.
- **288 verified maximum durability definitions** and **285 repairable equipment
  types**. Moose Hide Cape, Ice, Thunderblood Sword and Lightning Strike resolve.
- Current/maximum durability and percentage; quality-scaled item damage, armor,
  block and deflection, with parry and movement where applicable.
- **Individual Repair** and **Repair All** with a complete preview, exclusions,
  transactional application and change review. Already full/over-maximum items
  are preserved. Quality-only edits preserve current durability.
- Valheim **1.0.21**, current layouts **47 / 34 / 110 / 2**. Legacy supported
  formats remain available; computed repair requires inventory v110.
- SHA-512 verification, byte-identical untouched round trips, verified stack
  limits, original/alias protection, disk-verified **Save As**, and preservation
  of unrelated character data and existing cheat-related metadata.

## Verification and owner approval

The full suite passes **101 tests, zero failures or skips** on Windows 10,
Python 3.12.3 and PySide6 6.12.0. It covers save integrity, current/legacy formats,
catalog limits, item/skill editing, statistics, repairs, cancellation/rollback,
Save As failures/aliases and protected metadata. Qt automated tests are offscreen.
Release procedure reruns the same suite on the merged main commit before tagging.

The owner reports successful Moose Hide Cape identification, Individual Repair,
Repair All, export, Valheim 1.0.21 load, persistence of repaired equipment after
game save, and reopening the game-resaved character. The owner explicitly
approved release of this tested functionality. These statements do not imply
that every candidate, platform or quality value was exercised in-game.

Earlier controlled local exports also passed independent decoded comparisons
and raw-byte preservation checks. No-op/canceled repair remained byte-identical;
bulk repair changed exactly ten durability fields and preserved an over-maximum
item. No real saves or experimental decoded data are distributed.

## Known limitations

- **Native Linux testing remains pending.** Windows automated and owner workflow
  results do not certify Linux, all DPI/resolution combinations or accessibility.
  Earlier agent-native screenshot/input failures remain documented; numeric
  spinner screen-reader values need further verification.
- Static registry coverage is not an in-game acquisition test of every item.
  Eleven entries lack friendly labels; 122 retained legacy entries lack verified
  statistics. Unknown/modded records remain protected; no mod overlay editor.
- Statistics use Valheim 1.0.21 build 26249040 evidence. Positive-world-level
  damage/armor, projectile/skill/status effects and final combat outcomes are
  outside the verified calculations. Future save versions are rejected.
- High qualities are format-representable up to 65,535, not guaranteed safe in
  gameplay. Extreme quality and broad edge-case game behavior remain untested.
- General undo/redo, backup recovery, drag/drop and full equipment-slot management
  remain incomplete/deferred. New item placement follows verified pocket limits.
- Save editing does not guarantee achievement eligibility. Existing cheat history
  is preserved, not scrubbed. No world editing or runtime game modification.
- This is a source alpha tag, with no new installer or game assets. Retained
  attribution/provenance applies; broader packaging/distribution license review
  under FR-035/NFR-008 remains open. Owner release approval is not legal clearance.

## Integration and traceability

The validation branch contains `454ac4e` (Alpha 0.3), `fac8e1b` (Alpha 0.3.1)
and `edd6ab1` (validation). One history-preserving merge into main integrates
these once. `research/viking-editor-comparison` remains separate: no research
experiments, copied third-party code or temporary files are incorporated.

Evidence supports FR-002–005/010–018/030–033/040–044/050–054/056/060/072 and
NFR-005 within the stated scope. Owner acceptance adds real-game evidence for
FR-018/030/051/053 and the tested load/resave path. FR-073, native Linux aspects
of NFR-002/003, and broader release/distribution gates are not marked complete.
Approved requirements are unchanged; this alpha is not full desktop 1.0 acceptance.

Recommended next milestone: native Linux/offline acceptance and desktop
reliability/usability polish, followed by separately approved undo/recovery work.
No Alpha 0.4 implementation is included.

Details: [validation report](ALPHA_0.3.1_VALIDATION.md),
[owner acceptance](ALPHA_0.3.1_OWNER_ACCEPTANCE.md),
[catalog provenance](ALPHA_0.3.1_ITEM_COVERAGE.md).
