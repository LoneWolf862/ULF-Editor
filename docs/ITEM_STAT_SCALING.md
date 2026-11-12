# Valheim item statistics and quality scaling

For the subsequent 1.0.21 reader/writer implementation and local save checks, see [Alpha 0.2.1 compatibility](ALPHA_0.2.1_COMPATIBILITY.md).

**Research date** 2026-11-12  
**Verified target** Valheim 1.0.21, Steam build 26249040, Windows. This report describes the installed build and proposes a data contract. Runtime acceptance remains open.

## Evidence and version boundary

The Steam app manifest identified build 26249040. The assembly's `Version` initializer identifies 1.0.21. I inspected managed CIL with dnfile 0.18.0 and dncil 1.0.2 and read selected prefab type trees with UnityPy 1.25.4. The assembly and bundle were read locally. No game code was run, no saves were opened, and no extracted binaries or art are included. [Iron Gate 1.0.21 patch notes, 2026-10-28](https://www.valheim.com/news/patch-1-0-21/).

| Local input | SHA-256 |
|---|---|
| `assembly_valheim.dll` | `9f959c0396ec4240d47fcbe5d0d062c428cc627244506db5ea567f9d77b2b769` |
| SoftRef bundle `c4210710` | `84f55cfb24af51b9f0494fd9d1a355bf009e08545ff8ccf607c7d88d2e4e1ec8` |

