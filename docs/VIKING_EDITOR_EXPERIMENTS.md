# Viking Editor controlled experiments

Investigation performed November 12–13, 2026 (America/Denver). ULF baseline: `fac8e1b7ba941ff56a2a300e7e374ca48a3fd91c`. Desktop reference: `09a72ad03ae17955605cc392b4be43e95aec88a7`. These are research results, not changes to ULF functionality or approval of a future milestone.

## Method and safeguards

The owner explicitly authorized the designated local character save for this website investigation. An experimental copy, `experiment-input.fch`, was loaded through the browser file chooser. The original remained untouched; its SHA-256 was saved locally and rechecked. No unrelated saves were uploaded, no original or experimental saves are committed, and no identifying name, player ID, world name or crafter attribution is included here. This task-specific authorization did not change ULF's offline product requirements or the general prohibition on publishing real saves.

Input characteristics: **280,235 bytes**, profile **47**, player **34**, inventory **110**, skills **2**, **33 inventory records**, displayed in **48 slots**. Exact input hash is retained locally rather than published as a stable identifier. This is one actual save, not a synthetic compatibility matrix.

The existing in-app browser session was resumed after interruptions. Browser controls supported DOM/accessibility inspection, selecting controls, file chooser upload, editing fields, Undo/Redo and waiting for downloaded files. Each mutation began from the restored baseline, changed one user-facing property/action, and exported through **Save & download**. Undo restored the preceding action before the next experiment. The initial no-op and a later full-history undo export independently establish exact restoration. No original overwrite or direct-folder save workflow was used.

Local diagnostics used:

1. ULF `Character` to validate framing, SHA-512, layout versions and exact parse/serialize round-trip for every downloaded file.
2. The pinned desktop project's `decompile_fch` and `unpack_player_data_hex` as an independent semantic decoder for profile/player fields ULF intentionally retains as opaque sections.
3. Recursive before/after comparisons, plus ULF protected-section byte comparisons. Strings containing personal identifiers were redacted in diagnostic summaries.
4. Explicit list membership checks for additions/removals, rather than treating changed list lengths as sufficient proof. Duplicate/add tests preserved every original inventory dictionary; delete removed exactly the selected item. Recipe/material/biome tests changed the expected member only.

The second decoder is a useful cross-check, not an oracle: it normalizes dictionaries and some float representations. A matching decoded structure does not prove preservation of arbitrary duplicate keys, malformed text or noncanonical encoding. ULF's exact round-trip and raw-section checks supplement it. All exports retained the same format versions. No Valheim launch or game resave was performed.

## Results: 29 downloaded exports

**All 29 files passed ULF checksum and exact round-trip validation.** Twenty-seven contain intentional mutations; two are byte-identical controls. The profile structure excluding its nested player payload remained identical in all experiments. No experiment deliberately altered character cheat history, item cheat flags, drop counters or upgrade-seed records.

Fields below use the independent decoder's names. Inventory indices are serialization order, not screen coordinates. The selected sword was index 12 at zero-based `(0, 0)`; new/duplicate placement was `(5, 1)`. “Only” excludes necessary framing-length updates and SHA-512 changes.

