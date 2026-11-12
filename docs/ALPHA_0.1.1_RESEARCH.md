# Alpha 0.1.1 stabilization and acceptance report

**Date:** 2026-11-12. **Classification: INITIAL WINDOWS AND IN-GAME ACCEPTANCE PASSED.**

The automated stabilization gate passes. The known inventory identity, partial skill transaction, noncanonical item encoding and same-slot replacement/export defects have regression coverage. All 76 local vanilla inventory records are identified with independently verified stack limits. The owner completed initial Windows and in-game acceptance. Full MVP and production acceptance remain open.

## Implementation and corrected defects

- `core/fch.py`: retain original optional-field flags and bytes, including explicit default values, zero crafter IDs with names, nonminimal string lengths and wide custom-data counts. Unchanged unknown records stay byte-identical. Preserve untouched float32 skill bytes, including NaN payloads and negative zero; edited levels/XP validate before serialization. Stable hashes now use UTF-16 code units and NUL termination. Bound strings/counts and reject unsupported embedded versions. Quality supports 1–65,535 for edits; raw zero values can be preserved without legitimizing zero-valued proposals.
- `core/editing.py`: Qt-independent atomic item and skill transactions. Validate whole proposals before mutation; preserve XP unless explicitly edited. Reject ambiguous duplicate skill edits, invalid numeric types, invalid stacks and unverified item modifications. Removal operates on a selected record's identity.
- `desktop/app.py`: protect existing prefab identity; resolve newly added prefabs from current text rather than stale combo data. Preserve unchanged form values and pending skill text across inventory refresh. Invalid skill batches stop export. Removal and addition can replace a slot without retaining the removed item's identity or flags.
- `core/export.py`: original record indices distinguish retained records from newly added items, fixing removal/replacement in the same coordinates. Check intended inventory/float32 skill values after serialization, protected character segments and item metadata, unique slots and record identities, catalog limits and new-item flags. Reject source paths/hard-link aliases and externally changed sources. Write, flush, fsync and close a temporary file; reread exact bytes, reparse/check SHA-512 and round-trip, then atomically replace the destination. Failure messages identify the operation; cleanup failures explicitly report the temporary-file residue instead of claiming success.
- `core/catalog.py` and `core/catalog.json`: offline lookup with 821 sourced entries and no null stack limits. The catalog is still a reviewed subset of current vanilla items, not a completeness claim.

No original save, approved requirement, or existing cheat metadata was changed. No web infrastructure or Alpha 0.2 interface redesign was introduced.

## Catalog investigation and reproducible evidence

| Measure | Earlier session | Final |
|---|---:|---:|
| Catalog entries | 813 | 821 |
| Recognized records across both saves | 68/76 | 76/76 |
| Records with verified maximum stacks | 63/76 | 76/76 |
| Unresolved sample hashes | 8 | 0 |
| Unverified sample stack limits | 13 | 0 |

Sample A: 34/34 recognized and verified. Sample B: 42/42 recognized and verified. The samples contain 62 distinct prefabs; all 62 were independently inspected in installed vanilla game data. No stack-limit differences were found for previously sourced entries in that set.

The installed Steam manifest identifies build **26249040**, corresponding to Valheim **1.0.21**. The read-only extractor inspected ItemDrop components in bundle `c4210710`, reading `m_itemData.m_shared.m_maxStackSize` and `m_maxQuality`. Bundle SHA-256: `84f55cfb24af51b9f0494fd9d1a355bf009e08545ff8ccf607c7d88d2e4e1ec8`. The factual result is recorded in `references/local-game-item-limits.json`; it contains no character names, account identifiers, file paths, or save bytes.

`tools/inspect_game_items.py` reproduces the inspection using optional research dependency UnityPy **1.25.4**. Invoke it with a locally installed bundle path and prefab names; it prints only selected numerical metadata and the bundle digest. It never writes to game files. UnityPy is not an editor runtime dependency. Only the project virtual environment was augmented for this investigation.

