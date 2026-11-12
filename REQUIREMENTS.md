# ULF Editor — Product & Engineering Requirements

> **Status:** Approved for MVP development · **Baseline version:** 1.0 · **Date:** 2026-11-11  
> **Repository:** `LoneWolf862/ULF-Editor` · **Current product:** Python / PySide6 desktop  
> **Authority:** This document is the authoritative product specification. `AGENTS.md` governs coding-agent behavior. Code and tests are implementation evidence. Proposed decisions and TBDs require resolution before affected behavior is implemented.

## 1. Vision and purpose

ULF Editor is a locally controlled Valheim character-save workshop for inspecting and editing `.fch` saves. It combines the usability and visual polish that inspired the project (Viking Editor) with original, subtle wolf/Ulf/Norse styling. It begins as a cross-platform Python desktop application, with a potential web edition only after the desktop application is proven and feature-complete. No web implementation is planned during the desktop MVP or immediate desktop releases.

**Primary user outcome:** open a character, understand its inventory and skills, safely change item quality (including unusually high levels), stack amounts, inventory contents, and skill levels, and export a valid save copy without using in-game developer commands.

**Non-goal / no guarantee:** ULF must not promise that edits are invisible to Valheim, its achievement system, a server, or mods. Save integrity, cheat-tag preservation, and achievement eligibility are different concepts. ULF must not silently scrub or falsify existing character or world cheat history.

## 2. Scope and release boundaries

| Release | Goal | Acceptance gate |
|---|---|---|
| **0.1.1 Stabilization** | Make existing Python core and editing behavior reliable. | Regression suite passes; transactional edits; safe export/verify; format/version safeguards; reproducible synthetic fixtures. |
| **0.2 MVP usability & catalog** | Make daily item editing intuitive and complete. | Searchable comprehensive vanilla catalog, exact preservation of unknown items, an 8-column inventory grid, clear editing forms, synchronized skill sliders and numeric controls, and clear error reporting. Export uses Save As and protects the original. |
| **0.3 Desktop polish** | Improve the main desktop workflows before adding secondary character systems. | Polished layouts, optional licensed item artwork, undo/redo, keyboard navigation, backups/recovery, and clear change review. |
| **1.0 Desktop** | Stable Windows 10/Linux release. | Installers or documented distribution; full test matrix; documentation; in-game validation on disposable saves. |
| **Post-MVP expansions** | Equipment management, inventory organization, appearance, unlocks, presets, modded-item support. | Scheduled separately after core MVP acceptance; each receives its own requirements and tests. |
| **Web (deferred / optional)** | Consider browser implementation only if owner elects to pursue it. | No implementation work or web infrastructure in current roadmap; revisit after desktop maturity. |

Features may be pulled forward when safe, but no release is declared complete without its acceptance gate.

## 3. Users and workflows

### 3.1 Primary workflows

1. **Inspect:** Choose a `.fch`, validate it, view character identity and important version metadata, then browse inventory and skills without modifying it.
2. **Upgrade:** Select an item, change its quality (including above vanilla maxima), preview the change, and export a new save.
3. **Change stack:** Select an existing item, change quantity, understand game/catalog limits, and export.
4. **Add item:** Search a valid prefab, choose an available slot and supported properties, add it, and export.
5. **Edit skills:** Adjust a skill's level and optionally its progress/experience; apply changes together and export.
6. **Recover:** If load, validation, or export fails, retain the original unchanged and show a useful diagnosis.

### 3.2 Future workflows

After MVP: dedicated equipment management, inventory organization (sorting and drag/drop), character appearance editing, recipe/progression unlock editing, skill presets and bulk actions, advanced modded-item support, item comparisons, and optional sanitized reports. These are **planned post-MVP candidates**, not part of MVP acceptance. Web development remains optional and explicitly deferred.

## 4. Functional requirements

IDs use `FR-xxx`. Priority: **P0** required for stable core, **P1** planned for desktop product, **P2** later/optional.

### 4.1 File loading, integrity and identity

