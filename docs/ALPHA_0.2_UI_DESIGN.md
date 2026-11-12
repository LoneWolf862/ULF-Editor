# ULF Editor Alpha 0.2 UI/UX design

**Proposed for owner approval · 2026-11-12**  
[Review the offline desktop mockup](ALPHA_0.2_UI_MOCKUP.html)

## 1. Design goals and visual direction

Make the next action obvious from opening a save through exporting a verified copy. Keep the inventory spatial, the skills precise, and the difference between a draft, an applied edit, and an exported copy visible.

Use a charcoal canvas (`#151617`), stone panels (`#222426`), warm ivory text (`#F2E9DA`), and muted gray secondary text (`#BDB5A9`). Use bronze for borders and selection, muted gold (`#E3BB79`) for the main action, amber for warnings, sage for verified status, and salmon for errors. Use text and symbols alongside status colors. A small original wolf mark and a single runic detail establish the ULF identity. Keep surfaces behind text flat and reserve display serif type for the wordmark and character heading. Use the Qt system UI font for controls and tabular figures for values. FR-070–073.

The Alpha 0.1.1 gap analysis update is the current baseline. The PySide6 window still uses a fixed 8×6 table, an editable prefab combo, a skill table, and an export action that applies skill drafts implicitly. The redesign builds on the verified load, edit, and export services. FR-002–005, FR-017, FR-044, FR-050–053, FR-080.

## 2. Main window layout

| Region | Content and behavior |
|---|---|
| Header | ULF mark, character name, source filename, validation status, and edit status. Open Character and Review Changes are visible. A details affordance exposes the full path, detected section versions, SHA-512 and byte-exact round-trip outcomes, and supported cheat indicators with plain-language descriptions. |
| Navigation | Inventory, Skills, and Review. Show applied change count and flag tabs with unapplied drafts. Preserve selection and scroll position across tabs. Inventory opens first for a validated character. |
| Workspace | Inventory grid and contextual inspector, a scrollable skill list, or the review page. Each page has a single primary task. |
| Status | Show actionable progress or failure and the latest verified export destination when relevant. On launch, show an Open Character empty state. On a failed open, keep the prior session and explain the failed check. The CLI file argument uses the same load path and validation. |

**Open Character → Edit → Review → Export Save As.** Use “No pending changes”, “Unapplied edits”, “2 changes to export”, and “Export verified” as distinct states. If both kinds of pending edit exist, show both. Switching tabs preserves drafts. Opening another file or closing the window prompts when there are drafts or applied changes since the last verified export. Cancel keeps the session. A failed or canceled open keeps the prior session even after the user has elected to discard on successful open. FR-001–007, FR-057, FR-062, FR-071–074.

## 3. Inventory interface

- Use eight equal columns and a vertically scrolling grid. Use the existing six-row baseline for empty slots and extend the displayed height through the highest valid occupied row. The v109 row coordinate is a byte, so bound the view to 256 rows. Label row and column from one for display. Treat displayed extent as a way to inspect saved records. It does not establish additional writable capacity.
- An occupied tile shows a recognizable item silhouette or category glyph, quantity as **×18**, and quality as **Q4**. Show the item name within the tile where space permits and always in the accessible name and inspector. Empty tiles have recessed surfaces and accessible slot coordinates. Selected tiles use a bronze frame and a selection marker. Keyboard focus has its own visible ring. A pending removal remains identifiable in Review, and the corresponding grid cell becomes available after Apply.
- Invalid columns and duplicate coordinates appear in a visible **Inventory diagnostics** list with each record and its location. At duplicate cells, show a conflict marker and keep each record individually inspectable. Block editing of ambiguous records and surface the existing duplicate-position export block. Preserve the positions and records. Out-of-range columns remain inspectable via diagnostics.
- Select by click or arrows and open details with Enter. Tab moves between major controls. The inspector shows the chosen slot even when it is empty. At narrow widths, use a separate inspector page with Back to Inventory and restore focus to the originating slot. Sorting, movement, swapping, drag-and-drop and equipment management remain post-MVP. FR-010, FR-014–017, FR-019, FR-032, FR-071, FR-091.

## 4. Item editor

Show the name, prefab, category, slot, icon, and metadata provenance. Fields show applied values on entry. Record a draft only when a user changes a field. Apply Item validates the changed fields as one proposal and updates the in-memory working copy. Revert Draft restores that item's applied values. Switching slots preserves drafts by record identity. Remove uses the explicitly selected identity, names the item and slot in confirmation, and can be reversed before export through Review.

