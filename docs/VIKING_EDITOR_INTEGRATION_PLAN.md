# Viking Editor findings: proposed ULF integration plan

Date: 2026-11-13. Baseline: Alpha 0.3.1 at `fac8e1b7ba941ff56a2a300e7e374ca48a3fd91c`. **Proposal only: no feature implementation, requirement changes or Alpha 0.4 work is authorized by this document.** [REQUIREMENTS.md](../REQUIREMENTS.md) remains authoritative. See [reference comparison](VIKING_EDITOR_REFERENCE.md) and [controlled evidence](VIKING_EDITOR_EXPERIMENTS.md).

## Recommended direction

Keep ULF's independent Python/PySide6 architecture, original Norse/Wolf visual identity, offline catalogs and strict Save As verification. Learn from the web editor's discoverable quick actions, unified undo and grouped knowledge tools. Learn from the desktop source's optional local sprite extraction and mod-storage diagnostics. Do not replace ULF's parser, item-stat service or audited catalog with either reference implementation.

The catalog investigation found **no missing ordinary candidate** relative to the web snapshot: all 927 candidates, all shared stack limits and 288 applicable durability definitions agree. Work should focus on provenance, clear diagnostic categories, desktop polish and separately scoped workflows rather than inflating the catalog count. ULF already goes further than the inspected references in applicable damage/armor/block/deflection/parry/movement calculations and original-file protection.

## Proposed sequence and measurable gates

| Order | Proposed slice | Requirement IDs | Acceptance criteria before completion |
|---|---|---|---|
| 0 | Close remaining desktop/MVP acceptance | FR-001–007, FR-010–017, FR-030–033, FR-040–044, FR-050–054, FR-060–063; NFR-001–005 | Existing99 tests remain green; native Windows/Linux offline open/edit/Save As checklist; disposable in-game reload; source/alias rejection; no unknown-record changes; documented distribution/license review. Existing tests do not replace native/game acceptance. |
| 1 | General undo/redo and consistent change review | FR-020/054/071–073; NFR-004/005 | Undo of any supported command restores serialized-equivalent prior state; redo reproduces it; invalid command adds no history; redo clears after a divergent edit; dirty/export revision markers reflect actual state; grouped bulk action is one history entry. Test add/delete/replacement dependencies and active form drafts. |
| 2 | Keyboard/accessibility and quick-action polish | FR-017/033/044/070/071/073/074 | Every input has a meaningful accessible name; focus remains on a valid target after add/delete; arrow selection/Delete shortcuts have documented, safe equivalents; ordinary desktop/DPI matrix; no hidden pending drafts; large-list search does not block the UI. Keep original styling. |
| 3 | Catalog/stat provenance and optional local artwork | FR-030/033–035/075/098; NFR-003/008/010 | Keep 927 verified candidate coverage; separately report identity/limits/stat availability; show build/source per calculation; no remote dependency; optional extraction failure leaves old cache usable; no game artwork distributed without rights review. |
| 4 | Post-MVP fill, duplication, atomic replacement | FR-012–016/019–021/054/072/091 | Each command has a complete before/after proposal; verified limits only; occupied/ambiguous slots rejected; retained records byte-preserved; new-item flag policy applied; undo round-trips; no partial batch on error. Replacement explicitly previews durability or equipment side effects. |
| 5 | Post-MVP movement/swap and equipment | FR-019/090/091 | First implement domain and keyboard commands; then drag/drop as a UI adapter. Unique coordinates, no dropped/duplicated records, explicit swap/merge policy, full preview of auto-unequips, unsupported mod slots read-only. Verify real game invariants before claiming equipment validity. |
| 6 | Appearance and identity proposal | FR-005/015/060/092; NFR-005/007 | Versioned typed fields, raw preservation of untouched strings/RGB, unknown style tokens retained, finite float bounds, successful no-op and field-specific fixtures, disposable game validation. Name edits must account for possible game upgrade-seed/name relationships; do not change stored seeds. |
| 7 | Powers, vitals and foods proposal | FR-003–005/053/060 plus new owner-approved scope | Verify current/max field locations and game formulas. A single food action previews every affected maximum/current value; unknown food data is preserved rather than guessed; float32/quantization fixtures and in-game resave pass. Existing requirements do not fully specify these editing policies. |
| 8 | Knowledge/progression editor | FR-005/093; NFR-004/005 | Separate recipes, materials, stations, pieces, biomes, tutorials, texts and keys; preserve unknown entries/order/duplicates; use exact serialized tokens/localized values; preview dependencies; one unlock does not silently unlock unrelated data; disposable game validation. |
| 9 | Bulk skills/presets and mod overlays | FR-034/040–045/094/095 | Explicit XP policy; finite level/XP validation; atomic preview/undo; unknown skills unchanged; data-only overlays with build/mod identity and collision handling; no overlay automatically acquires verified write authority. |