| ID | Priority | Requirement | Verifiable acceptance |
|---|---|---|---|
| FR-001 | P0 | Open `.fch` from a user-selected local path; do not modify input on open. | Input hashes unchanged after open/close. |
| FR-002 | P0 | Verify framing, lengths, and SHA-512 according to supported format before editing. | Invalid/truncated/checksum-failed files fail safely with diagnostics. |
| FR-003 | P0 | Only permit edits on fully understood/supported profile, player and inventory/skills layouts. | Unsupported versions are read-only or rejected with explicit reason. |
| FR-004 | P0 | Require byte-for-byte parse→serialize round-trip for untouched input before enabling export. | Untouched output equals input exactly. |
| FR-005 | P0 | Preserve all unrelated records/bytes (worlds, map data, recipes, appearance, statistics, custom data). | Synthetic fixture diff shows only intended fields plus necessary framing/hash changes. |
| FR-006 | P1 | Display relevant character metadata, supported versions, and checksum/round-trip status. | UI status reflects actual engine results. |
| FR-007 | P1 | Recognize game-save format changes and explain compatibility rather than attempting unsafe best guesses. | Tests cover representative rejected versions. |

### 4.2 Inventory model and editing

| ID | Priority | Requirement | Verifiable acceptance |
|---|---|---|---|
| FR-010 | P0 | Decode all existing inventory records, including unknown prefab hashes and custom metadata, losslessly. | Unknown entries round-trip exactly. |
| FR-011 | P0 | Modify quality using range validated for detected inventory format. Support high levels permitted by serialization, but warn about possible gameplay instability and vanilla item limits. | Quality 1, high legal value, and invalid bounds tested; no integer overflow. |
| FR-012 | P0 | Enforce each identified item’s **game-defined maximum stack size** for quantity edits and item creation, as well as format bounds; never allow stack overflow via the ordinary UI or export. | 1 and item max accepted; 0, negatives, max+1 and overflow rejected with clear errors. |
| FR-013 | P0 | Add catalog-resolved items with prefab identifier/hash, unique unoccupied slot, appropriate defaults, and per-item maximum stack enforcement. | New item loads and exports correctly; collisions and oversize stacks rejected. |
| FR-014 | P0 | Remove items only after explicit selection; retain ability to cancel before export. | Deleted item absent only from new output; original unchanged. |
| FR-015 | P0 | Preserve equipped, picked-up, crafter, variant, world-level, custom data and trailing flags on unrelated items. | Before/after metadata equal for unaffected records. |
| FR-016 | P0 | Never silently set or clear existing per-item cheated flags; newly created item flag behavior is explicit and documented. | Flag-preservation tests pass; new-item fields inspected. |
| FR-017 | P0 usability | Display inventory in game-like 8-column slots; represent varying grid heights without losing records. | Occupied cells display consistently; no overlap or silent truncation. |
| FR-018 | P1 | Edit durability with range/precision safeguards; show raw and friendly values where necessary. | Round-trip comparisons account for format precision. |
| FR-019 | Post-MVP | Move, swap, and drag/drop inventory slots transactionally as part of FR-091. | Conflicts resolved only via explicit swap/move, with no duplicate coordinates. |
| FR-020 | P1 | Show original/current value and pending changes for all edited items; support undo/redo. | Undo restores serialized-equivalent state. |
| FR-021 | P2 | Bulk item edits and presets. | Defined when scheduled. |

### 4.3 Catalogs and unknown items

| ID | Priority | Requirement | Verifiable acceptance |
|---|---|---|---|
| FR-030 | P0 | Maintain a **comprehensive versioned vanilla item catalog** mapping prefab names to stable hashes, display labels, and authoritative maximum stack sizes, including items from supported current game content. | Stable-hash vectors pass; known vanilla fixture hashes resolve, and limits are present for editable stacks. |
| FR-031 | P0 | Validate new prefab selections against catalog, or an explicitly enabled advanced custom-prefab workflow. | Misspelled names rejected by default; advanced cases visibly marked unverified. |
| FR-032 | P0 | Preserve unrecognized inventory records byte-for-byte and show the unknown hash and diagnostic context. The sole exception is an explicit quantity edit backed by a verified maximum stack size for that item. Preserve every other field and reject quantity edits without that verification. | Unknown records remain byte-identical across unrelated edits. A verified quantity edit changes only quantity and its necessary encoding. Unverified quantity edits are rejected. |
| FR-033 | P0 usability | Search/filter by localized name and prefab identifier; show category, **maximum stack**, maximum known quality, and catalog version/source. | Typical vanilla items can be found by friendly name; max-stack feedback is visible during edits. |
| FR-034 | P1 | Permit optional local catalog overlays for modded prefabs without making remote requests mandatory. | Overlay imports are validated and do not overwrite base catalog silently. |
| FR-035 | P1 | Attribute third-party data and obey applicable licenses; never assume images/code can be copied from Viking Editor. | Distribution includes attribution/license records. |