| Field | Control and validation |
|---|---|
| Quantity | Integer input with stepper and verified maximum beside it. Allow 1 through the lower of the verified maximum and 65,535. Show an inline error for invalid input. Display existing unusual values exactly and explain any existing validation block. |
| Quality | Integer input with stepper, 1–65,535 for v109. Show the known vanilla maximum and warn on valid edits above it. Use “Vanilla maximum unavailable” where the reference lacks a value. |
| Durability | Decimal input with up to two fractional digits and raw value in details. Validate exact hundredths against the existing domain limit for explicit edits. Preserve raw values on display and when editing other fields. |
| Equipped and protected fields | Preserve the existing equipped checkbox for verified records. Show understood cheat metadata read-only. Keep prefab, slot, flags, and other protected metadata under existing core rules. |
| Unknown records | Show hash, slot, stored values, and preservation status. Disable removal and every unverified edit. The requirements permit only an explicit quantity edit backed by a verified item maximum, with every other byte preserved. No current unknown-record verification path is assumed. |

The existing domain and export validators remain authoritative. They may block a known record with an existing oversized stack even during an unrelated change. Show the affected item and reason and preserve its current value until the user explicitly makes a valid correction. FR-010–016, FR-018, FR-032, FR-054, FR-060, FR-072.

## 5. Skill editor

Use stacked rows with skill name, applied level, a 0–100 slider, a labeled numeric field, and a draft marker with before/after values. Default to the known skill list. A known skill absent from the save can display level 0 and “No saved record” and is created only by an explicit accepted edit. List unknown IDs, duplicate records and unusual saved values as diagnostic rows. Duplicate and unknown records remain read-only. For a unique known skill with an unusual saved value, show its raw value and enable an explicit valid correction. Show **Experience** as a per-row disclosure with the saved accumulator, optional numeric edit and a preserve-by-default explanation. FR-040–044.

Use a 0.1 slider step with keyboard arrows and larger Page Up/Down steps. Numeric entry accepts finer finite values and displays applied values with enough significant digits to round-trip a float32. Numeric changes move the thumb to the nearest step without rounding the entry. Moving the slider explicitly selects its stepped value. Block feedback signals during synchronization, refresh, or disclosure. Field dirtiness comes from user edits and effective value changes. Recompute visible before/after at stored precision and submit only changed fields. Untouched XP retains its exact bytes, including unusual values. Show raw exceptional values with their status and leave the editable numeric input unset until the user explicitly enters a replacement. Proposed XP range follows the current validator, 0 inclusive to one billion exclusive.

**Apply Skill Changes** validates the entire draft batch together. A bad row leaves the working copy unchanged, retains all drafts, and directs focus to the first invalid input. **Discard Skill Drafts** resets drafts to the applied values. Propose removing the existing “Set all to 100” action from Alpha 0.2 in line with FR-045/094 scheduling. Retain level-only XP preservation from Alpha 0.1.1 and request explicit confirmation for Alpha 0.2 because D-03 remains proposed.

## 6. Item creation, catalog, and artwork

**Add Item** opens the offline catalog from Inventory. A selected empty slot pre-fills the target. Otherwise suggest the first eligible free slot and show it before confirmation. Search the localized display name and canonical prefab ID, with exact matches first and a category filter. Use the bundled English display names as the initial language, pending scope approval for additional catalog translations. Rows show item art or fallback, name, prefab, category, verified stack and known quality maximum. A details view shows catalog version and source. Provide no-match and no-free-slot states. Bind the add action to an explicitly selected catalog row. Invalidate selection when search results exclude it.

Choose a row, confirm an eligible slot, review defaults (quantity 1, quality 1, durability from the existing add path, equipped off), and adjust supported values. **Add to Inventory** stages one validated item. Recheck slot vacancy and stack maximum at Apply. Cancel preserves the working copy. Missing verified stack metadata disables creation and gives the reason. Keep verification provenance local and versioned, with hash collision checks. The 821-entry stabilization catalog is a starting point. Alpha 0.2 requires a reviewed manifest for the supported vanilla build, comparison against a versioned item reference, verified limits, and a documented explanation of coverage gaps. FR-012–013, FR-016, FR-030–035, FR-097–098.

