# Alpha 0.2 interface implementation

**Branch** feature/alpha-0.2-ui

**Status** Interface implemented and regression-tested on Windows 10. Native platform acceptance and complete vanilla catalog coverage remain open.

The [approved design](ALPHA_0.2_UI_DESIGN.md) specifies the desktop workflow. [Alpha 0.1.1 stabilization evidence](ALPHA_0.1.1_RESEARCH.md) remains the baseline for the engine and manual in-game acceptance of that release.

## Components and files

| Files | Implementation |
|---|---|
| desktop/app.py | ULF window, file and validation details, draft and export status, Review, native file dialogs and background load/export jobs. The file picker and command-line argument use the same validation path. |
| desktop/inventory.py | Eight-column model/view grid, variable height, keyboard selection, compact inspector, inventory diagnostics, exact item inputs, and searchable item creation. |
| desktop/skills.py | Skill cards with synchronized sliders and precise entry, experience disclosure, exceptional-record diagnostics, and all-or-nothing application. |
| desktop/session.py | Loaded baseline, working copy, independent drafts and identity-based review/discard. Discarding a removal restores the original only after dependent replacements are accounted for. Export tracking compares the working revision against the last verified export. |
| desktop/item_catalog.py, desktop/item_labels.json | Local search index and English display names/categories. Limits and provenance come from the existing core catalog. |
| desktop/theme.py | Charcoal and bronze theme, original ULF wolf mark and item silhouettes, category fallback art, and accessible text and focus styles. |
| tests/test_desktop.py, tests/test_catalog.py | Updated the seven desktop regressions for the new entry points and added coverage for the interface and localized catalog metadata. |
| README.md, docs/ALPHA_0.2_UI_IMPLEMENTATION.md | Updated usage and acceptance evidence. The approved design and offline mockup were already present as untracked files before implementation. |

The Alpha 0.1.1 binary engine, domain validators and export service are byte-for-byte unchanged in Git. The desktop session submits explicit field changes to those validators. Load and export use isolated worker jobs. Save As delegates source/alias protection, source-change detection, semantic verification, closed-file read-back, and publication to the existing service. Artwork is drawn locally in Qt. No game or Viking Editor graphics are bundled.

## Automated verification

Windows 10 Pro 22H2 build 19045, Python 3.12.3, PySide6 6.12.0.

- The original **53-test** suite passed before the interface changes.
- The final suite passed **69 tests**, including **22 Qt interface tests**, with zero failures or skips. Command `.venv\Scripts\python.exe -B -m unittest discover -s tests -v`.
- All **22 interface tests** also passed with offscreen Qt scaling set to **150%** and **200%**. Layout checks use **800×600**, **1366×768**, and **1920×1080** logical window sizes. They verify compact inspector navigation, side-by-side layout, keyboard focus, and the minimum grid target width.
- The offline test exercises catalog search, validated load, creation, and export while Python socket construction is blocked. All fixtures and captured screenshots use synthetic data. Native dialogs are mocked in automation.

## Requirements and acceptance

| Requirements | Disposition |
|---|---|
| FR-001–007, FR-062 | Implemented and tested through the desktop load path. Successful load displays the actual verification result. Failed load preserves the prior session and drafts. Version and cheat flag details are available. |
| FR-010–018, FR-031–032, FR-072 | Implemented and tested for existing verified records and catalog creation. Covers quality 65,535, stack bounds, exact hundredths for durability, confirmed removal, protected flags, duplicate and invalid positions, and visible rows through 256. Existing items above row six can be edited when verified. New items use rows one through six. Unknown records remain read-only and export byte-for-byte. The verified-quantity exception has no supported metadata path in this build. |
| FR-030, FR-033, FR-035, FR-097–098 | Search, category filters, per-item limits and source metadata implemented and tested offline against the bundled reference set. The 821-entry catalog covers all 808 inventory-valid rows in the pinned fch-decoder TSV and all 62 prefabs verified in the existing Valheim 1.0.21 sample audit. Full current-build coverage and Linux offline verification remain open. |
| FR-040–044 | Implemented and tested. Slider steps are 0.1. The numeric field retains finer values through the existing float32 encoding. Failed batches preserve the prior state and drafts. Explicit XP edits and exact preservation of untouched skill fields are covered. |
| FR-050–054, FR-056–057, FR-060–063, NFR-001 | Review, dependent discard, verified Save As, and destination feedback implemented. Tests cover cancellation, source aliases, source changes, unchanged source bytes, preserved unknown and cheat data, and reopened output. Achievement eligibility remains unverified. |
| FR-070–074, FR-080, NFR-002–005 | PySide6 UI implemented with an independent core and no additional runtime dependencies. Windows offscreen tests and synthetic keyboard/layout checks pass. Native accessibility, Linux, and representative large-save responsiveness still need acceptance. |
| FR-075, NFR-008 | Original icons cover common items and fallback categories. Asset provenance is documented below. Full distribution licensing audit remains open. |

## Catalog and artwork provenance

`desktop/item_labels.json` takes the English Name and Type columns for the 821 matching prefabs from the [pinned Jötunn 1.0.7 snapshot](references/jotunn-item-list.md), commit `41cd418939707f9ae925e8c2927c195c1af0c906`. The matching uses the canonical prefab identifier. The [Jötunn license notice](references/Jotunn-LICENSE.txt) and [fch-decoder license notice](references/fch-decoder-LICENSE.txt) are retained. The regression suite checks both the metadata mapping and coverage of the pinned inventory-valid list.

The Jötunn snapshot has 412 additional rows with icon references and no bundled catalog entry. An icon reference establishes neither player-inventory eligibility nor a verified stack maximum. A comprehensive Valheim 1.0.21 inventory-valid manifest with current limits is still needed to classify the gaps and add eligible items safely. The interface displays provenance per item and blocks arbitrary prefabs and unverified quantities.

The ULF mark and icons in `desktop/theme.py` are original Qt drawings. Fallbacks use category silhouettes and a question mark for unknown prefabs. No image files or network font resources are required.

## Remaining usability and manual acceptance

- On Windows 10 and Linux, disable networking and walk through Open, edit quality/quantity/durability, remove and add, edit level/experience, review, and Save As. Reopen a disposable export and compare intended values and the source digest. Exercise native dialog cancel/replace, a locked destination, and an externally modified source.
- Check keyboard-only navigation, screen reader announcements, system high contrast, text scaling, and 100%, 150%, and 200% DPI on native desktops. The compact inspector uses a separate view and restores focus to the slot. Long tile names elide and remain available in the inspector and accessible name. Some items use shared category art.
- Measure responsiveness with large and modded saves. File operations run on workers. In-memory proposal copying and validation, plus rendering of large diagnostics and review lists, still need representative performance checks.
- Confirm a disposable Alpha 0.2 export loads and plays in Valheim. Achievement testing is a separate controlled test covering character, world, mods, game version and server behavior.
- Complete the catalog coverage and distribution licensing checks before release acceptance.