### 4.4 Skills

| ID | Priority | Requirement | Verifiable acceptance |
|---|---|---|---|
| FR-040 | P0 | Decode known and unknown skill IDs without data loss. | Unknown IDs round-trip. |
| FR-041 | P0 | Edit skill levels within valid game/format bounds, normally 0–100; reject non-finite values. | 0, 100, negatives, NaN, infinity covered. |
| FR-042 | P0 | Support saved progress/experience accumulator when format supports it; define reset/preservation policy explicitly. | UI and serialized accumulator match chosen policy. |
| FR-043 | P0 | Validate a complete proposed set of skill edits before applying any changes. | One invalid row leaves all prior state untouched. |
| FR-044 | P0 usability | Provide **per-skill sliders (normally 0–100) paired with synchronized numeric entry**, visible level/progress, and a pending-change summary. Controls must be intuitive without spreadsheet-style cell editing. | Slider↔number updates bidirectionally; keyboard operation, exact values, and staged edits work without accidental partial writes. |
| FR-045 | P2 | Bulk skill operations (e.g., all to target level) with confirmation/undo. | Defined when scheduled. |

### 4.5 Export, backups, and change auditing

| ID | Priority | Requirement | Verifiable acceptance |
|---|---|---|---|
| FR-050 | P0 | Export via **Save As** to a separate file. Overwriting the original character save is prohibited, including through another path that identifies the source file. | Source digest remains identical and attempts to export to the source or an alias are rejected. |
| FR-051 | P0 | Serialize in memory, validate structure/checksum, write to temporary file, flush/close, re-read and re-parse from disk, then atomically rename/replace the **target** when possible. | Failed validation never leaves a successful-looking output. |
| FR-052 | P0 | Report exactly why export fails and clean up temporary files. | Fault-injection tests for failed write/rename/checksum. |
| FR-053 | P0 | Verify exported inventory/skill values and preservation of unrelated records and existing cheat metadata against intended edits. | Automated before/after semantic check passes. |
| FR-054 | P1 | Preview changes before export and identify potentially non-vanilla values (high quality/stack). | All modified fields shown in review. |
| FR-055 | Superseded | Retired advanced overwrite proposal. FR-050 governs exports. | Excluded from MVP acceptance. Separate-file backup and recovery remain desktop polish work. |
| FR-056 | P1 | Detect externally modified source file before export and require reload/confirmation. | Changed input does not export silently from stale state. |
| FR-057 | P1 | Show export destination and post-write validation status. | UI displays actual path and verified result. |

### 4.6 Achievement/cheat-state handling

| ID | Priority | Requirement | Verifiable acceptance |
|---|---|---|---|
| FR-060 | P0 | Treat existing character cheat records, known command history, counters, and per-item cheated flags as protected, unmodified metadata during ordinary editing. | Byte/semantic comparisons confirm preservation. |
| FR-061 | P0 | Do not call in-game developer commands, perform runtime patches, or claim automatic achievement eligibility. | Product text and implementation audited. |
| FR-062 | P1 | Display existing cheat-related metadata read-only where format is understood, with uncertainty clearly described. | Status is factual and does not claim future eligibility. |
| FR-063 | P1 | Document that achievement outcome may also depend on world state, mods, game version and server behavior; in-game eligibility must be tested separately with disposable saves. | Docs/test plan include end-to-end test. |

### 4.7 Desktop UI and accessibility

