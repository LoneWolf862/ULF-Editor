"""Synthetic regression gates for the audited Alpha 0.3.1 dataset."""

from copy import deepcopy
import json
from pathlib import Path
import unittest

from core.catalog import CATALOG
from core.editing import apply_item
from core.fch import Character, FormatError, Item, stable_hash
from core.item_stats import SNAPSHOT, calculate_item_stats
from desktop.item_catalog import BY_PREFAB, search_catalog
from synthetic import current_character_bytes
from tools.audit_game_items import classification
from tools.build_item_data import build


ROOT = Path(__file__).resolve().parents[1]
REPORT = json.loads((ROOT / "docs/references/item-coverage-1.0.21.json").read_text(encoding="utf-8"))


class ItemCoverageTests(unittest.TestCase):
    def test_fr030_registry_partition_and_complete_offline_coverage(self):
        eligible = set(REPORT["inventory_prefabs"])
        excluded = REPORT["excluded"]
        self.assertEqual(len(eligible), 927)
        self.assertEqual(len(eligible) + len(excluded), 1522)
        self.assertFalse(eligible.intersection(excluded))
        self.assertEqual(sum(REPORT["counts"].values()), 1522)
        self.assertEqual(set(SNAPSHOT["items"]), eligible)
        self.assertEqual(set(CATALOG), eligible | set(REPORT["retained_legacy_entries"]))
        self.assertEqual(len(CATALOG), 1049)
        for prefab in eligible:
            with self.subTest(prefab=prefab):
                self.assertEqual(CATALOG[prefab]["max_stack"], SNAPSHOT["items"][prefab]["max_stack"])
                self.assertEqual(CATALOG[prefab]["max_quality"], SNAPSHOT["items"][prefab]["max_quality"])
                self.assertIn("1.0.21", BY_PREFAB[prefab].source)
                self.assertIsNotNone(calculate_item_stats(Item(stable_hash(prefab), 0, 0)))

    def test_fr030_reported_identities_and_names(self):
        for prefab, name, identifier, maximum in (
            ("CapeDeepNorth", "Moose Hide Cape", 1865694990, 1),
            ("Ice", "Ice", -466768857, 50),
            ("SwordGold_BloodLightning", "Thunderblood Sword", 1690651452, 1),
            ("StaffThunderBlood", "Lightning Strike", -677306358, 1),
        ):
            with self.subTest(prefab=prefab):
                self.assertEqual(stable_hash(prefab), identifier)
                self.assertEqual(search_catalog(name, None)[0].prefab, prefab)
                self.assertEqual(BY_PREFAB[prefab].maximum_stack, maximum)

    def test_fr012_audited_stack_boundaries_and_current_format_roundtrip(self):
        for prefab in REPORT["inventory_prefabs"]:
            with self.subTest(prefab=prefab):
                maximum = CATALOG[prefab]["max_stack"]
                item = Item(stable_hash(prefab), 0, 0, stack=maximum, custom=[("fixture", "preserve")], tail=5)
                character = Character(current_character_bytes(item_bytes=[item.to_bytes()]))
                self.assertTrue(character.roundtrip)
                before = character.serialize()
                for invalid in (0, maximum + 1, 65536):
                    with self.assertRaises(FormatError):
                        apply_item(character, character.items[0], {"stack": invalid})
                    self.assertEqual(character.serialize(), before)
                apply_item(character, character.items[0], {"stack": 1})
                reopened = Character(character.serialize())
                self.assertEqual(reopened.items[0].stack, 1)
                self.assertEqual(reopened.items[0].custom, item.custom)
                self.assertEqual(reopened.items[0].tail, 5)

    def test_fr018_independent_observations_and_high_quality_vectors(self):
        examples = (("SwordGold_BloodLightning", 8, 71500, 750),
                    ("StaffThunderBlood", 8, 73300, 750),
                    ("CapeDeepNorth", 32, 272700, 2750))
        for prefab, quality, raw, maximum in examples:
            item = Item(stable_hash(prefab), 0, 0, quality=quality, durability_raw=raw)
            before = deepcopy(item)
            stats = calculate_item_stats(item)
            self.assertEqual(stats.maximum_durability, maximum)
            self.assertEqual(stats.repair_raw(), maximum * 100)
            self.assertAlmostEqual(stats.durability_fraction(raw), raw / (maximum * 100), places=6)
            for q in (1, 4, 20, 50, 100):
                expected = (1200 if prefab == "CapeDeepNorth" else 400) + (q - 1) * 50
                self.assertEqual(calculate_item_stats(item, q).maximum_durability, expected)
            self.assertEqual(item, before)
        cape = calculate_item_stats(Item(stable_hash("CapeDeepNorth"), 0, 0, quality=32))
        self.assertEqual(cape.armor, 74)
        sword = calculate_item_stats(Item(stable_hash("SwordGold_BloodLightning"), 0, 0, quality=8))
        self.assertEqual(sword.damage, {"slash": 250, "lightning": 80})
        self.assertEqual((sword.block, sword.deflection, sword.parry), (66, 55, 2))

    def test_fr030_extractor_separates_internal_and_inventory_objects(self):
        shared = {"m_itemType": 1, "m_icons": [{"m_PathID": 1}]}
        self.assertEqual(classification("Ice", "Assets/GameElements/Items/materials/Ice.prefab", shared, True), "inventory")
        for name, path, data, rigidbody, expected in (
            ("Effect", "fx", None, False, "no_itemdrop"),
            ("Hair", "hair", {**shared, "m_itemType": 10}, False, "customization"),
            ("Attack", "attack", {**shared, "m_icons": []}, True, "no_inventory_icon"),
            ("Attack", "attack", {**shared, "m_icons": [{"m_PathID": 0}]}, True, "no_inventory_icon"),
            ("FW_Axe", "Assets/Characters/FallenWarrior/Equipment/FW_Axe.prefab", shared, True, "npc_equipment_or_attack"),
            ("Feast", "Assets/GameElements/Pieces/Feast.prefab", shared, False, "placed_object"),
            ("CapeTest", "items", shared, True, "internal_or_test"),
            ("Unresolved", "", shared, True, "unresolved_asset_path"),
        ):
            self.assertEqual(classification(name, path, data, rigidbody), expected)

    def test_fr030_builder_rejects_unverified_build(self):
        with self.assertRaisesRegex(ValueError, "reviewed"):
            build({"sha256": "unverified", "audit_version": 1}, {}, "")

    def test_fr018_inapplicable_and_missing_stats_are_distinct(self):
        self.assertIsNone(calculate_item_stats(Item(stable_hash("UnknownFixture"), 0, 0)))
        self.assertIsNone(calculate_item_stats(Item(stable_hash("Beard1"), 0, 0)))
        ice = calculate_item_stats(Item(stable_hash("Ice"), 0, 0, stack=3))
        self.assertIsNotNone(ice)
        self.assertIsNone(ice.maximum_durability)
        self.assertIsNone(ice.repair_raw())

    def test_fr033_missing_display_name_does_not_erase_verified_identity(self):
        entry = BY_PREFAB["IceSkates"]
        self.assertEqual(entry.name, "IceSkates")
        self.assertIn("Display name unavailable", entry.source)
        self.assertEqual(entry.maximum_stack, 1)
        self.assertIsNotNone(calculate_item_stats(Item(stable_hash(entry.prefab), 0, 0)))
        self.assertEqual(search_catalog("Kindled Ribs", None)[0].prefab, "FaderDrop")
