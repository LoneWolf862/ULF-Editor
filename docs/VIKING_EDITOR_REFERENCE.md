# Viking Editor reference investigation

Research dates: November 12–13, 2026 (America/Denver). Research-only branch: `research/viking-editor-comparison`. ULF baseline: Alpha 0.3.1, `fac8e1b7ba941ff56a2a300e7e374ca48a3fd91c`, descended from the completed `fix/alpha-0.3.1-item-coverage` branch. No application or approved requirements changes accompany this report.

## Findings that affect engineering decisions

1. **The web editor demonstrably handles this current-format save.** Twenty-seven controlled mutation exports, an initial no-op, and an undo-restoration export pass ULF checksum and exact round-trip checks. Both unmodified exports equal the original bytes. This establishes compatibility for the tested profile 47 / player 34 / inventory 110 / skills 2 sample, not universal compatibility or in-game acceptance.
2. **The web catalog does not reveal missing ordinary candidates in ULF.** It has 994 entries, including all 927 candidates in ULF's installed-game audit. All shared stack limits and all 288 applicable durability coefficient pairs agree. Its remaining 67 entries classify as 54 NPC equipment/attacks, nine placed objects, and four internal/test entries. Its 344 durability definitions include 56 from those extra categories. Counts alone would give a misleading coverage comparison.
3. **The desktop source is actively maintained, but its latest release is materially older.** Reviewed HEAD is `09a72ad03ae17955605cc392b4be43e95aec88a7`. Its inner codec supports current layouts. Release v2.3.0 writes player 33 and inventory 109 unconditionally; do not recommend that release for the current save based on HEAD behavior.
4. **ULF should retain its stricter save boundaries.** The desktop HEAD codec accepts a deliberately corrupted checksum with a warning. On a no-op decode/encode of the authorized copy, it changes one durability from 1092.10 to 1092.09. Its passing tests do not establish byte-preserving behavior for all real inputs.
5. **Bulk actions need complete previews.** Web “Repair all (10)” changed 11 records, including reducing an over-maximum durability from 1600 to 800. Food refresh changes saved maxima; skill edits rescale XP. These are concrete reasons to retain ULF's proposal/review/export architecture.

Detailed evidence, field differences and limitations: [experiments](VIKING_EDITOR_EXPERIMENTS.md). Proposed work and acceptance criteria: [integration plan](VIKING_EDITOR_INTEGRATION_PLAN.md).

## Scope, sources and confidence