| ID | Priority | Requirement | Verifiable acceptance |
|---|---|---|---|
| FR-070 | P1 | Use PySide6 with coherent dark Norse/wolf styling: readable text, restrained bronze accents, original art, clear affordances. | Design review on Windows and Linux. |
| FR-071 | P0 usability | Provide clear, beginner-friendly navigation for Character, Inventory, Skills, and Export/Review, plus prominent status/error feedback. | Key tasks complete without editing raw JSON. |
| FR-072 | P1 | Prevent UI controls from directly mutating core objects until validation succeeds; maintain a staged edit model. | Invalid UI action is atomic. |
| FR-073 | P1 | Maintain keyboard navigation, readable focus indicators, scalable layouts, and practical high-DPI support. | Manual accessibility checklist passes. |
| FR-074 | P1 | Keep heavy file operations off UI thread or provide progress/cancel where necessary. | UI remains responsive on representative large saves. |
| FR-075 | P2 | Item icons, tooltips, equipment slots and theme customization; require rights to included assets. | Defined when scheduled. |

### 4.8 Post-MVP expansion backlog (not required for initial release)

| ID | Priority | Proposed capability | Acceptance planning note |
|---|---|---|---|
| FR-090 | Post-MVP | Equipment panel showing worn gear, equipped states, and supported slot management. | Define equipment-specific game invariants before implementation. |
| FR-091 | Post-MVP | Inventory organization: sorting, movement/swapping, drag-and-drop, safe conflict handling. | No lost items or duplicated occupied slots. |
| FR-092 | Post-MVP | Appearance editing (hair, beard, character colors/model where supported). | Preserve unedited appearance fields. |
| FR-093 | Post-MVP | Recipe, material and progression unlock editing. | Document save fields and verify game behavior on test character. |
| FR-094 | Post-MVP | Skill presets and bulk operations with previews, confirmations, and undo. | No partially applied preset. |
| FR-095 | Post-MVP | Advanced modded-item support using local catalog overlays and optional per-mod metadata. | Never assume unknown prefab hashes are vanilla; preserve unknown records. |

### 4.9 Vanilla save compatibility and diagnostics

**Available local test material:** The owner reports **two vanilla `.fch` saves in the local project environment**, including one previously showing unidentified items. Their exact paths are not part of this document and should be discovered by the local coding agent, without guessing. Do not commit, upload, or copy the saves into the repository.

| ID | Priority | Requirement | Verifiable acceptance |
|---|---|---|---|
| FR-096 | P0 | Investigate both owner-provided vanilla saves **read-only** to identify unrecognized prefab hashes and diagnose catalog gaps vs parser bugs. | Local diagnostic counts and hashes are reported without disclosing personal character data. |
| FR-097 | P0 | Expand the bundled, versioned catalog to resolve all verifiably vanilla items found in the two saves where reliable names and limits exist. | All identified vanilla hashes match the official/current prefab reference or a reviewed source; unresolved entries are listed honestly. |
| FR-098 | P0 | Make catalog metadata available offline on both Windows and Linux. | With network disabled, all known supported prefab names and stack limits remain available. |

### 4.10 Web portability (later)

| ID | Priority | Requirement | Verifiable acceptance |
|---|---|---|---|
| FR-080 | P0 architectural | Core save logic must remain UI-independent as a general maintainability requirement; **no active work toward a web port**. | Headless unit tests run without Qt. |
| FR-081 | Deferred optional | Only if approved later, choose browser-local engine (TypeScript/WASM) vs Python API using explicit privacy, maintenance and deployment evaluation. | Architecture decision record approved. |
| FR-082 | Deferred optional | If a web edition is approved, default to local browser processing where practical; no silent upload of character saves. | Network inspection and privacy tests pass. |
| FR-083 | Deferred optional | Self-hostable static frontend preferred if browser-local format engine is achieved. | Documented Nginx deployment. |

## 5. Nonfunctional requirements

- **NFR-001 Reliability (P0):** No source corruption or unverified success messages; fail closed on ambiguity.
- **NFR-002 Portability (P0):** Python 3.12 baseline; fully local Windows 10 and Linux desktop support; no hard-coded user paths; release instructions tested on both platforms.
- **NFR-003 Privacy and offline use (P0):** The packaged Windows and Linux app must work fully offline for all MVP functions, including catalog lookup, load, edit, and export; no sign-in, network dependency, telemetry, or uploading saves. No real saves in the repository.
- **NFR-004 Maintainability (P0):** Engine, domain edit operations, catalogs, UI, and export/validation boundaries separated; clear type hints/docstrings for binary formats.
- **NFR-005 Testability (P0):** Automated tests work headlessly with synthetic fixtures; compatibility checks for future format versions.
- **NFR-006 Performance (P1):** Representative character loads and exports should feel interactive; define numeric benchmark after collecting sample sizes (**TBD**).
- **NFR-007 Security (P0):** Untrusted save inputs are bounded (length/count/string-size limits), never executed; no arbitrary shell commands derived from file content.
- **NFR-008 Licensing (P0):** Audit origin/licenses of parser code, catalogs, game artwork, and dependencies before public distribution.
- **NFR-009 Observability (P1):** Structured diagnostic messages with no sensitive save contents by default; optional redacted debug report.
- **NFR-010 Reproducibility (P1):** Pinned/controlled dependency versions, documented setup, CI tests, release artifacts with version identifiers.