| Previously unresolved prefab | Stable hash | Maximum stack |
|---|---:|---:|
| OrbThunderBlood | 1263128497 | 50 |
| StaffThunderBlood | -677306358 | 1 |
| StaffSpiritCaller | -1724175458 | 1 |
| StaffOrbofAhri | -1819695760 | 1 |
| StaffFrostOrbs | -97147916 | 1 |
| FistGold | 690355706 | 1 |
| FistGold_BloodLightning | -987977923 | 1 |
| FistGold_FrostFire | 1990120219 | 1 |

The other five formerly unverified entries are BombDynamite (50), Leatherstraps (50), GrapplingHook (1), SwordGold_BloodLightning (1) and SwordGold_FrostFire (1). These are vanilla game prefabs, not inferred mod records.

### Sources and licensing

- The initial expansion uses inventory-valid metadata from [MIT-licensed fch-decoder](https://github.com/lanchelms/fch-decoder/tree/1a5ff4f767e1bbf2f7955d4dcd22e628eb318427), pinned at `1a5ff4f767e1bbf2f7955d4dcd22e628eb318427`. The TSV and MIT notice are retained. Its parser documentation informed compact item fields and UTF-16 hashing; executable code was not imported.
- [Jotunn generated item list](https://valheim-modding.github.io/Jotunn/data/objects/item-list.html), generated for game 1.0.7, independently establishes the eight missing vanilla identities. Snapshot pinned to Jotunn commit `41cd418939707f9ae925e8c2927c195c1af0c906`, with MIT notice, in `references/`. This table does not establish stack limits.
- [Valheim Database's extraction provenance](https://valheimdb.com/about) corroborates game 1.0.21/build 26249040 and its ObjectDB extraction method; its [Thunderblood Essence page](https://valheimdb.com/items/thunderblood-essence) explicitly corroborates stack 50. No website dataset or artwork was imported.
- [ratbuddy's catalog](https://github.com/ratbuddy/valheim-fch-editor/blob/main/item_catalog.json) supplied candidates. Its reuse license was not established; its dataset was not copied. Installed game metadata independently resolved the candidates. Its cheat-metadata documentation was consulted, without importing implementation code.
- [UnityPy](https://github.com/K0lb3/UnityPy) is MIT-licensed and used only for research. The checked-in extraction utility is original project code. No game executable, asset bundle, artwork, or complete serialized prefab is redistributed; the local evidence consists only of identifiers and numerical compatibility facts. Full application/dependency distribution licensing remains a release gate (NFR-008).

## Automated and local validation

Command: `.venv/Scripts/python.exe -B -m unittest discover -s tests -v`.

**53 tests passed, 0 failed, 0 skipped**, on Windows 10 build 19045, Python 3.12.3 and PySide6 6.12.0. The original 29-test baseline remains covered; the interrupted 37-test state passed before further development. The final suite includes seven offscreen Qt tests. A separate run with PySide6 imports explicitly blocked passed all 46 core tests. Git whitespace validation passed. Subtests additionally exercise all 62 extracted prefab limits and 22 existing profile/player combinations.

Coverage includes quality-only edits and format maximum, stack bounds, add/remove/replace, invalid prefabs and coordinates, custom/unknown bytes, raw skill precision, atomic invalid batches, invalid types, duplicate skills, unsupported versions, truncated inputs, bad checksums, source/hard-link protection, changed sources, metadata changes, disk corruption, temporary creation/write/flush/publication/cleanup failures, and closed-file read-back. Qt tests cover window construction, file selection handlers with failure/recovery, item/skill edits, pending-value preservation and synthetic disk export/reopen. Native file dialogs are mocked, not interactively accepted.

Both original vanilla files were read-only rechecked: SHA-512 validation and byte-identical no-op round trips pass. Every one of the 76 items was separately edited to quality 65,535 on an in-memory copy and reparsed successfully; item-tail flags were unchanged. Original bytes were rechecked after inspection and remain identical. No real save output was generated or uploaded.

The accepted parser matrix remains profile 44/46, player 23–33, inventory 109, skills 2. Real-file evidence covers **46/33/109/2 only**. Synthetic older layouts test current parser behavior, not independent historical game correctness. No version expansion was made.

## Requirement disposition

| Requirement IDs | Stabilization disposition and evidence |
|---|---|
| FR-002–005, FR-010, FR-015–016 | Implemented and regression-tested for the supported current layout: checksum/no-op gate, raw encodings and unrelated metadata preservation. Historical game variants still need independent evidence. |
| FR-011–014, FR-018, FR-072 | Implemented and tested: transactional item edits, high quality, bounded stacks, add/remove and replacement. |
| FR-030–032, FR-097–098 | Sample-catalog gate complete and tested; all 76 records verified, offline lookup and unknown protection. Comprehensive vanilla catalog/search metadata remains Alpha 0.2. |
| FR-040–043 | Implemented and tested: unknown skill preservation, valid bounds, XP preservation and atomic batches. |
| FR-050–053, FR-056, FR-060 | Implemented and tested: source protection, semantic verification, closed-disk read-back, failure handling and metadata preservation. The owner confirmed that a modified export loaded and was playable in Valheim. Broader filesystem coverage remains open. |
| FR-096 | Complete: two read-only compatibility investigations with redacted counts. |
| FR-080, NFR-005 | Complete for stabilization: Qt-independent core and synthetic regression suite with no private-fixture skips. |
| NFR-002, NFR-003, NFR-007, NFR-008 | Partial at product-release level: Windows offscreen tests and offline design verified; Linux execution, broad hostile-input assurance and distribution licensing audit remain. |
| FR-017, FR-033, FR-044, FR-071 | Partially implemented or unimplemented usability scope for Alpha 0.2, including synchronized skill sliders. Not claimed complete by this stabilization. |

The owner assignment explicitly preserves experience unless edited, superseding the still-proposed D-03 reset default for this milestone. Approved REQUIREMENTS.md and AGENTS.md were not rewritten.

## Owner acceptance

The owner reported on 2026-11-12 that all inventory items in the tested Windows session appeared correctly identified (FR-030, FR-097). Item and skill editing worked without observable errors (FR-011–014, FR-041–043). A modified character save loaded successfully in Valheim, and the character was playable (FR-050–053). The interface supported the tested workflow, and the owner identified significant usability and visual improvements for Alpha 0.2 (FR-017, FR-033, FR-044, FR-070–071). Alpha 0.2 implementation awaits design approval.

The confirmation covers the reported workflow. Individual edit operations, native Windows version, offline mode, source-digest comparison, exact in-game field values, and the Valheim build were unspecified in the owner report. Linux compatibility remains unverified (NFR-002/003, FR-098). Achievement eligibility remains unverified and requires separate controlled testing. Outcomes can depend on character and world state, mods, game version, and server behavior (FR-060–063).

## Remaining risks and verification

1. Complete the Windows 10 and Linux offline acceptance matrix: open a disposable save, change quality/quantity, remove/add, edit level/XP, export to a distinct file, reopen, and verify the original digest. Linux has not been executed here; path handling uses pathlib, samefile and same-directory temporary files, but permissions, Qt dependencies and rename behavior need real platform testing.
2. Use disposable exported copies for follow-up Valheim testing of specific item behavior, skill values and metadata. Structurally valid extreme quality values do not establish game behavior. Achievement eligibility remains a separate, unverified concern.
3. Historical layouts, large/modded saves and unusual filesystem configurations need further compatibility samples. The fixed 8×6 UI does not display out-of-grid items; those records are preserved. Duplicate occupied slots block export rather than silently deleting data.
4. Atomic replacement protects normal publication failures. Adversarial filesystem alias races and power-loss durability after rename are not guaranteed. If permissions prevent cleanup, the reported temporary file must be removed manually.
5. Complete the comprehensive catalog, usability/sliders, dependency pinning/distribution audit and later release gates before claiming full MVP or production readiness. No known reproduced stabilization defect remains open.

## Release verification

Branch: `fix/alpha-0.1.1-stability`. Remote: `https://github.com/LoneWolf862/ULF-Editor.git`.

GitHub branch verification matched stabilization commit `93b20243fac342d2630929f599b5942a914906d5`. The release verification run passed all 53 automated tests with zero failures or skips.
