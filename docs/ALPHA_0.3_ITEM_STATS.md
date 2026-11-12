# Alpha 0.3 item statistics and repair

**2026-11-12 · Ready for owner testing for the supported prefabs**

## Implementation and coverage

The selected-item inspector shows stored durability, calculated maximum, and a percentage meter. An unapplied quality edit updates the calculation while leaving stored durability untouched. Weapon and shield previews show applicable damage channels, base block, deflection, parry, and movement. Armor previews show armor and movement. The preview describes item statistics before combat effects.

Repair stages a durability-only edit at the item's applied quality. Repair All shows the proposed changes and the reasons items were skipped, then requests confirmation. The session validates the preview against the current working revision and drafts, applies commands to a private candidate, and publishes the candidate only after all changes validate and serialize. Both actions feed the existing Review and verified Save As workflow. Neither operation grants Crafting XP. Source protection, item identity, unknown-record handling, and stack validation use the existing engine.

| Coverage | Count | Scope |
|---|---:|---|
| Prefabs in the bundled statistics snapshot | 8 | All eight also exist in the existing 821-entry catalog. |
| Applicable verified durability | 6 | Bronze Axe, Iron Sword, Wood Shield, Iron Helmet, Staff of Embers, Breastplate of Ask. |
| Applicable verified item damage | 3 | Bronze Axe, Iron Sword, Staff of Embers. |
| Applicable verified armor | 2 | Iron Helmet, Breastplate of Ask. |
| Applicable verified blocking | 4 | Bronze Axe, Iron Sword, Wood Shield, Staff of Embers. |
| Durability inapplicable | 2 | Wood and Thunderblood Essence. |

Coverage counts reflect the applicable values shown in the inspector. Some prefab definitions also contain defaults for fields outside their item category. Staff damage is the item's vector and does not predict the projectile or damage dealt.

## Verified scaling and precision

For quality q in 1–65,535, the service uses base plus (q − 1) times the verified per-level coefficient for durability, each damage channel, armor, base block, and deflection. It rounds intermediate values to float32. Blocking adjustment is base plus half the product of base and the Blocking skill factor. The inspector shows base block because runtime skill and status effects can change the effective value. The prefab parry multiplier and movement modifier are constant with quality. Armor and damage are unavailable for nonzero item world level because the effective world-level context has not been verified.

The percentage uses the game's decoded float32 durability and clamps the ratio to 0–100%. The inspector separately flags stored durability above the calculated maximum. Repair uses the game's float32 maximum times 100, truncated to a signed int32. Targets outside the representable positive range are skipped. At quality 65,535 an Iron Sword has a calculated maximum of 3,276,900 and encodes a repair target of 327,689,984 raw hundredths. This precision difference and the 16-bit quality boundary describe the codec and arithmetic. In-game behavior at extreme quality remains unverified. [Assembly evidence and formula derivation](ITEM_STAT_SCALING.md), [Iron Sword comparison, 1.0.20](https://valheim.source.gs/items/iron-sword/).

## Offline data and regeneration

`core/item_stats_1_0_21.json` contains schema version 1, Valheim 1.0.21, Steam build 26249040, extractor version, bundle name and SHA-256, verification status, and selected numerical coefficients. The statistics module resolves unambiguous prefab hashes against the existing catalog and suppresses rows that disagree with its verified stack limit. The inspector obtains localized names and categories from the existing offline catalog. The application uses no network, UnityPy, or game assemblies at runtime.

Use the existing optional UnityPy 1.25.4 research environment and run the following with a local, read-only bundle path.

```text
python tools/inspect_game_items.py --statistics <bundle> SwordIron AxeBronze ShieldWood HelmetIron Wood StaffFireball ArmorAshlandsMediumChest OrbThunderBlood
```

The command emits deterministically sorted JSON with the bundle digest and extractor version. Record the verified schema, game version, Steam build, and verification status after checking the installed manifest, assembly methods, and source digests. Compare new coefficients against the reviewed snapshot and existing stack limits before promoting a replacement. Update the regression vectors for any confirmed formula or coefficient change.

The bundled data contains a small set of factual coefficients inspected from local bundle `c4210710`. The project distributes no extracted game code, artwork, full assets, or copied third-party database. UnityPy remains an optional MIT-licensed research tool. Iron Gate's mod statement does not grant redistribution rights for game assets. Complete a separate provenance and distribution review before significantly expanding the dataset. [Iron Gate modding statement](https://valheim.com/news/regarding-mods/), [UnityPy license](https://github.com/K0lb3/UnityPy).

## Compatibility, requirements, and acceptance

All 78 baseline tests passed at the Alpha 0.2.1 tag before implementation. The owner confirmed completion of Alpha 0.2.1 in-game testing and approved that release. The compatibility report predates that confirmation and does not contain per-case manual results. Alpha 0.3 in-game results remain outstanding.

The full Windows suite now passes **87 tests, zero failures or skips**. New tests cover quality 1, 4, 10, 25, 50, 100 and 65,535, invalid quality and blocking factors, missing metadata, world-level omissions, durability quantization, live preview, repair/export, bulk confirmation and cancellation, late-failure rollback, stale previews, and unchanged equipment, crafter, custom, cheat and skill data. Legacy profiles and current 47 / 34 / 110 / 2 retain codec and export coverage. [Alpha 0.2.1 compatibility](ALPHA_0.2.1_COMPATIBILITY.md).

- **FR-018, FR-054, FR-072** are covered for the supported workflows through exact stored values, preview, and validated edits.
- **FR-002–005, FR-012, FR-015–016, FR-032, FR-050–053, FR-060, FR-080** retain existing safety and separation coverage.
- **FR-030/035 and NFR-002/003/008** remain partial at release level. Full catalog coverage, Linux runtime acceptance, and a distribution audit are open.
- **Proposed amendments FR-101–103** in the feature expansion plan describe build-scoped stats, durability, and bulk repair. This milestone implements the repair portion of proposed FR-103. These proposals remain pending owner approval as amendments to the official baseline. [Proposed requirements](FEATURE_EXPANSION_PLAN.md).

Calculated repair is enabled for the current inventory v110 format and the 1.0.21 snapshot. Legacy saves retain existing editing and Save As support and can display labeled 1.0.21 estimates. The format alone cannot identify every game patch or mod configuration. Unknown items, unsupported stats, unapplied item drafts, ambiguous positions, and items at or above the repair target are skipped.

### Outstanding owner tests

1. On a disposable offline 1.0.21 character, compare the supported sword, shield and armor tooltips at ordinary qualities. Change quality, export, and verify stored durability is unchanged.
2. Repair one damaged item, preview and cancel a batch, then confirm a batch. Reopen the exported copy in ULF and Valheim, resave in-game, and check the intended durability, equipment, other metadata, and original file digest.
3. Check high-quality durability quantization in a separate disposable save. Repeat the native interface and offline workflow on Windows 10 and Linux.