## 6. Domain and validation rules

1. **Source is immutable.** Editing applies to staged changes in memory. Save As exports to a separate file.
2. **No-op save is byte-identical.** Re-serialization must reproduce a supported untouched input, including preservation of raw tails/metadata.
3. **Catalog limits versus binary limits:** Quality may be intentionally nonstandard (warn); **stack overflow is forbidden (error)**. Distinguish errors from warnings clearly.
4. **Quality:** For inventory v109, storage uses an optional `uint16` (when quality ≠ 1). UI must not silently truncate; cap is format-dependent, not a promise of game behavior.
5. **Quantity:** For inventory v109, storage uses an optional `uint16` (when stack ≠ 1). **Never exceed the game-defined maximum stack per prefab**, even if the binary field can represent more. If a catalog max is absent or uncertain, disable quantity editing/creation for that prefab until validated metadata is available; preserve existing data as-is rather than silently clamp it.
6. **Unknown prefabs:** Preserve existing unknown records exactly. The only permitted change is an explicit quantity edit with a verified maximum stack size for that item. Adding unverified custom prefabs is outside MVP scope.
7. **Skills:** Reject NaN/infinity and invalid ranges; never partially apply an edit batch.
8. **Position:** Every item in a normal inventory must have a valid, unique `(x, y)` slot for the selected grid representation; do not silently relocate items on load.
9. **Cheat metadata:** Preserve as found; do not mislabel a checksum-valid file as guaranteed achievement-safe.
10. **Validation:** Disk read-back and semantic verification are necessary before claiming successful export.

## 7. Proposed architecture

```text
ULF-Editor/
  AGENTS.md                  # coding-agent instructions
  REQUIREMENTS.md            # product contract (this file)
  core/
    fch.py                   # current binary implementation (to refactor as warranted)
    catalog.json             # versioned prefabs, later expanded
    ...                      # future: domain, validators, file IO, catalogs
  desktop/
    app.py                   # PySide6 frontend
    ...                      # future: inventory, skills, dialogs, themes
  tests/
    test_fch.py
    fixtures/                # synthetic, non-personal fixtures only
  docs/
    ...                      # format notes, design decisions, test plan
  run.py
  requirements.txt
```

Suggested layers: `format parser/writer` → `domain model and edit transactions` → `validation/export service` → `desktop UI`. The eventual web client must talk to domain functions, never manipulate raw parser objects directly.

## 8. Testing and acceptance strategy

### 8.1 Automated tests required for 0.1.1

- Known stable-hash vectors and signed integer conversions.
- Valid file parsing; bad checksums; malformed lengths; truncated data; hostile count/size inputs.
- Untouched byte-identical round-trip for synthetic versioned fixtures.
- Quality/stack boundaries and malformed input handling, including different catalog max stacks, zero/negative quantities, and max+1 rejection.
- Unknown item and custom-data preservation; item flag preservation; unidentified vanilla items from two owner-provided files tracked as compatibility cases.
- Inventory add/remove with slot collision and bound checks.
- Atomic skill edits, including a valid row followed by an invalid one.
- Export write-to-temp, read-back, digest/semantic validation, cleanup on failure.
- Unrelated data and cheat metadata unchanged after edits.
- Explicit rejection of unsupported versions, with readable errors.

### 8.2 Manual desktop tests required before 1.0

- Windows 10 and Linux with Python 3.12/PySide6, **fully offline**, including item catalog, editing, and export.
- Load a disposable character; edit each of four primary features; export/reopen; launch game with **copy**, not main save.
- Verify item behavior and skill state inside Valheim.
- Check achievement eligibility separately using controlled test accounts/characters/worlds; document version and observed outcome, not absolute claims.
- DPI scaling, keyboard focus, skill slider/numeric synchronization, catalog lookup, modded/unknown entries, failures and recovery.