The [browser application](https://vikingeditor.com/) and [miskamero/VikingEditor](https://github.com/miskamero/VikingEditor) are separate projects. No common source ownership or licensing is inferred from their names.

Evidence labels in the matrix:

- **W — Verified working:** exercised with browser export/decoded comparison, an executed codec test, or existing ULF automated coverage. Scope is stated; this is not an in-game guarantee.
- **D — Documented but untested:** visible control, implementation source or documentation exists, but this investigation did not validate that operation end to end.
- **P — Partially implemented:** a meaningful subset exists, with missing behavior identified.
- **U — Unsupported:** no implementation in the inspected scope, or explicitly incompatible behavior.
- **? — Unknown:** insufficient evidence; absence is not asserted.

Confidence: H = direct experiment or specific inspected code, M = visible controls/documentation, L = uncertain or missing evidence. “Desktop” below means pinned HEAD, unless specifically labelled release. Desktop GUI was not manually operated; source inspection and its 130-test suite were used. ULF's unchanged 99-test suite passes. The historical expansion/scaling documents predate Alpha 0.3.1; their old 821-entry and format-gap statements are superseded by [Alpha 0.2.1 compatibility](ALPHA_0.2.1_COMPATIBILITY.md), [Alpha 0.3 implementation](ALPHA_0.3_ITEM_STATS.md), and [Alpha 0.3.1 audit](ALPHA_0.3.1_ITEM_COVERAGE.md).

## Web application architecture and compatibility

The delivered application uses Next.js/Turbopack and React JavaScript chunks. The observed binary implementation uses typed arrays/DataView, UTF-8/string framing, integer fields, BigInt identifiers, and WebCrypto SHA-512. A local File API input is parsed in the browser; export creates a Blob download. Separate folder workflows use File System Access interfaces. TypeScript as the original authoring language is unknown. No WebAssembly dependency was identified in the inspected character path.

The inspected codec explicitly allows profile 46/47, player 33/34 and inventory 109/110. Skills are versioned separately. It retains structured character data, raw sections, item optional fields and trailing cheat bytes; item custom data uses ordered pairs. Its writer rebuilds optional flags. Thus canonical successful samples do not prove acceptance or preservation of every noncanonical encoding; a round-trip gate is important. The homepage advertises load round-trip validation, export validation, supported-version rejection and preservation of the opened format. The current-format sample directly verifies the successful path, not every rejection path.

The web data is delivered as embedded JSON in a lazy-loaded JavaScript chunk, not obtained by reading the visitor's installed game. Item records include prefab, English/German labels, type, stack and ordinary quality limits, Forge eligibility, variants, durability base/increment, localization token and food properties. A separate data object covers recipes, pieces and stations. No item damage-channel, armor, block, deflection, parry or movement coefficients were found in this item schema. Full combat statistics are not established as supported.

The [privacy policy](https://vikingeditor.com/privacy/) states local-only save processing, self-hosted fonts and consent-based Matomo analytics. Analytics was declined during the experiments. Hosting, advertising and optional analytics mean local save processing is not synonymous with zero network activity. The reviewed character path and local downloads support the local-processing claim, but no complete network capture was available: absence of file transmission was not independently proven packet by packet. No associated public source repository was located in the focused search. Public delivery of code is not an open-source license.

The site advertises Valheim 1.0.21. That matches its embedded data version and the tested footer, and is corroborated by the actual current-format export results. It does not identify a reproducible extraction commit, game assembly digest or complete methodology comparable to ULF's local audit. Claims about future game compatibility remain unverified. Download export was tested; direct folder writes, automatic backups, other browsers, mobile devices and its separate world editor were not.

## Feature comparison

Priority: P0 = preserve safety/finish acceptance; P1 = desktop polish next; P2 = separately scheduled post-MVP; hold = not recommended or outside scope. Requirement IDs are dependencies, not new authorization.

| Feature | Web | Desktop HEAD | ULF Alpha 0.3.1 | Confidence and dependencies / priority |
|---|---|---|---|---|
| Current 47/34/110/2 load/export | W, tested sample | P, parses/writes but no-op drift | W | H; FR-002–005, P0 |
| Add/remove item | W | D | W | H web/ULF, M desktop; FR-013–014 |
| Replace prefab | W, also clamps durability | D, editable prefab field | P, staged remove/add same slot | H; atomic proposal, P2 |
| Duplicate item | W | ? | U | H web; free slot, metadata policy, P2 |
| Quality | W, tested 8→9; Forge UI up to 100 | D, ordinary dialog 1–99 | W, format range 1–65535 with caveats | H; FR-011; retain format-aware ULF range |
| Quantity | W, verified Ice 3→4 | D, generic 1–9999 | W, per-prefab caps | H; FR-012; do not adopt generic bounds |
| Current durability | W | D, generic numeric field | W | H; integer hundredths and FR-018 |
| Computed maximum durability | W, verified examples | U in inspected item database/UI | W | H; build coefficients, P0 preservation |
| Repair / Repair All | W / W with extra reduction | U in inspected inventory UI | W, previewed atomic repair plan | H; full change preview, P1 |
| Fill stack / Fill All | W / W, 13 records | U in inspected inventory UI | U | H; verified caps and bulk proposal, P2 |
| Move/swap/drag and drop | D; gesture attempted without movement | ?; coordinate model and EAQ slots exist | U | M/L; FR-019/091, P2 |
| Equipped state | W, one weapon toggle | D | W, flag only | H; full equipment rules distinct, FR-090 P2 |
| Armor slot exclusivity | D, UI promises auto-unequip | P, EAQ-aware representation | U as full equipment model | M; runtime invariants, P2 |
| Crafter name/ID | W name; D ID | D | U editing; metadata preserved | H/M; explicit protected-field proposal, P2 |
| Custom item key/value metadata | D, advanced entry control | P, retained in model; no general form verified | P, preservation/inspection | M; ordered pairs/raw bytes, FR-015/032 |
| Variant, world level, picked-up state | D advanced controls | D variant; other metadata retained | P, preservation/inspection | M; no generic mutation without rules |
| Clear inventory | D visible control | ? | U | M/L; preview, confirmation, P2 |
| Undo/redo | W, undo export byte-identical; redo deletion observed | ? no general history identified | P, review/discard only | H; FR-020/054, P1 |
| Before/after change review | P, dirty tabs/history; no comprehensive diff observed | ? | W | H/M; FR-054, retain ULF strength |
| Character identity display/name editing | W display; D name form | D | P, display only | M; name may affect game seed behavior, P2 |
| Hair/beard selection | W | D, bundled choice tables | U editing, preserved | H/M; FR-092, P2 |
| Skin/hair colors | W sliders; D raw RGB disclosure | D QColorDialog | U editing, preserved | H/M; float32 triples, FR-092 |
| Body/model | D male/female controls | D model 0/1 | U editing, preserved | M; FR-092, P2 |
| 3D character preview | U in observed interface | U in inspected appearance tab | U | H; no need to adopt |
| Current health/stamina | W | D | U editing, preserved | H/M; typed head/tail fields, P2 |
| Current/max eitr | D, input disabled for tested no-eitr food set | D | U editing, preserved | M; food constraints, P2 |
| Maximum health/stamina | W as food-derived side effects | D directly editable | U editing, preserved | H/M; authoritative game formulas first |
| Forsaken power/cooldown | W | D | U editing, preserved | H/M; FR-005 boundary, P2 |
| Active foods/durations | W refresh; D add/remove | D | U editing, preserved | H/M; dependent maxima, P2 |
| Individual skill levels | W | D, covered by upstream tests | W | H/M; FR-041/044 |
| Skill XP | P, displayed progress/rescaled on level edit; no direct input observed | D direct progress editing | W explicit XP | H/M; FR-042, policy must be explicit |
| Bulk skills/presets | D target/max/reset; no named preset system observed | D reset/max/unlock controls | U | M; FR-045/094, P2 |
| Skill graphical controls | W sliders + number | D source controls | W sliders + number | H/M; FR-044/073 |
| Known recipes | W single unlock | P read-only progress browser | U editing, preserved | H; FR-093, P2 |
| Known materials | W single removal | P read-only progress browser | U editing, preserved | H; FR-093, P2 |
| Crafting stations/levels | W | P read-only progress browser | U editing, preserved | H; FR-093, P2 |
| Biomes | W single removal | P read-only progress browser | U editing, preserved | H; localized values, P2 |
| Build pieces | D separate knowledge category | P recipe/progression records displayed | U editing, preserved | M; token classification, P2 |
| Tutorials / lore / known texts | D Hugin/Lore controls | P codec preservation; dedicated editing not found | U editing, preserved | M; FR-093, P2 |
| Trophies / keys / unique discoveries | D knowledge categories | P read-only categories | U editing, preserved | M; FR-093, P2 |
| World/profile statistics | P header/world references | D statistics and worlds tabs | P opaque preservation | M; scope review before editing |
| New character creation | ? | D `newCharacter.py` | U | M/L; separate future requirement |
| Cheat flags/history | D advanced readout; tested exports preserve existing state | D editable/removal controls | W preservation, read-only inspection | H; FR-016/060–063, hold removal tools |
| Item artwork | Original-looking symbolic inventory glyphs observed | D local Unity sprite extraction | W original/fallback icons | M/H; FR-035/075, rights gate |
| Offline item lookup | D delivered data; cold offline launch untested | D local cache after installed-game extraction | W bundled data | H/M; FR-098/NFR-003 |
| Automatic backup | D folder workflow claim | D default backup/retention code | P original protected; broader recovery deferred | M; separate-file recovery only, P1 |
| Source overwrite protection | P download copy path tested; folder workflow can write | U equivalent protection; original can be target | W source and aliases blocked | H; FR-050, retain ULF policy |
| Reopen/check written output | D advertised browser validation; external ULF check passes | U equivalent post-write check not found | W | H/M; FR-051–053, P0 |

“Unsupported” for ULF character/progression editing does not mean that data is dropped: it is preserved in protected sections. The matrix does not elevate upstream test coverage to a manual GUI or in-game test.

## Desktop maintenance, architecture and extraction

The pinned [HEAD commit](https://github.com/miskamero/VikingEditor/commit/09a72ad03ae17955605cc392b4be43e95aec88a7) is dated 2026-11-13 00:18:09 +02:00 (November 12 in Denver), with meaningful equipment-slot, safeguards and regression work. Other November commits address modern saves and modded skills. GitHub's API returned no open non-PR issues at inspection time; that is not evidence of no defects. [Latest release v2.3.0](https://github.com/miskamero/VikingEditor/releases/tag/v2.3.0) was published 2026-10-12 17:21:56 UTC. Its hard-coded 33/109 inner writer differs from HEAD. No released-binary 1.0.21 acceptance test was performed.

Python/PySide6 form the desktop application. The README targets Windows/Linux and Python 3.9+, while actual pinned dependencies include PySide6 6.11.1 and UnityPy 1.25.3; the README minimum is not a verified install matrix. Pillow, texture/compression/audio dependencies and PyInstaller support extraction/packaging. The local run used ULF's existing environment, not a clean reproduction of the upstream dependency lock. The [Windows Python 3.11 test workflow](https://github.com/miskamero/VikingEditor/blob/09a72ad03ae17955605cc392b4be43e95aec88a7/.github/workflows/unittests.yml) and 130 passing local tests are useful evidence, with Linux and released executables still untested here.

Source responsibilities:

| Component | Findings |
|---|---|
| [fchUtil.py](https://github.com/miskamero/VikingEditor/blob/09a72ad03ae17955605cc392b4be43e95aec88a7/subscripts/fchUtil.py) | Outer profile dictionary, framing, SHA-512, JSON intermediary. Checksum mismatch and unknown outer profile are warnings on read. Writer allows 46/47. Writes destination directly. UTF-8 decoding can ignore invalid bytes. |
| [playerDataUtil.py](https://github.com/miskamero/VikingEditor/blob/09a72ad03ae17955605cc392b4be43e95aec88a7/subscripts/playerDataUtil.py) | Versioned inner model: vitals/power, inventory, knowledge, appearance, foods, skills, custom data, current stamina/eitr, build UI bytes, v34 drop counters/upgrade seeds, retained trailing hex. Unknown inner versions rejected. Canonicalizes item flags; dictionaries cannot preserve duplicate keys. Durability float conversion truncates on write. |
| [inventoryTab.py](https://github.com/miskamero/VikingEditor/blob/09a72ad03ae17955605cc392b4be43e95aec88a7/ui/inventoryTab.py) | Grid with normal pockets and EquipmentAndQuickSlots-aware storage. Unsupported records shown read-only; latest code applies changed properties selectively. EAQ residence/identity edits restricted because runtime slot rules are unavailable. |
| [itemEditDialog.py](https://github.com/miskamero/VikingEditor/blob/09a72ad03ae17955605cc392b4be43e95aec88a7/ui/itemEditDialog.py) | Prefab, generic stack/quality/variant/durability controls, equipped and cheat checkbox, exact crafter-ID text field. Generic caps do not implement ULF's per-item verified maximum policy. Imported abnormal values should not be assumed clamped on unrelated saves: latest selective-change logic matters. |
| [progressTab.py](https://github.com/miskamero/VikingEditor/blob/09a72ad03ae17955605cc392b4be43e95aec88a7/ui/progressTab.py) | Searchable read-only counts/list for recipes, stations, materials, trophies, uniques and biomes. It is not equivalent to the web knowledge editor. |
| [mainWindow.py](https://github.com/miskamero/VikingEditor/blob/09a72ad03ae17955605cc392b4be43e95aec88a7/ui/mainWindow.py) | Collects tab changes, prompts for target, optional/default backup with retention, intermediate JSON and direct compile. No equivalent source-alias prohibition, atomic verified target replacement or post-write reopen was identified. |

The [item database extractor](https://github.com/miskamero/VikingEditor/blob/09a72ad03ae17955605cc392b4be43e95aec88a7/subscripts/itemDatabase.py) scans installed SoftRef bundles through UnityPy, resolves GameObject ItemDrop components, and selects shared localization tokens beginning with `$item_`. It writes a local prefab/hash/name-token/icon cache. It does **not** extract stack limits, quality coefficients, damage, armor, blocking or maximum durability. A hard-coded `valheim_version: "1.0"` label is not build verification. It does not establish ObjectDB-rooted player-inventory eligibility and retains the first hash-collision candidate. These are reasons to retain ULF's stronger audit rather than replace it.

Useful icon implementation patterns are content-addressed PNG names, sprite caching, RGBA extraction, variant slots with fallback, constrained cache paths, temporary-file replacement and preservation of an old database on failed extraction. Progress/cancellation callbacks are useful for a future optional extractor. Do not execute a full bundle scan every application launch. Hair/beard choices are bundled Python tables, not evidence of current-build extraction of all customization assets.

## Catalog, statistics and the three diagnostic categories

The comparison used the website's delivered factual metadata locally and ULF's [installed-game classification ledger](references/item-coverage-1.0.21.json). No website dataset or implementation was imported into ULF or committed.

| Measure | Web snapshot | ULF baseline | Interpretation |
|---|---:|---:|---|
| Total catalog entries | 994 | 1049 | Different inclusion policies; neither count alone proves completeness. |
| Shared ordinary candidates | 927 | 927 | No ordinary candidate missing from the web set or current ULF audit. |
| Applicable durability definitions on ordinary candidates | 288 | 288 | All base/increment pairs agree. |
| Additional web durability definitions | 56 | Not promoted as ordinary stats | Belong to the web's 67 nonordinary entries. |
| Shared stack-limit disagreements | 0 | 0 | Strong corroboration, not independent proof of web extraction provenance. |
| Web names absent from ULF's full catalog | 56 | — | Classified extras, not automatically catalog defects. |

Keep separate statuses in future diagnostics:

- **Unknown prefab:** no verified identity for the serialized hash; preserve exact record bytes. A familiar-looking display label is insufficient.
- **Missing catalog metadata:** identity resolved, but a field such as maximum stack or localization is unavailable. Disable dependent writes; never infer a stack cap from type.
- **Missing statistics:** identity and stack limit are known, but applicable coefficients or context are missing. Preserve editing that is independently safe; disable derived repair/stat claims. Inapplicable durability is a fourth state, distinct from missing data.

The web formula uses base + max(0, q−1) × increment, rounded to integer hundredths with JavaScript arithmetic. Unknown durability has a fallback in its helper; this is not a verified item maximum. Its unknown-item inspector uses format-wide fallback limits (65535). Neither fallback should be adopted by ULF. The Forge UI commonly allows 100, retaining a larger existing quality in its upper bound; this is an editor policy, not proof of a game limit. ULF's inspected game methods have no verified quality-100 arithmetic cutoff. ULF additionally emulates float32 intermediates and validates signed-hundredth representability. No extreme-quality browser export or runtime game test was performed.

ULF already extracts applicable damage, armor, block, deflection, parry and movement data, with applicability and context restrictions. No more complete combat-stat database was established in either reference. Continue using installed 1.0.21 assets and assembly methods as authority; external agreements are cross-checks. Positive world-level and projectile/skill/status interactions remain separate research topics in [ITEM_STAT_SCALING.md](ITEM_STAT_SCALING.md).

## UI/UX observations

The web editor separates Inventory, Skills, Character and Knowledge. A persistent export/history bar, dirty-tab indicators, contextual inspector, compact grid, category/search picker and keyboard-labelled controls make common actions discoverable. Hotbar and equipped styling are readable; numerical maxima are adjacent to inputs. Skills pair sliders with precise decimal inputs and explain progress behavior. Knowledge separates item recipes from building pieces and exposes extra saved entries rather than hiding them.

These are patterns to adapt independently, not a layout or artwork specification for ULF. Prefer ULF's explicit review panel over relying only on dirty badges. Particularly useful additions are domain-backed undo, keyboard commands equivalent to drag actions, consistent quick-action placement, and grouped/searchable future progression controls. Show the full transaction, including auto-unequips, durability reductions and derived maxima.

Observed weaknesses/uncertainties: bulk repair's displayed count excluded an additional changed record; a no-op restored through Undo could still show dirty-tab styling before final export; some spinbuttons lack individual accessible names in the observed tree; long knowledge lists expose inconsistent category/header totals. Those counts may reflect extra/legacy tokens, not damaged data. Dragging did not move the selected item using the available gesture. Screen-reader completeness, responsive breakpoints, mobile layout and keyboard-only task completion were not comprehensively tested. No 3D model preview appeared in the inspected character panel.

## Licensing and reuse boundary

The website's [legal notice](https://vikingeditor.com/imprint/) reserves rights; no reusable source/data license was established. Keep its JS, database and graphics out of ULF. Numerical agreement can motivate independently verified game-data extraction without copying its dataset.

The desktop repository's [LICENSE](https://github.com/miskamero/VikingEditor/blob/09a72ad03ae17955605cc392b4be43e95aec88a7/LICENSE) is GPLv3; [NOTICE](https://github.com/miskamero/VikingEditor/blob/09a72ad03ae17955605cc392b4be43e95aec88a7/NOTICE) separately restricts use of the VikingEditor name/logos for modified versions. Source availability is not permission to copy into an incompatibly licensed distribution. Prefer independently implemented patterns. Any proposed GPL incorporation needs a deliberate project-license review, notices and corresponding-source obligations as applicable. Neither license grants independent rights to Valheim artwork; optional user-local extraction is a different distribution model, not a blanket permission. See FR-035 and NFR-008.

## Limits and next verification

This research covers one authorized local save and static installed-build evidence from Alpha 0.3.1. It does not certify arbitrary modded saves, noncanonical strings/duplicate maps, every supported historical version, future versions, in-game achievements, gameplay at extreme quality, other operating systems or every website path. No cheat flags or character cheat history were deliberately changed. No world editor experiments were performed. A full network trace, actual drag/drop success, responsive/accessibility matrix, direct-folder backup failure handling and released desktop binary tests remain manual/future checks. These limits do not prevent the concrete roadmap in the integration plan.
