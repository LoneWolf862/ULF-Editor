# Alpha 0.3.1 release-candidate validation

**Release update — November 13, 2026:** The owner approved the tested identity,
repair, export, Valheim 1.0.21 load, game-save persistence and reopening workflow,
and explicitly authorized merge and release. All **101 automated tests pass**
again on the release candidate. See the [owner result record](ALPHA_0.3.1_OWNER_ACCEPTANCE.md)
and [release notes](ALPHA_0.3.1_RELEASE.md). Native Linux and broader accessibility/
edge-case coverage remain pending. The earlier assessment below is historical;
its requirement for explicit owner approval is now satisfied.

Original assessment, November 13, 2026 (America/Denver): **PARTIALLY READY**: automated and local
save-integrity gates pass; native interaction/visual acceptance and in-game
acceptance remain open. No confirmed production defect was found or fixed.
No merge, tag or release was performed. The owner should complete the
[acceptance checklist](ALPHA_0.3.1_OWNER_ACCEPTANCE.md) before a merge decision.

## Baseline and acceptance criteria

Remote state fetched successfully before work. Clean checkout, one worktree;
created `release/alpha-0.3.1-validation` from the verified candidate. Ancestry:

| Branch | Commit | Relationship |
|---|---|---|
| main | e234755f7ccba89dc68c5c9838fd42ecc9271f62 | Stable Alpha 0.2.1 baseline |
| feature/alpha-0.3-item-stats | 454ac4efb343efe4fe295676e0c8ea0063fcd5a1 | Three commits after main |
| fix/alpha-0.3.1-item-coverage | fac8e1b7ba941ff56a2a300e7e374ca48a3fd91c | Two commits after Alpha 0.3; candidate |
| research/viking-editor-comparison | 5e2bcac76d5e736bb38266f8c8bd77bfdb514be3 | One documentation commit after candidate; not merged |

Defined gates: all existing regressions pass (NFR-005); untouched bytes and
protected metadata remain exact (FR-002–005/010/015–016/032/050–053/060);
catalog totals and three durability examples match (FR-018/030–033/097–098);
repair preview count equals actual changes and cancellation/rollback are atomic
(FR-018/054/072); native workflow and disposable game resave are recorded
honestly (FR-057/071–073, NFR-001–003). Approved requirements are unchanged.

## Automated evidence

Environment: Windows 10 build 19045, Python 3.12.3, PySide6 6.12.0.
Command: `.venv/Scripts/python.exe -m unittest discover -s tests -q`.
Baseline: **99 passed**. Final: **101 passed**, zero failures/skips.

Existing tests cover load/checksum/framing/version rejection; legacy and current
47/34/110/2 layouts; byte-identical no-op; inventory add/remove/quantity/quality;
skills and XP batches; identification/scaling/maxima; individual and bulk repair;
cancel, late-failure rollback and stale previews; unknown/custom/cheat metadata;
source aliases and changed sources; Save As disk verification and error cleanup.
Qt workflow tests use offscreen widgets and mocked native dialogs.

Two new synthetic tests in `tests/test_release_acceptance.py` explicitly guard
the research risks: raw 109210 hundredths survives no-op and quality-only disk
export; bulk repair changes exactly two previewed records while preserving a
1600/800 over-maximum record and all protected sections. No real fixtures added.

## Catalog validation

Recomputed from the current coverage ledger, catalog and statistics service:

| Measure | Actual | Result |
|---|---:|---|
| Registered prefabs partitioned | 1522 | Match |
| Ordinary candidates supported | 927/927 | Match |
| Total catalog | 1049 | Match |
| Applicable durability definitions | 288 | Match |
| Repairable equipment definitions | 285 | Match |

Moose Hide Cape, Ice, Thunderblood Sword and Lightning Strike resolve with
verified names/hashes/limits. Regression vectors confirm q8 sword = 750, q8
Lightning Strike = 750, q32 cape = 2750. No discrepancies. This revalidates
bundled data against the recorded audit; it is not a new extraction of all
game assets or proof that every candidate has been used in-game.

## Controlled real-save exports

Used a separate copy of the authorized research input, with no synthetic
metadata injection. One available original was read only and matched the
previously retained research digest after testing. The historical second sample
was not available. All files remain local in ignored `.venv/alpha031-validation/`;
no save, personal identifier, raw decoded structure or source digest is committed.

