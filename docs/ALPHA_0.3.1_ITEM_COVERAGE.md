# Alpha 0.3.1 catalog and statistics audit

Date: 2026-11-12. Development branch: `fix/alpha-0.3.1-item-coverage`.
Base: fetched and verified `origin/feature/alpha-0.3-item-stats`, `454ac4e`.
The clean baseline passed all 87 tests before changes. No main merge or release
is authorized by this report. Approved REQUIREMENTS.md is unchanged.

## Acceptance targets and architecture

- FR-030–033, FR-097–098: enumerate the installed ObjectDB, classify every entry,
  resolve the reported hashes, and provide verified offline limits and names
  where available. Preserve and report incomplete metadata independently.
- FR-018, FR-054, FR-072: calculate the three observed durability maxima from
  extracted coefficients; test q1/4/20/50/100; stage individual and bulk repair
  without modifying quality, quantity, skills, or unrelated item fields.
- FR-002–005, FR-010, FR-015–016, FR-032, FR-050–053, FR-060: retain checksum,
  byte-exact no-op, unknown-record, original-file and cheat-metadata protections.
- FR-080, NFR-003/005: no Qt dependency in core; synthetic fixtures; no game
  installation, network, UnityPy, or assemblies required by the running editor.

The existing parser, edit transactions, export service and repair transactions
remain unchanged. A research-only ObjectDB auditor complements the selected-item
extractor. A deterministic builder produces the catalog, statistics, attributed
labels and a complete classification ledger. The existing statistics service
consumes the expanded snapshot. Inspection UI changes stay in the existing pane.

## Source verification

The installed Steam manifest still identifies build **26249040**, Valheim
**1.0.21**. Local read-only input hashes:

| Input | SHA-256 |
|---|---|
| SoftRef bundle `c4210710` | `84f55cfb24af51b9f0494fd9d1a355bf009e08545ff8ccf607c7d88d2e4e1ec8` |
| `assembly_valheim.dll` | `9f959c0396ec4240d47fcbe5d0d062c428cc627244506db5ea567f9d77b2b769` |
| `resources.assets` | `892db5626808f6929c7f3c5dd3997e965100074b0a493d7ce54eb2489f0cdd6f` |

The assembly matches the independently inspected formula/codec evidence in
[ITEM_STAT_SCALING.md](ITEM_STAT_SCALING.md) and
[ALPHA_0.2.1_COMPATIBILITY.md](ALPHA_0.2.1_COMPATIBILITY.md). Coefficients were
extracted anew from every selected ItemDrop shared record. All selected tokens
match the pinned Jötunn mapping. Installed English localization independently
confirms the three reported equipment names and Ice. It also changes FaderDrop's
older label to **Kindled Ribs**; the override identifies its own source.