| Resource | Proposed treatment |
|---|---|
| Valheim item sprites | Valheim ships item artwork in its icon atlas. Jötunn documents access to it and indexes sprite locations. Its prefab list provides names and English localizations for catalog research. The wiki's item-image index provides visual reference. Neither public visibility nor the modding tool's license establishes a redistribution grant for the underlying game art. [Jötunn GUI documentation](https://valheim-modding.github.io/Jotunn/tutorials/gui.html), [sprite list](https://valheim-modding.github.io/Jotunn/data/gui/sprite-list.html), [item list](https://valheim-modding.github.io/Jotunn/data/objects/item-list.html), [wiki image index](https://valheim.fandom.com/wiki/Category:Item_images). |
| Iron Gate guidance | The published modding statement describes the studio's position on mods. This review found no explicit permission there to bundle game sprites in ULF. Treat redistribution as uncleared. Exclude downloaded, extracted, hotlinked and copied game or Viking Editor artwork from the release unless the relevant rights holder grants suitable permission. [Iron Gate's modding statement](https://valheim.com/news/regarding-mods/). |
| Original and open icons | Start with original ULF item silhouettes for common items and category marks for weapons, tools, armor, food, materials and trophies. Use a neutral question-mark tile for unknown items. Lucide is a candidate for utility controls under its applicable license notices. Record asset creator, source, license, required attribution and modifications before bundling any third-party art. [Lucide license](https://github.com/lucide-icons/lucide/blob/main/LICENSE). |

Use one silhouette treatment and a consistent size and padding across the set. Resolve icons from bundled local resources by prefab, then category, then the generic fallback. Missing or unreadable artwork leaves the name, values, and actions usable. Treat a user-supplied local art pack as separate scope for approval. FR-035, FR-075, FR-098, NFR-003/008.

## 7. Change review and Save As

1. Draft fields are separate from the working copy. Apply updates that copy atomically. Review lists applied changes grouped by Inventory and Skills with original → applied values, slot and item or skill identity, additions, removals, and warnings. A replacement in one slot shows both affected records. An unapplied draft banner links back to its editor. Require users to apply or discard drafts before Save As.
2. **Discard Change** removes that proposed operation and revalidates dependent operations, such as a slot reused after removal. If a discard would invalidate another operation, identify both and offer to discard them together. **Discard All** confirms before restoring the loaded baseline. Keep validation failures distinct from advisory warnings. Generic history and undo/redo remain FR-020 polish.
3. **Export Save As** opens the native dialog with a suggested distinct `_ULF_edited.fch` filename and shows the selected path before publication. Confirm replacement of an existing eligible target through the native dialog. Delegate validation, alias checks, source-change detection, checksum and semantic verification, temporary-file read-back, and publication to `export_character`. Disable duplicate export while the operation is active.
4. On success, show the verified path and “Export verified”. Keep the source as the review baseline and record the exported working revision. Only new edits since that revision count as unsaved. On cancellation or failure retain applied edits and drafts. Keep the original unchanged, report the failing step and provide the next action, such as choosing a different path or reloading a changed source. A verified export indicates save integrity. Achievement eligibility remains unverified and is covered separately. FR-014, FR-050–054, FR-056–057, FR-060–063, NFR-001.

## 8. Component architecture

| Proposed boundary | Responsibility |
|---|---|
| PySide6 shell and session controller | Own navigation and lifecycle, source path, immutable loaded baseline, working revision, drafts by record/skill identity and exported revision. Expose read-only view models and accepted transaction results to widgets. |
| Inventory view and inspector | Qt model/view with a delegate for tiles, accessible names and row/column navigation. Inspector and catalog dialog emit explicit edit intents. |
| Skills view | Scrollable widgets with independent row state and synchronized controls. Send only the changed fields to a batch adapter. |
| Review model | Project differences by original record identity and skill ID. Preserve raw baseline records. Replay dependent commands from the baseline for discard, validating before replacing the working copy. |
| Catalog and icons | Build a deterministic offline metadata index. Keep icon selection independent of item identification and validation. |
| Load/edit/export adapters | Reuse `Character`, `apply_item`, `remove_item`, `apply_skills`, `Character.add`, and `export_character`. Run load/export on isolated snapshots in a worker and send results back on the Qt thread. Use progress and busy state. Keep a running publication indivisible. |

Keep `core/fch.py` serialization behavior outside the redesign. Two integration limits need owner agreement before the relevant implementation stage. `Character.add` currently rejects rows above six even if the view can display higher rows. The proposal keeps those rows inspection/edit-only for existing items and confines creation to eligible cells within the current domain bounds. If creation in higher rows is required, agree on reliable writable-height evidence and authorize a separately reviewed placement-rule change before offering it. Current unknown-record checks preserve the entire record and lack a verified-quantity exception path. Exposing that exception later requires a trusted verification source and matching domain/export validation that proves byte preservation outside quantity. FR-013, FR-017, FR-032, FR-072, FR-074, FR-080, NFR-004.

## 9. Accessibility and desktop usability

- Target 1366×768 and 1920×1080 at 100%, plus 150% and 200% scaling where the display can provide the required logical area. Test a compact 800×600 logical work area. Use two panes when an eight-column grid with minimum 44 logical-pixel targets and the inspector fit side by side. Collapse the inspector into its own scrollable page at narrower widths. Keep primary actions reachable through vertical scrolling or a pinned footer.
- Target text contrast of 4.5:1 and visible control/focus boundaries of 3:1 against adjacent surfaces. Use descriptive labels, shapes and states as well as color. Give each skill slider, numeric field, tile, alert and icon-only control an accessible name. Avoid tooltips as the sole place for required information. Announce validation failures and return focus to the triggering control after modal dismissal.
- Use native dialogs, a predictable tab order, arrow navigation within the grid, Enter for activation, Escape for dialog dismissal, and standard Open/Save As shortcuts. Save As leads to Review first when invoked from an editor. Support system text scaling and high-contrast settings. Use Qt logical units and DPI-aware icons. Avoid animation that delays interaction. FR-070–074, NFR-002/003.

## 10. Implementation stages after approval

1. **Shell and session** — build validated load, compact/wide navigation, explicit state and focus flow. FR-001–007, FR-070–074, FR-080.
2. **Inventory and offline catalog** — implement the grid, inspector, bounded creation, catalog coverage and artwork fallback. Close the higher-row creation and unknown-quantity scope decisions before enabling either workflow. FR-010–018, FR-030–035, FR-097–098.
3. **Skills** — implement precise synchronized controls, draft tracking, XP disclosure and atomic validation. FR-040–044.
4. **Review and export** — implement field-level diffs, dependent discard, native Save As and verified status. FR-050–057, FR-060–063.
5. **Platform acceptance** — run synthetic regressions, perform keyboard/DPI and offline workflow tests on Windows 10 and Linux, and audit distributed catalog and artwork licenses. NFR-001–005, NFR-008.

## 11. Acceptance criteria

| Requirements | Pass condition |
|---|---|
| FR-001–007, FR-071 | Open a valid synthetic save and see identity and actual checksum/round-trip results. Try corrupt and unsupported saves through both entry points. A failed load never replaces a working session or changes source bytes. |
| FR-010–018, FR-032 | Test fewer than six occupied rows, occupied rows above six, the maximum row byte, invalid columns and duplicates. Every record remains reachable. Verify keyboard selection, known item edits, 1/max stack acceptance, overflow rejection, high-quality warning, and byte-identical preservation of untouched unknown records. |
| FR-013, FR-030–035, FR-097–098 | With networking off, find sample items by display name and exact prefab. Check metadata coverage against the reviewed build manifest and reject missing limits, stale selection and occupied targets. A new record has its intended identity and an unset cheated flag. A missing icon leaves all actions available. |
| FR-040–044 | Verify slider↔entry synchronization at 0, 100 and fractional values, and keyboard increments. Include an invalid row in a valid batch and assert no mutation. Inventory-only and level-only edits preserve untouched skill bytes, including XP and unknown IDs. |
| FR-050–057, FR-060–063 | Review add/edit/remove and skill changes with exact before/after values. Exercise draft cancellation, dependent discard, source aliases, changed source, write/read-back failure, and retry. A successful export reopens with intended values and protected data intact. The source digest is unchanged and the destination and verified status are displayed. |
| FR-070–074, FR-080, NFR-002/003/005/008 | On Windows 10 and Linux, perform the full offline workflow using keyboard alone at the test sizes and scaling levels. Check focus, labels, contrast, accessible scrolling and responsive status during file operations. Pass the Alpha 0.1.1 suite plus new UI regressions. Verify provenance for every distributed asset. |

**Owner approval requested** for the layout and theme, the Apply → Review → Save As model, creation bounded to the existing writable rows, level-only XP preservation and removal of the bulk skill action, and the original-art-first offline catalog. These are design proposals. Platform acceptance and catalog completeness will be established during implementation and testing.