| ID / local output | UI action | Verified structural difference | Other changes / interpretation |
|---|---|---|---|
| E00 `web-noop` | Export without edits | None; exactly 280,235 original bytes | Establishes successful no-op path for this sample. |
| E01 `web-quality` | Sword quality 8→9 | `inventory[12].quality` only | Current durability remains 715; displayed max changes 750→800. |
| E02 `web-durability` | Set current durability 700 | `inventory[12].durability` 715→700 | Quality and metadata unchanged. |
| E03 `web-repair` | Repair selected sword | Durability 715→750 | No skill/XP or other item changes. |
| E04 `web-duplicate` | Duplicate sword | Inventory 33→34; appended copy at `(5,1)` | Copy has q8, stack1, current715, unequipped, picked-up, preserved crafter/custom data, cheat byte0. Original 33 records unchanged. |
| E05 `web-equipped` | Equip sword | `inventory[12].equipped` false→true | No other equipment changed in this case; does not prove armor conflict handling. |
| E06 `web-crafter` | Set crafter name to research marker | `inventory[12].crafter_name` only | Crafter numeric ID preserved; original name withheld. |
| E07 `web-replace` | Replace with Bronze Sword | Prefab hash 1690651452→995331031; durability715→550 | q8 retained. New q8 maximum is550; current durability is clamped. Identity change is not the sole serialized edit. |
| E08 `web-hair` | Select No Hair | `hair`: Hair7→HairNone | Only this appearance string and framing/hash change. |
| E09 `web-beard` | Select No Beard | `beard`: Beard18→BeardNone | Only this appearance string and framing/hash change. |
| E10 `web-power` | Select Eikthyr | `guardian_power`: GP_Moder→GP_Eikthyr | Cooldown unchanged. |
| E11 `web-cooldown` | Set cooldown60 | `guardian_power_cooldown`: 0→60 | Other head fields unchanged. |
| E12 `web-health` | Set health200 | `health`: 207.1339569→200 | Maximum health unchanged. |
| E13 `web-food` | Fresh on first active food | `foods[0].time`:875→1800 | Also max_health207.1339569→227.5651855 and max_stamina171.2757568→178.0861511. Current health/stamina unchanged. |
| E14 `web-skin` | One keyboard increment on skin slider | All three skin RGB components approximately0.65→0.6493 | Model, hair and other fields unchanged. UI tone maps inversely to these channel values. |
| E15 `web-colour` | One keyboard increment on hair-tone slider | Hair green0.65507865→0.65476704; blue0.49666089→0.49636081 | Red and other character properties unchanged. |
| E16 `web-recipe` | Learn Breastplate of the Protector | `known_recipes`871→872, adds `$item_chest_heavy_deepnorth` | Existing recipe order/members retained. No automatic material/station unlock. |
| E17 `web-station` | Artisan Table level2→1 | `known_stations["$piece_artisanstation"]`:2→1 | No recipe deletion. Station knowledge and physical station availability are different. |
| E18 `web-material` | Forget Acorns | `known_material`534→533, removes `$item_oakseeds` | No recipe removal. UI discovered-item count uses a broader/different presentation than this raw list. |
| E19 `web-biome` | Forget Meadows | `known_biomes`9→8, removes `Meadows` | Serialized value is localized text, not a numeric biome enum in this list. |
| E20 `web-skill` | Swords level to80 | `skills[3].level`:85.8245163→80 | XP180.75→165.2377472 too; proportional-progress policy, not a level-only edit. |
| E21 `web-quantity` | Ice stack3→4 | `inventory[29].stack` only | Verified maximum displayed50. |
| E22 `web-fill` | Ice Max | Stack3→50 | No unrelated stack edits. |
| E23 `web-delete` | Delete Ice | Inventory33→32, only Ice removed | Undo restored it; Redo removed it again visibly; Undo restored baseline before continuing. |
| E24 `web-add` | Add Bronze Sword to empty slot6/2 | Inventory33→34; new record at `(5,1)` | q1, stack1, durability200, picked-up true, equipped false, world0, variant0, empty custom data, cheat byte0. Original records unchanged. |
| E25 `web-finalundo` | Export after undoing all mutations | None; exact original bytes | Verifies restoration despite transient unsaved indicators in UI. |
| E26 `web-repairall` | Repair all (10) | **11** durability fields changed | Ten increases and one1600→800 reduction; details below. |
| E27 `web-fillall` | Fill stacks (13) | Exactly 13 stack fields changed | No quality/durability/metadata changes. All proposed quantities match verified caps. |
| E28 `web-stamina` | Set current stamina150 | `stamina`:171.2757568→150 | Tail bytes necessarily change at this field; other decoded tail values unchanged. |

At the end, Undo was disabled after restoring baseline. No experimental state needed to be applied to an original save.