The [pinned MIT fch-decoder reference](references/items.tsv) remains a codec and
historical catalog comparator, not authority for present inventory eligibility.
The [Jötunn generated index](https://valheim-modding.github.io/Jotunn/data/objects/item-list.html)
includes attack proxies as well as player items. Its icon/name alone cannot
establish inventory eligibility. The audited registry is the local `_NetScene`
ObjectDB `m_items`, rather than that web table or the previous catalog count.

## Complete registry audit and conservative eligibility

The bundle exposes **5,477 prefab container entries**. ObjectDB registers
**1,522 unique prefab names**; **1,519** have root ItemDrop data. Scanning the
container graph finds **zero additional unregistered ItemDrop prefabs**.

| Classification | Count | Treatment |
|---|---:|---|
| Ordinary inventory candidates | 927 | Verified ItemDrop, non-null inventory icon, rigidbody, registered canonical identity; included with limits and statistics. |
| Customization | 114 | Item type 10; hair/beard records, separately classified. |
| No inventory icon | 411 | Mostly attack proxies and NPC gear; not promoted as player items. |
| NPC equipment or attacks with icons | 54 | Character asset graph, excluding actual fish and TrophyKvastur; not promoted. |
| Placed objects | 9 | Feast objects lack the inventory item's rigidbody; material counterparts are separate prefabs. |
| Internal/test | 4 | CapeTest, PlayerUnarmed, SledgeCheat, SwordCheat; ordinary inventory eligibility not established. |
| No ItemDrop | 3 | FrozenKing_Summon, PropFeastDeepNorth, SnowRoller. |
| Unresolved registered identities | 0 | Every registered name classified; none inferred from a display name. |

This is a comprehensive **static registry audit**, not a claim that each prefab
has been acquired and used in-game. The 927 are a conservative, reproducible
ordinary inventory set. NPC/test/placed exclusions do not prove those objects
could never be forced into a save. Their normal player usability remains outside
the verified set. No unknown hash is mapped speculatively.

The machine-readable [coverage ledger](references/item-coverage-1.0.21.json)
lists all included identities, all exclusions and reasons, and retained legacy
entries. This makes gaps reviewable rather than concealing them in a total.

## Exact coverage

| Measure | Before | After |
|---|---:|---:|
| Ordinary audited inventory prefabs supported | 699 / 927 | 927 / 927 |
| Missing ordinary audited inventory identities | 228 | 0 |
| Total catalog entries | 821 | 1,049 |
| Retained legacy entries outside ordinary inventory set | 122 | 122 |
| Ordinary inventory entries with verified stack limits | 699 | 927 |
| Ordinary inventory entries with verified normal max quality | 699 | 927 |
| Ordinary inventory entries with verified statistics | 8 | 927 |
| Applicable verified maximum durability | 6 | 288 |
| Repairable equipment with verified maximum durability | 6 | 285 |
| Applicable nonempty damage vectors (weapons/tools/ammo) | 3 | 177 |
| Applicable armor (helmet/chest/legs/shoulder) | 2 | 116 |
| Applicable block/deflection/parry (weapon/tool/shield categories) | 4 | 196 |

All 1,049 retained/expanded catalog entries have freshly verified stack and
quality limits. None of the old 821 stack limits disagreed with the installed
data. The 122 compatibility entries are 111 customization entries, eight placed
feasts and three Dverger weapon/attack entries. They remain recognized with
their prior editing behavior, but are excluded from the ordinary inventory and
statistics totals. No new NPC/customization/test entry is added.

All 927 statistical rows include use-durability, repairability, damage channel
coefficients, armor, block, deflection, parry, movement, max stack, normal quality
and numeric item type. Default armor/durability/block fields on materials do not
make those properties applicable. Sparkler, Torch and TorchMist use durability
but explicitly disallow repair. Damage is the prefab's item vector, not a claim
about projectile damage, attack multipliers or combat results. Positive world
levels still suppress damage/armor calculations because their context is unverified.

### Three different kinds of missing information

1. **Unknown prefab:** no verified identity for a hash. None remain in the local
   sample or audited registry. Arbitrary/modded hashes still stay protected.
2. **Missing catalog metadata:** zero missing stack/quality limits in the supported
   set; **11 missing friendly display names**. The pinned labels contain unresolved
   tokens for GenericMoldUncooked, IceShoes, IceSkates, Larva, LastBossGate_RuneTile,
   MoldSmallParts, Pot_Shard_Red, SmallPartsGoldUncooked, TorchMist, TrophyDeerWhite
   and TurretBoltBone. Installed localization also lacks these token definitions.
   The UI uses exact prefab identifiers and discloses the missing names. Their
   identity, numerical metadata and statistics are independently verified.
3. **Missing statistics:** zero within the 927 audited ordinary items. The 122
   legacy entries intentionally lack a supported statistics row. The UI explains
   unavailable statistics separately from unknown identity and missing limits.

## Independent observation checks

| Item / verified prefab | Hash | Quality | Current | Extracted base + increment | Calculated max | Owner's max |
|---|---:|---:|---:|---|---:|---:|
| Thunderblood Sword / SwordGold_BloodLightning | 1690651452 | 8 | 715 | 400 + 50 per level | 750 | 750 |
| Lightning Strike / StaffThunderBlood | -677306358 | 8 | 733 | 400 + 50 per level | 750 | 750 |
| Moose Hide Cape / CapeDeepNorth | 1865694990 | 32 | 2727 | 1200 + 50 per level | 2750 | 2750 |

Ice is prefab `Ice`, hash **-466768857**, max stack **50**, normal quality **1**.
It does not use durability. Quantity 3 is valid. The cape has stack limit 1 and
normal quality maximum 4; q32 is representable and retains the high-quality warning.
No coefficient was fitted to the observations. Single-precision calculation and
signed-hundredths repair encoding remain the previously verified implementation.

## Source and redistribution review

Reviewed the [Iron Gate mod statement](https://valheim.com/news/regarding-mods/)
and [Valheim EULA](https://valheim.com/eula/). Neither is treated as a blanket
license to redistribute game assets or proprietary code. This change distributes
only selected factual compatibility identifiers, classifications and numerical
parameters needed by the offline editor, not bundles, assemblies, full serialized
prefabs, localization tables, descriptions, artwork or audio. This continues the
existing project's factual-metadata approach; it does not assert a newly granted
game-content license. Broader distribution/legal clearance remains a release gate
under NFR-008; no release is created here.

Friendly labels/categories retain the pinned Jötunn source and
[MIT notice](references/Jotunn-LICENSE.txt); the independently verified one-name
override is identified above. Existing fch-decoder attribution is retained.
UnityPy 1.25.4 is an optional MIT research dependency. Neither UnityPy nor game
assets become application dependencies. No third-party website dataset was copied.

## Reproduction

Using the optional research environment, supply the local bundle path:

```text
python -m tools.audit_game_items <SoftRef/Bundles/c4210710> --output <local-audit.json>
python -m tools.build_item_data <local-audit.json> --output-dir <review-directory>
```

The first tool resolves actual registered ItemDrop components, validates limits,
rejects ambiguous duplicates, scans for unregistered ItemDrops and records input
digests. The second is explicitly pinned to the inspected build digest and
uses the existing catalog as the compatibility baseline. Review generated diffs
before copying files from the review directory. It is deterministic against
the current baseline. The full intermediate audit is local; the repository
contains the minimal runtime snapshot and complete classification ledger.

## Validation and remaining acceptance

The full Windows automated suite passes **99 tests, zero failures or skips**.
It covers all 927 stack boundaries and current-format round trips; independent
hash/name and q1/4/20/50/100 durability vectors; all three observed examples;
individual and transactional bulk repair; quality changes retaining durability;
unknown/missing-limit/missing-stat distinctions; legacy/current save formats;
Save As read-back, aliases, original bytes and item/character cheat preservation.
All committed fixtures are synthetic.

Only **one** `.fch` is currently present in the provided test folder. Read-only
validation identifies **33/33** records, with **0** unknown identities, **0**
missing limits and **0** missing statistical rows. SHA-512 validation and the
byte-identical no-op pass; original bytes were rechecked unchanged. No real save
was exported, committed or uploaded. The two earlier samples remain historical
evidence; this session does not claim to have rerun unavailable files.

The inspector shows current/max durability and percentage, explains unavailable
values, and puts prefab, raw serialized durability and provenance in optional
Advanced Item Details. The visible milestone is Alpha 0.3.1. Ammo now displays
its verified damage vector. No major layout change was made.

FR-018/030–033/054/072/097 and NFR-005 have implementation and automated evidence
within the stated set; FR-002–005/010/015–016/032/050–053/060 retain regression
coverage. FR-096 is partial for this session because only one sample is available.
FR-098/NFR-002/003 still need native Linux offline acceptance. FR-035/NFR-008
retain the distribution review gate. Unimplemented here: new codec versions,
mod support, gameplay verification of excluded candidates, projectile/world-level
damage, Alpha 0.4, releases and merges. Native in-game repair/resave acceptance
and broad item acquisition checks remain owner testing; the supplied observations
validate the three calculated maxima, not a new end-to-end game run.