| Case | Actual result |
|---|---|
| No-op | Exact input bytes after export/reopen |
| Sword quality 8→9 | One quality field changed; current durability unchanged |
| Individual sword repair | One durability field, 715→750 |
| Repair All | Exactly 10 durability fields changed; 23 skipped; over-maximum 1600 retained |
| Canceled plan | No application; export remains byte-identical |
| Every exported case | SHA-512, parse/serialize and on-disk reopen pass |

Each case starts from baseline. A byte comparison of every item against an
expected copy permits only the intended field; unrelated items remain exact.
Prefix/suffix/head/middle/tail and raw skills remain exact, protecting opaque
character records, counters, upgrade seeds and cheat history. Existing item
flags, crafter fields and custom data remain unchanged. No new cheat metadata
was introduced. Original and experimental input remain byte-identical.

Independent cross-check: pinned reference decoder `09a72ad03ae17955605cc392b4be43e95aec88a7`
was used read-only to decode each ULF export and compare complete profile/player
structures. Only expected quality/durability paths differ. Its writer was not
used; its dictionary normalization is not proof of raw preservation, hence the
separate exact byte checks. Local `validate.py` and `results.json` retain the
reproduction details. Cancellation here means discarding an unapplied plan;
actual dialog cancellation is covered by offscreen regression, not native input.

## Native Windows evidence and limitation

The actual PySide6 application was launched on Windows, including a launch with
the disposable input path. Windows accessibility inspection verified the Alpha
0.3.1 label, SHA-512/byte-exact status, 33 items/48 slots, all four requested
names, selected sword, enabled Repair/Repair All/Review controls, and durability
meter value 953 (95.3%). This is actual application evidence, not a mocked run.

However, desktop capture failed with `FrameArrived timed out` and `window capture
timed out`; an input attempt reported `coordinate input geometry is unavailable`.
A keyboard Open attempt produced no observable chooser. Retrying with a visible
interactive launch did not restore capture. Consequently **visual inventory
rendering, armor selection, quality editing, individual Repair, bulk preview,
Review and Save As through native input are not signed off**. Their offscreen
regressions and core exports passed, but those do not substitute for native
usability. No observed exception establishes an application defect; capture
errors are tool failures. Accessibility also exposes custom numeric spinners
as value zero; actual value announcement needs manual verification (FR-073).

## Research review and deferred work

Reviewed all three Viking documents at research commit `5e2bcac`, plus the
expansion plan, scaling research and Alpha 0.3/0.3.1 reports. No ordinary catalog
gap or new ULF serialization incompatibility is demonstrated by that evidence.
Reference desktop decimal drift/checksum-warning behavior and web bulk-repair
extra reduction are guarded against by ULF's retained protections and tests.
Current v34 counters/seeds remain opaque and byte-preserved. No reference code
or dataset was imported and the research commit remains separate.

Undo/redo, optional artwork, fill/duplicate/replace, movement/equipment rules,
appearance, foods/vitals, knowledge and mod overlays are future scoped work,
not fixes authorized here. General undo/recovery and native accessibility remain
incomplete baseline desktop-polish requirements; this validation does not mark
the entire original 0.3 roadmap complete. Skill XP policy is unchanged.

## Requirement status and decision

- Implemented/tested within current scope: FR-002–005/010–016/018/030–033,
  FR-040–044/050–054/056/060, FR-072; NFR-005. Evidence has the boundaries above.
- Partially verified: FR-001/006/017/057/070–073 (native load/accessibility only);
  FR-096 (one sample); FR-098 and NFR-002/003 (offline regression exists, native
  Linux/offline platform matrix not performed); FR-063 (procedure, no game result).
- Outstanding before full release: owner gameplay/resave, native interaction
  and visual matrix, Linux validation, and distribution/license gate FR-035 /
  NFR-008. This task does not provide new legal clearance.
- Unimplemented by this work: general undo/recovery and post-MVP features;
  broader existing requirement gaps are not silently waived.

No confirmed code blocker requires a production fix. Native usability and
gameplay evidence are insufficient to recommend unconditional merge. Complete
the checklist, resolve failures, and obtain explicit owner approval for any
merge or release. Validation changes are limited to tests and these documents;
the completion message records their final commit and synchronization status.