### 8.3 Definition of done (each feature)

Code reviewed; unit/regression coverage; error paths documented; UI prevents accidental loss; tests pass; user-visible behavior documented; no real save data committed; Git diff limited to intended files; no push/merge without owner approval.

## 9. Development and governance

- `main` remains stable. Larger work on branches; feature changes should be small and independently reviewable.
- Codex may inspect, edit, and test in the selected local repository. Commits, pushes, and merges require explicit owner approval unless owner later changes policy.
- `AGENTS.md` must reference this document; when guidelines conflict, stop and request explicit owner decision rather than guessing.
- Changes to product scope require modifying requirements, acceptance criteria, and milestone plan in the same review.
- Track requirements IDs in issues/PRs and test names when practical.
- Keep an auditable changelog for releases and document file-format compatibility per version.

## 10. Explicitly out of scope for current MVP

- World `.db`/`.fwl` editing, world cheat-state modifications, or map editing.
- Runtime game hooking, console automation, cheat-state scrubbing, or achievement bypass tools.
- Multiplayer server synchronization, server loot-table tuning, and automated encounter drop generation (separate potential project).
- Cloud accounts, remote storage of saves, social sharing, or telemetry.
- Game-content artwork redistribution without permission.
- Exact cloning of Viking Editor proprietary code, layouts, trademarks, or assets.

## 11. Owner decisions and proposed defaults

| Decision | Proposed default | Why it matters |
|---|---|---|
| **D-01: Above-normal stacks — DECIDED** | **Never allow an item stack to exceed its verified game-defined maximum. No overflow toggle.** Unknown max disables quantity editing until metadata is available. | Owner explicitly prioritizes preventing invalid stacks. |
| **D-02: High quality** | Permit any legal format value, warn above catalog maximum; no claim game supports extreme values. | High upgrades are core product value. |
| **D-03: Skill experience** | Changing level resets accumulator to zero unless user explicitly sets progress. | Avoid confusing mixed level/progress states. |
| **D-04: Existing unknown/modded items — DECIDED** | Preserve unknown records exactly. Permit only explicit quantity changes supported by a verified maximum stack size. | Protect unknown fields and prevent destructive catalog assumptions. |
| **D-05: Adding custom prefab IDs** | Catalog-only by default, advanced override later with warning. | Avoid generating invalid items. |
| **D-06: Source overwrite — DECIDED** | MVP exports use Save As. Overwriting the original character save is prohibited. | Protect valuable character saves. |
| **D-07: Achievement UX** | Read-only state inspection/warnings; no cheat scrubbing; no eligibility guarantee. | Keep accurate and safe behavior. |
| **D-08: Game version support** | Support formats proven by tests, initially v46 profile/v33 player/v109 inventory; extend only with fixtures. | Avoid false compatibility claims. |
| **D-09: Catalog strategy** | Versioned bundled base catalog + optional user overlays; license review before import. | Modded support and compliance. |
| **D-10: Web processing — DEFERRED** | **No web implementation now.** Revisit only if owner chooses after local Windows/Linux desktop MVP is working and polished. | Web is optional, not a current deliverable. |
| **D-11: MVP usability and inventory scope — DECIDED** | Basic inventory usability (FR-017, FR-033, FR-071) and skill sliders with numeric entry (FR-044) are MVP. Advanced sorting, drag-and-drop, movement/swapping and equipment management (FR-019, FR-090–091) are post-MVP. | Keep the core desktop editing workflow usable and the MVP scope focused. |

## 12. Traceability and immediate next work

Start with stabilization on a feature branch when implementation is authorized. Use the two local vanilla saves for **read-only** catalog diagnostics and keep them out of Git. Prioritize FR-001–005, FR-010–016, FR-030–032, FR-040–043, FR-050–053, FR-060–061, NFR-001/003/005/007 and their tests. Keep the full visual redesign out of stabilization.

Approval covers MVP development and the decisions marked decided above. Treat remaining proposed defaults as open where they affect behavior. Refer to [the gap analysis](docs/MVP_GAP_ANALYSIS.md) for evidence and implementation sequencing.