### Bulk repair discrepancy

The button counted ten below-maximum items, but the export modified indices `0,6,7,8,12,13,14,16,17,23,26`. Index23 went from1600 to800. The other ten increased to their computed maxima. This is an observed mismatch between the action label's count and its total effects, not an assumption based on binary offsets. Preserve ULF's explicit preview of every increase/decrease and skip reason. A repair command must define whether over-maximum values are reduced; the action label must count every change.

Fill All changed indices `5,10,11,19,20,21,22,24,27,29,30,31,32`. Final stacks were respectively `10,10,10,10,10,10,100,50,50,50,50,50,50`. Only quantity fields changed.

### Byte-level observations

For equal-length files, E01 quality changed65 bytes total, E02 durability65, E03 repair66, E05 equip65, E07 replacement71, E11 cooldown66, E12 health66, E13 food72, E14 skin70, E15 hair color68, E17 station64, and E20 skill69. These counts include the checksum: not every one of its64 bytes necessarily differs. They must not be interpreted as the number of gameplay fields.

Hair/beard/power/crafter and list changes can alter string/count framing and shift later data. For example, duplication adds28 bytes, while adding the default Bronze Sword adds13. Variable-length changes require structural alignment, not naive offset comparison. Raw ULF head/middle/tail/skills sections stayed identical whenever the operation did not target those sections. E28 correctly changes a tail field; claiming all tails were unchanged would be incorrect.

## What the experiments establish about the format

- Item quality and stack use optional unsigned16-bit fields in the current codec. Position/world-level bytes, presence/equipment flags, optional crafter64-bit ID/string, prefab32-bit hash, ordered custom data and trailing cheat byte are separate concerns. The successful examples corroborate ULF's current layout; they do not newly authorize editing every field.
- Stored durability is signed integer hundredths. Maximum durability is calculated from item data and quality, not a separate maximum field in the record. E01 changed quality without rewriting current durability; E03 changed only current durability.
- Power and cooldown reside before inventory. Appearance, knowledge and foods lie in ULF's preserved middle. Skill records have separate level/XP float32 fields. Current stamina/eitr and v34 maps lie later. Future typed editing should subdivide these protected sections while retaining untouched raw encodings.
- Recipe/material strings are localization tokens; biome discovery uses localized text. Presentation labels cannot safely serve as universal serialized identifiers. Knowledge category counts are not equivalent to raw serialized list lengths.
- Food-derived maxima and XP progress involve policies/formulas beyond simple serialization. Web behavior is reference evidence, not authority over game formulas or ULF's approved policy.
- Existing flags and profile metadata were preserved in the tested changes. The experiment does not assess achievements or authorize clearing flags.

## Desktop codec experiments

The public source was cloned into ignored local research storage and pinned to HEAD `09a72ad03ae17955605cc392b4be43e95aec88a7`. Its codec functions were inspected before executing local diagnostic calls. No GUI install or upstream code import into ULF production occurred. The cache environment was redirected to local research storage; no installed personal cache was required.

| Test | Result | Implication |
|---|---|---|
| Decode current input; pack player; compile outer profile | Current versions recognized and retained, but output is not byte-identical | At index14, durability1092.10 becomes1092.09. Other decoded fields match. |
| Corrupt only one checksum byte in a disposable copy; call `decompile_fch` | Accepted with checksum-mismatch warning | Not equivalent to ULF's fail-closed integrity policy. |
| Run current upstream regression suite | **130 tests passed** | Useful coverage, does not catch the observed real-input decimal drift. |
| Inspect release v2.3.0 writer | Hard-coded player33 and inventory109 | Current HEAD compatibility cannot be attributed to the release binary. No release GUI experiment performed. |

The no-op drift follows the inspected implementation's float conversion: read integer hundredths through multiplication by0.01, then serialize with `int(durability * 100.0)`. Binary floating-point plus truncation can lose a hundredth. Preserve ULF's raw integer handling and original bytes. Do not fix or fork this upstream project as part of the research assignment.