Do not label stages as completed releases until their approved acceptance gates pass. [FEATURE_EXPANSION_PLAN.md](FEATURE_EXPANSION_PLAN.md) remains useful for proposed scope, but its earlier version/catalog gaps are superseded by completed Alpha 0.2.1/0.3.1 evidence. The above order preserves D-11: advanced organization/equipment stay post-MVP.

## Architecture changes worth proposing

### Reusable edit proposals and history

Extend the existing domain transaction/session design rather than mutating parser objects from widgets. A command should contain stable record identity, expected revision, validated requested changes, the complete derived effects, original raw values and a human-readable summary. Validate on a private candidate, then publish atomically. The existing repair-plan revision checks are a useful starting point.

Keep form drafts, applied working state, original input and last validated export as distinct states. Undo should restore bytes/identity and update selection without silently applying an unfinished form. Export must still run the full validation service regardless of history state. Do not use direct deep-copy snapshots as a substitute for explaining side effects, and do not couple command objects to Qt.

Specific regression gates prompted by this investigation:

- A repair-all label/count must equal the number of changed records, including any permitted reductions. Require an explicit policy for over-maximum current durability; preserve the existing ULF preview behavior until that policy is approved.
- Replacement must list old/new prefab, current/maximum durability, stack, quality and equipped effects. The web experiment's715→550 clamp is evidence of a side effect, not authorization for ULF to clamp silently.
- Duplicate must use an unoccupied legal slot, preserve the original, and explicitly define crafter/custom/cheat metadata handling. Do not copy another application's new-record flags by assumption.
- Bulk fill must reject unknown maxima; never use65535 or9999 as a game stack limit.

### Typed access without losing raw data

Future character editors should add versioned views into currently protected player sections. Retain the original encoded span for each untouched field/record, including strings, optional-field presence, float bit patterns, ordered pairs and opaque tails. Expose targeted replacement functions with a strict allowlist of changed fields. Reject layouts that are not understood instead of inferring them from a game-version string.

Use lists of key/value records when the format can preserve order or duplicates; a Python dictionary is an application convenience, not a lossless wire model. Keep original item durability as integer hundredths and encode edits under the existing validated policy. The desktop no-op1092.10→1092.09 defect demonstrates why float reconstruction must not touch unrelated values.

Source framing/hash verification, byte-identical no-op gate, protected metadata checks, source-alias rejection, write-to-temp, disk reopen and verified target replacement remain mandatory. Do not adopt the desktop reference's warning-only checksum path or direct destination writes. Preserve v34 drop counters and item-upgrade seeds as protected data; future typed readers do not imply permission to edit them.

### Build-specific data services

Retain separate catalog identity/limits, applicability/stat coefficients, formula policy and presentation labels. A diagnostic should answer independently:

1. Is this hash mapped unambiguously to a verified prefab?
2. Which catalog fields are verified for this build?
3. Which statistics are applicable, verified and calculable with the available context?

“Not applicable” and “unknown” must differ. A missing label must not turn a known item into an unknown prefab; missing coefficients must not manufacture a maximum durability. Conversely, a known label cannot authorize stack edits. Preserve ULF's exclusion ledger for NPC attacks, placed objects, customization and internal entries. Website-only extra entries are audit leads, not automatic additions.

Extend current extraction only when a specific feature needs it: localized labels, variant/icon references, equipment slot/hand rules, customization definitions, recipes/stations and food coefficients. Each extension needs pinned installation/build/hash inputs, deterministic output, coverage/exclusion counts and independent field checks. Keep projectile, skill, status and positive-world-level context separate from basic item statistics. Never infer a true combat damage value from a raw item vector.

## Reuse and licensing decisions