The installed writers emit **profile 47, player 34, inventory 110, skills 2**, as seen in `PlayerProfile.SavePlayerToDisk`, `Player.Save`, `Inventory.Save`, and `Skills.Save`. ULF accepts profile 44/46, player 23–33, inventory 109, and skills 2. Current files therefore need separate codec verification before editing. The installed `ItemData.Load` consumes a trailing byte for v109, but populates `m_cheated` from bit zero only at v110 or later. This is a concrete reason to keep versioned semantics and preserve the entire byte in ULF. Prior Alpha 0.1.1 playability and v109 round-trip evidence remain scoped to the previously tested save. [ULF stabilization evidence](ALPHA_0.1.1_RESEARCH.md), [pinned codec comparator](https://github.com/lanchelms/fch-decoder).

## Verified formulas

Let **q** be saved item quality, **n = max(0, q − 1)**, **w** the item's saved world level, and **s** the runtime Blocking skill factor. Formulas describe the item methods in the inspected assembly and use the loaded prefab's shared values. Typical coefficients are zero for properties that stay constant. Vanilla applicability is a separate question. For example, materials can carry default durability values while `m_useDurability` is false.

| Property | Verified method and computation | Quality dependence |
|---|---|---|
| Maximum durability | `ItemData.GetMaxDurability(q)` returns `m_maxDurability + n × m_durabilityPerLevel`. | Linear above q1, flat at and below q1. |
| Durability fraction | `ItemData.GetDurabilityPercentage` returns 1 if maximum equals zero, otherwise clamps current divided by maximum to [0, 1]. | Indirect through maximum. The editor should show unavailable for an inapplicable or unverified denominator and show an explicit warning if current exceeds maximum. |
| Generic and physical damage | `ItemData.GetDamage(q,w)` starts from `m_damages` and applies `DamageTypes.Add(m_damagesPerLevel, q−1)` at q>1. Channels include generic, blunt, slash, pierce, chop and pickaxe. | Each channel scales independently. Chop and pickaxe are tool damage channels. |
| Elemental and other damage | The same channel-wise addition applies to fire, frost, lightning, poison, spirit and the non-player channel. With w>0, the game then calls `DamageTypes.IncreaseEqually` with the world-level damage amount and the chop-special handling enabled. | Linear per channel at w=0. For positive w the post-quality mix determines the redistribution. |
| Armor | `ItemData.GetArmor(q,w)` returns `m_armor + n × m_armorPerLevel + w × Game.m_worldLevelGearBaseAC`. | Linear at fixed world level. Applicable armor depends on equipment rules. |
| Base block power / block armor | `ItemData.GetBaseBlockPower(q)` returns `m_blockPower + n × m_blockPowerPerLevel`. The item tooltip labels the base as block armor and separately shows the Blocking-adjusted figure. | Linear at fixed skill. |
| Blocking-adjusted value | `ItemData.GetBlockPower(q,s)` returns `base + base × s × 0.5`. `GetBlockPowerTooltip` obtains the Blocking factor from the current player. | Same quality coefficient as base, multiplied by the skill adjustment. Actual blocking also depends on timing, status and combat state. |
| Deflection force | `ItemData.GetDeflectionForce(q)` returns `m_deflectionForce + n × m_deflectionForcePerLevel`. | Linear if the coefficient is nonzero. Attack knockback is a separate property. |
| Parry / timed block | `ItemData.AddBlockTooltip` reads `m_timedBlockBonus` directly. `Humanoid.BlockAttack` checks the timed window, applies the bonus to its block calculation and allows a status-effect adjustment. | The prefab multiplier is quality-independent. The scaled block value can still change with quality. A value at or below one lacks the normal timed bonus in the observed check. |
| Movement modifier | The prefab `m_movementModifier` feeds the equipment modifier system. `Player.GetEquipmentMovementModifier` reads the cached movement channel. | No quality coefficient in this path. Display the item contribution separately from total movement speed and other effects. |
| Visual scale | `ItemData.GetScale(q)` returns a uniform scale of `1 + (q−1) × m_scaleByQuality`. `ItemDrop.SetQuality` assigns quality and updates the scale. | Linear where the coefficient is nonzero. Display only if useful for explaining an extreme-quality warning. |

The world-level damage routine first sums the quality-adjusted damage channels. For a positive sum **T**, it calculates the chop bonus using the original denominator T, then removes the original chop value from the denominator before increasing the remaining channels proportionally. The amount passed to the routine is `w × Game.m_worldLevelGearBaseDamage`. The `Game` constructor sets base AC to 38 and damage to 120, but these are constructor defaults. Extract effective values from the build's game prefab and verify denominator-zero cases before promising results for positive world levels. A first preview can support verified w=0 directly and show positive-world-level results as unavailable when context is incomplete.

Skill rolls, hit chains, attack multipliers, ammo/projectiles, area effects, target armor and resistance, blocking state and equipment effects sit outside these item methods. A staff's item damage vector can differ from the damage dealt by its projectile. Add explicit context before presenting an attack estimate. Display item durability, armor, damage and handling as calculated values beside their actual stored inputs.

### Local prefab and formula cross-checks

The following calculations use the inspected bundle's `ItemDrop.m_itemData.m_shared` fields at w=0. Values are static predictions, with no in-game observations attached.

| Prefab | Extracted coefficients | Predicted result |
|---|---|---|
| `SwordIron` | 55 slash, +6 per level. Durability 200, +50. Block 21, +0. Deflection 20, +5. | q4: 73 slash, 350 durability, 21 base block, 35 deflection. q100: 649 slash, 5,150 durability. |
| `AxeBronze` | 40 slash, +5. 40 chop, +3. Durability 125, +50. | q4: 55 slash, 49 chop, 275 durability. |
| `ShieldWood` | Block 6, +6. Deflection 20, +5. Parry ×1.5. Movement −5%. | q3: 18 base block, 27 at s=1, 30 deflection. Parry and movement coefficients stay fixed. |
| `HelmetIron` | Armor 14, +2. Durability 1,000, +200. | q4: 20 armor, 1,600 durability. |
| `StaffFireball` | 120 blunt, +0. 120 fire, +6. | q4 raw item vector: 120 blunt and 138 fire. Inspect projectile and area effects separately. |
| `Wood` | `m_useDurability=false`, despite nonzero default durability coefficients. | Durability and repair are inapplicable. |

The public database independently reports the Iron Sword's per-quality slash and durability and the Wood Shield's base/maximum block armor, parry and movement values. Treat both as cross-checks and retain the local method and asset evidence as authority. [Iron Sword data](https://valheim.source.gs/items/iron-sword/), [shield data](https://valheimdb.com/shields), [Valheim Database extraction provenance](https://valheimdb.com/about).

## Forge of Potential and extreme quality

- **Normal upgrades and Forge eligibility.** `InventoryGui.UpdateRecipeList` checks for an upgradeable recipe, a requirement marked `m_upgraderResource` at an upgrader station, and an appropriate current item quality. The observed Forge list filters out items below the ordinary quality maximum. `InventoryGui.DoCrafting` proposes current quality +1 and skips the ordinary `m_maxQuality` ceiling at a station marked `m_upgrader`. Eligibility and behavior here are specific to build 26249040. [Iron Gate's 1.0 release notes](https://www.valheim.com/news/valheim-1-0-has-arrived-/), [1.0.20 patch notes](https://www.valheim.com/news/patch-1-0-20/).
- **Outcome and state.** The crafting path reads `m_upgradeChance`, `m_breakChance` and the return fraction from the marked resource. It contains success, destruction and downgrade branches. All 16 inspected `Upgrader[0–7]{Armor,Weapon}` prefab records had thresholds approximately 0.65 and 1.0 and a return fraction approximately 0.35. In those records the break condition covers unsuccessful rolls, so the downgrade branch is not expected for the inspected vanilla resources. This differs from describing every possible recipe or mod. The build stores per-key upgrade seeds in player v34 and reads character name when initializing missing seeds. Preserve those records and avoid simulating or altering the outcome state in ULF.
- **Stat evaluation after success.** The successful crafting path creates an item at the new quality using the normal inventory path. The inspected item-stat methods have no Forge-dependent branch or quality-100 cutoff. Normal crafting maxima and Forge eligibility are separate from the arithmetic. Quality 100 has no verified status as a gameplay cap or recommendation. Broader downstream limits remain untested.
- **Save representation.** Current ULF permits deliberate qualities 1–65,535 in v109 and preserves raw legacy/unusual values during unrelated edits. The installed v110 methods also write/read a 16-bit optional quality, with implicit 1 when absent. The writer converts the runtime integer to unsigned 16 bits, so values beyond that representation can lose high bits on serialization. Treat 65,535 as a format boundary, never as a safe gameplay maximum.
- **Numerics.** The inspected stat methods use single-precision operands and no high-quality upper clamp. All unsigned 16-bit qualities are exactly representable as float32 integers, but calculated results may lose increments as magnitude grows. The durability writer multiplies the runtime value by 100 and converts to signed int32. The loaded value is divided by 100. Large values can lose hundredth precision well before integer range, and out-of-range conversion is unsafe. Use a build-matched numeric policy for computed repairs and reject unrepresentable results. For example, the Iron Sword's computed q65,535 maximum is 3,276,900, where adjacent float32 values are 0.25 apart. Extreme quality can affect visuals, combat, persistence and downstream systems even if the item-stat expression is finite.
- **Repair scope.** `InventoryGui.RepairOneItem` sets current durability to `GetMaxDurability` and raises Crafting skill in game. `CanRepair` checks repairability and station/recipe context. A desktop repair should stage only the durability change. Explain that it edits the save directly. Leave skill XP, world state, cheat metadata and other fields untouched.

## Proposed offline database

Use deterministic UTF-8 JSON snapshots initially. Store the game build and schema revision separately. Resolve an exact build or a reviewed compatibility mapping. Save layout versions alone do not identify a game patch. Allow a user-selected source snapshot if a build cannot be inferred, with explicit provenance and write-authority rules.

| Record | Required fields and rules |
|---|---|
| Manifest | Schema version, game version, Steam build/platform, snapshot ID, extraction tool revision, assembly and asset hashes, verification date, coverage counts and exclusions, source/license ledger, formula rule set and fixture identifiers. |
| Prefab identity | Canonical prefab, signed stable hash, localization token and approved labels, actual item type, inventory eligibility and evidence, known variants and applicability, definition source. Hash collisions are ambiguous and block writes. |
| Limits | Verified stack maximum, ordinary max quality, durability-used and repairability flags, optional equipment slot and hands, source version per field. Distinguish zero, inapplicable and unknown. |
| Stat coefficients | Base and per-level durability, armor, each damage channel, block and deflection. Record timed block bonus, movement contribution, visual scaling and optional world-level context. Keep recipe and attack/projectile data in separate records. |
| Evidence | Per field or verified field group record extraction target, named method/field, source digest, status and write eligibility. Suggested statuses are verified, unverified, conflicting, and inapplicable. Unknown metadata stays null. |
| Optional user overlays | Explicit namespace, mod identity/version and target build, stable-hash/ID claims, versioned data-only schema and evidence. An imported claim is not automatically verified. No scripts, plugins, remote endpoints or silent overrides. |

## Extraction and verification procedure

1. **Pin inputs.** Locate a user-supplied installation read-only, confirm the app manifest and embedded game version, and hash the assembly and required bundles. Record platform and extraction-tool versions. The optional local research tool remains separate from the runtime. [Iron Gate Asset Bundle FAQ](https://valheim.com/support/modding-faq-for-the-asset-bundle-update-0-217-40/), [UnityPy](https://github.com/K0lb3/UnityPy), [dnfile](https://github.com/malwarefrank/dnfile), [dncil](https://github.com/mandiant/dncil).
2. **Enumerate definitions.** Resolve the actual ObjectDB and its registered items and recipes through the local SoftRef index and bundle dependencies. Follow ItemDrop components to shared fields and resolve localization/variant metadata independently. Separate real player inventory candidates from attack proxies, dummies, placeholders and references that merely have icons. The inspected sample bundle contains the eight checked item prefabs and 16 upgrader records. ObjectDB enumeration across dependencies was not performed here. [Valheim Database extraction methodology](https://valheimdb.com/about), [Jötunn item index](https://valheim-modding.github.io/Jotunn/data/objects/item-list.html).
3. **Review and publish deterministically.** Hash and sort rows, validate types and signed hash uniqueness, compare with the 821-entry baseline, classify gaps and record contradictions. Compare field-by-field against pinned inventory-valid references and representative independent extracts. Never infer stack sizes from appearance or category. Require a review and snapshot diff before bundled updates.
4. **Verify formulas and serialization separately.** Use numeric fixtures for q1, q2, ordinary maxima, above-vanilla, 100 and 65,535, world-level zero and positive, nonzero chop, zero totals, zero coefficients, missing metadata and mod conflicts. Check float32 order and signed hundredth conversion, thresholds and overflow. Codec fixtures cover 46/33/109/2 and proposed 47/34/110/2 independently.
5. **Measure runtime behavior.** On a matching offline build with disposable local saves, compare in-game item tooltips, persisted values after reload/resave, repairs and equip/unequip. Test plausible high values before extreme cases. Confirm exact source digests, the continued preservation of unknown and protected bytes, and the same editor workflows on Windows 10 and Linux. Keep game and personal saves local.

## Source and redistribution decisions

| Source | Intended use |
|---|---|
| Installed Valheim assembly and asset bundles | Local static analysis and extraction of the minimum numerical facts needed for verification. Keep assemblies, CIL dumps, bundles, artwork, game text and raw asset trees out of distribution. Review terms and dataset rights before bundling any larger snapshot. Offer user-local extraction if distribution rights remain unresolved. [Iron Gate's modding statement](https://valheim.com/news/regarding-mods/). |
| valheim.source.gs and Valheim Database | Corroborate selected rows and methodology. No dataset reuse grant established in this review. Avoid scraping or mirroring their tables, prose or art. [Source.gs](https://valheim.source.gs/), [Valheim Database attribution](https://valheimdb.com/about). |
| WackysDatabase and Jötunn | Reference for data modeling and tooling, especially variant/attack fields and mod overlays. WackysDatabase's MIT license covers its licensed project code and gives no independent rights to game content. Keep existing pinned Jötunn attribution. No dependency or new imported code proposed. [WackysDatabase source and license](https://github.com/Wacky-Mole/WackysDatabase), [Jötunn project](https://github.com/Valheim-Modding/Jotunn). |
| fch-decoder | Pinned MIT-licensed codec and inventory-valid TSV are useful for version 46 and baseline comparison. Its documented format matrix does not establish current writer compatibility. Preserve existing notices and verify provenance of any additional content. [Project and license](https://github.com/lanchelms/fch-decoder), [ULF retained notice](references/fch-decoder-LICENSE.txt). |

## Open questions

- Locate the complete ObjectDB item and recipe graph, classify eligible inventory items, and verify effective world-level constants and variant-specific overrides. Verify actual projectile/attack layers separately.
- Confirm q>ordinary maximum behavior through load, tooltips, equip, repair, combat, world transfers and game resave, including the points where precision or unrelated caps become visible. No runtime quality ceiling was established.
- Verify the current profile/player/inventory layouts with synthetic noncanonical fixtures and disposable saves from build 26249040. Confirm real-world pocket geometry and the supported writable capacity before widening placement.
- Confirm repair quantization and maximum durability preservation at extreme levels. Establish a repeatable runtime comparison on both platforms before approving calculated writes.
