import unittest

from core.fch import Item, stable_hash
from core.item_stats import GAME_VERSION, SNAPSHOT, ItemStatistics, calculate_item_stats


def item(prefab, **fields):
    return Item(stable_hash(prefab), 0, 0, **fields)


class ItemStatisticsTests(unittest.TestCase):
    def test_verified_iron_sword_quality_vectors(self):
        sword = item("SwordIron", durability_raw=8125)
        for quality in (1, 4, 10, 25, 50, 100, 65535):
            with self.subTest(quality=quality):
                stats = calculate_item_stats(sword, quality)
                levels = quality - 1
                self.assertEqual(stats.maximum_durability, 200 + levels * 50)
                self.assertEqual(stats.damage, {"slash": 55 + levels * 6})
                self.assertEqual(stats.block, 21)
                self.assertEqual(stats.deflection, 20 + levels * 5)
        self.assertEqual((sword.quality, sword.durability_raw), (1, 8125))
        self.assertEqual(calculate_item_stats(sword, 65535).repair_raw(), 327689984)

    def test_channels_armor_and_blocking_context(self):
        staff = calculate_item_stats(item("StaffFireball"), 4)
        self.assertEqual(staff.damage, {"blunt": 120, "fire": 138})
        self.assertEqual(calculate_item_stats(item("AxeBronze"), 4).damage, {"slash": 55, "chop": 49})
        self.assertEqual(calculate_item_stats(item("HelmetIron"), 4).armor, 20)
        shield = calculate_item_stats(item("ShieldWood"), 3)
        self.assertEqual((shield.block, shield.block_with_skill(1), shield.deflection, shield.parry), (18, 27, 30, 1.5))
        self.assertAlmostEqual(shield.movement, -0.05)
        with self.assertRaises(ValueError):
            shield.block_with_skill(float("nan"))

    def test_missing_and_invalid_input_fails_closed(self):
        self.assertIsNone(calculate_item_stats(item("UnlistedModItem")))
        self.assertIsNone(calculate_item_stats(item("SwordIron", has_prefab=False)))
        for quality in (0, -1, 65536, 1.0, True):
            self.assertIsNone(calculate_item_stats(item("SwordIron"), quality))
        wood = calculate_item_stats(item("Wood"))
        self.assertIsNone(wood.maximum_durability)
        self.assertIsNone(wood.repair_raw())
        higher_world = calculate_item_stats(item("SwordIron", world_level=1), 4)
        self.assertIsNone(higher_world.armor)
        self.assertIsNone(higher_world.damage)
        self.assertEqual(higher_world.maximum_durability, 350)
        overflow = ItemStatistics(2**31, {}, 0, 0, 0, 0, 0, True)
        self.assertIsNone(overflow.repair_raw())

    def test_snapshot_provenance(self):
        self.assertEqual((GAME_VERSION, SNAPSHOT["steam_build"]), ("1.0.21", 26249040))
        self.assertEqual(SNAPSHOT["sha256"],
                         "84f55cfb24af51b9f0494fd9d1a355bf009e08545ff8ccf607c7d88d2e4e1ec8")