| Candidate | Recommendation | Conditions |
|---|---|---|
| Web JS/parser/data/UI assets | **Do not import** | No reusable license established. Publicly delivered resources were inspected only. Independently implement behavior from requirements and verified facts. |
| Desktop GPLv3 parser | **Do not substitute** | Copyleft review would be required; no-op drift, canonicalization and checksum policy are incompatible with ULF safety guarantees without substantial work. |
| Desktop extraction/cache code | **Pattern reference; no code reuse proposed** | Content-addressed local icons, atomic cache replacement, variant fallback and progress/cancel are useful ideas. Any literal reuse needs GPL/project-license compatibility review and notices. |
| UnityPy extraction library | **Evaluate as optional development/local-extraction dependency** | Audit the pinned dependency license and transitive components; retain existing offline runtime independence. Library licensing does not grant rights to extracted game art. |
| Installed game numerical metadata | **Continue independent audit** | Keep assembly/assets local, pin versions and hashes, publish only reviewed minimum factual data with provenance and distribution review. |
| Valheim artwork/customization assets | **Optional local cache only pending rights decision** | No redistribution inferred from availability, fan-tool use or GPL code. Retain original fallback glyphs. |
| Jötunn / existing fch-decoder references | **Retain current attributed cross-check role** | Existing notices remain; older tables do not establish current eligibility or format support. |

Relevant source boundaries: [web legal notice](https://vikingeditor.com/imprint/), [desktop GPLv3 license](https://github.com/miskamero/VikingEditor/blob/09a72ad03ae17955605cc392b4be43e95aec88a7/LICENSE), [desktop trademark notice](https://github.com/miskamero/VikingEditor/blob/09a72ad03ae17955605cc392b4be43e95aec88a7/NOTICE), [UnityPy](https://github.com/K0lb3/UnityPy), and [existing ULF source review](ITEM_STAT_SCALING.md). This is a project reuse decision, not a legal opinion or permission grant.

## UX recommendations

Use a consistent inspector with adjacent maximum/current values and clear reasons for disabled actions. Keep original/current/pending values visible and accessible; distinguish error, warning and unavailable calculation. Adopt searchable categories, compact skill cards and dedicated future knowledge groups without reproducing another application's graphics or exact visual composition.

Do not copy the web editor's quality100 policy into ULF. FR-011 permits legal format values with caveats; current game methods do not establish100 as a universal runtime cap. Explain ordinary upgrade limits separately from representation limits and safe gameplay assumptions.

Make all pointer actions reachable by keyboard commands. For future drag/drop, call the same validated move/swap command as keyboard controls. Add accessible names to every spinbox, focus restoration and readable non-color indicators for equipped/dirty/error states. Retain ULF's explicit export review and post-write status; a successful download alone is not an in-game compatibility claim.

Future progression UI should show both known catalog entries and preserved unknown/legacy entries. Label raw serialized counts separately from filtered/category counts. Biome localization and recipe tokens should remain visible in an advanced diagnostic view without requiring users to edit raw JSON.

## Decisions that still require owner-approved feature scope

No decision is needed to complete this research. Before implementing the relevant future slice, settle:

- Food/vital derivation policy, including whether current values are clamped/refilled and which saved maxima change.
- Explicit skill XP semantics. The web editor rescales progress; ULF currently preserves XP unless explicitly edited. REQUIREMENTS D-03 is a proposed default, not authority to silently change current behavior. Decide policy and align requirements/tests before implementation.
- Duplicate/replacement metadata rules, over-maximum repair handling and equipment conflict policy.
- Artwork distribution model and any GPL component incorporation.
- Scope for character-name editing, custom metadata and mod overlays; no cheat-history removal or achievement guarantees.

Do not implement cloud accounts, telemetry, world editing, browser infrastructure or a web port from this comparison. FR-080 remains an engine-independence requirement; FR-081–083 remain deferred.

## Follow-up validation backlog

Prioritize synthetic raw-preservation fixtures for typed character fields, malformed/duplicate maps, explicit-default item flags and future-version rejection. Pair each new field editor with a one-action structural-diff test. Add disposable in-game acceptance for food maxima, equipment conflicts, locale-dependent knowledge and high-quality behavior. Verify optional extraction on Windows/Linux and failure/cancellation paths without requiring a game installation for normal ULF use.

Reference-tool follow-ups, if they become relevant to a scheduled feature: successful browser move/swap test, full network audit, direct-folder backup failure handling, mobile/accessibility matrix and released desktop binary tests. These are documented uncertainties, not reasons to postpone ULF's existing acceptance work.

## Research completion and requirement traceability

This assignment supplies evidence and proposed acceptance criteria for FR-003–005/007, FR-011–020, FR-030–035, FR-040–045, FR-050–054, FR-060–063, FR-070–075, FR-080, FR-090–098 and NFR-001/003–005/008–010. It does **not** mark unimplemented requirements complete. ULF's existing automated behaviors remain tested; native/game/distribution gates and the post-MVP features above remain outstanding as individually identified. Production code, requirements and source saves remain unchanged.