## Public resource and catalog evidence

Publicly delivered character resources were retained locally only. No private endpoint, source map bypass or restricted server code was accessed. For snapshot reproducibility:

| Resource | SHA-256 |
|---|---|
| Homepage HTML captured in initial investigation | `e7f2fc6ccf5cb97bbae194ce9547337f14e55f537e5adb09000b062253dca495` |
| [`44tv3q-g2df54.js`](https://vikingeditor.com/_next/static/chunks/44tv3q-g2df54.js), binary/file code | `a2838b1aa9dea5c210c543b50ce342fe8af1f00fe2228c48bb3e6a45b34a3e6d` |
| [`0dj8zczpm9an1.js`](https://vikingeditor.com/_next/static/chunks/0dj8zczpm9an1.js), inventory/catalog | `f578c2f8c3dd6e6c5c5029a70cecb7370b32a7bb1684ec27ed934598e6aecf64` |
| [`1yhtru1ao1bhd.js`](https://vikingeditor.com/_next/static/chunks/1yhtru1ao1bhd.js), character/knowledge controls | `5ff5cf3692aa651219bbbc9c5889c7d6030663a0b1b6a62a535bc2df44a4ef83` |

Chunk URLs may disappear on deployment; these hashes identify observed resources, not a public reuse grant. The local diagnostic read JSON literals as data rather than executing proprietary JavaScript outside the browser.

The catalog contains 994 unique prefab records; 344 have durability data. Comparison against the ULF installed-game snapshot found all 927 ordinary candidates, no shared maximum-stack disagreements and no applicable durability coefficient disagreements. The 67 extras match 54 NPC/attack, nine placed-object and four internal/test classifications. All 56 additional durability rows occur in that extra set. ULF's 1049 catalog entries include retained legacy identities, so neither total is a direct eligibility metric.

The authoritative installed-game evidence remains build 26249040/Valheim 1.0.21, with input hashes and extraction methodology in [the Alpha 0.3.1 audit](ALPHA_0.3.1_ITEM_COVERAGE.md). This research did not replace that provenance with website metadata.

## Unperformed or inconclusive tests

- The available screenshot-based drag gesture did not move the selected sword. The original slot remained unchanged; no movement export was claimed. Website instructions advertise move/swap/stacking, but successful drag/drop and keyboard movement need a separate test.
- Name/model editing, direct RGB entry, custom item metadata mutation, armor auto-unequip, variant changes, new active-food selection, eitr editing, mass skill operations, lore/tutorial/trophy/key mutation, clear-all and historical/future-format rejection were inspected where controls/source existed, not independently exported.
- Eitr input was disabled for the tested food configuration. This is not evidence that eitr editing is globally unsupported.
- No full network request recorder was exposed through the used browser tool surface. The source path and privacy claim support browser-local processing; no complete traffic audit was performed. Analytics was declined.
- No direct-folder writes, backup failures, mobile/responsive matrix, comprehensive keyboard/screen-reader audit, game reload, Linux run or released desktop binary test was conducted.
- The checksum-negative experiment was on the desktop codec, not the website. Do not generalize it to the web editor.

## Reproduction and retention

Ignored `.venv/viking-research/` contains the input copy, named `web-*.fch` exports, local JSON comparisons, scripts, resource manifest, desktop clone and disposable diagnostics. Browser downloads also remain local. These files are preserved for the owner but intentionally omitted from Git. A new investigator can repeat the procedure with their own authorized current save, preserving a source digest, making one action per export and checking both byte and semantic differences. No personal fixture is necessary in the public repository.

Validation commands used Python 3.12.3: ULF `.venv/Scripts/python.exe -m unittest discover -s tests -q` (**99 passed**), and the corresponding interpreter against upstream's `tests` directory (**130 passed**). The upstream run used the existing environment rather than a clean installation of all pinned dependencies. Research changes are documentation-only; the original save digest and production tree are rechecked before commit/push.
