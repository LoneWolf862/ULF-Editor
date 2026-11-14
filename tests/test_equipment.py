"""Pinned saved-slot rules; not a claim about live game equip conditions."""

from pathlib import Path
import unittest

from core.equipment import equipment_changes, equip_item
from core.fch import Character, FormatError, Item, stable_hash
from desktop.session import Session
from synthetic import current_character_bytes


def character(*prefabs):
    return Character(current_character_bytes(item_bytes=[
        Item(stable_hash(p), n, 0, durability_raw=50000).to_bytes() for n, p in enumerate(prefabs)]))


class EquipmentTests(unittest.TestCase):
    def test_fr090_one_handed_and_shield_coexist_two_handed_displaces_both(self):
        c = character("SwordIron", "ShieldWood", "AtgeirBronze")
        equip_item(c, c.items[0], True)
        equip_item(c, c.items[1], True)
        self.assertEqual([i.equipped for i in c.items], [True, True, False])
        before = c.serialize()
        self.assertEqual(equipment_changes(c, c.items[2], True), ((0, False), (1, False), (2, True)))
        self.assertEqual(c.serialize(), before)
        equip_item(c, c.items[2], True)
        self.assertEqual([i.equipped for i in c.items], [False, False, True])

    def test_fr090_armor_accessory_ammo_conflicts(self):
        for left, right in [("HelmetIron", "HelmetBronze"), ("CapeWolf", "CapeDeepNorth"),
                            ("ArmorIronChest", "ArmorBronzeChest"), ("ArmorIronLegs", "ArmorBronzeLegs"),
                            ("Wishbone", "BeltStrength"), ("ArrowWood", "ArrowFire")]:
            with self.subTest(slot=left):
                c = character(left, right)
                c.items[0].tail = 5
                equip_item(c, c.items[0], True)
                equip_item(c, c.items[1], True)
                self.assertEqual([i.equipped for i in c.items], [False, True])
                self.assertEqual(c.items[0].tail, 5)

    def test_fr090_unsupported_broken_dlc_custom_and_unknown_fail_closed(self):
        for prefab in ("Wood", "Torch", "HelmetOdin", "CapeOdin", "UnknownEquipment"):
            with self.subTest(prefab=prefab):
                c = character(prefab)
                before = c.serialize()
                with self.assertRaises(FormatError):
                    equip_item(c, c.items[0], True)
                self.assertEqual(c.serialize(), before)
        for field, value in [("durability_raw", 0), ("custom", [("mod", "opaque")]), ("world_level", 1)]:
            c = character("SwordIron")
            setattr(c.items[0], field, value)
            before = c.serialize()
            with self.assertRaises(FormatError):
                equip_item(c, c.items[0], True)
            self.assertEqual(c.serialize(), before)

    def test_fr090_unknown_equipped_item_preserved_blocks_new_equip(self):
        c = character("SwordIron", "UnknownEquipment")
        c.items[1].equipped = True
        before = c.serialize()
        with self.assertRaises(FormatError):
            equip_item(c, c.items[0], True)
        self.assertEqual(c.serialize(), before)

    def test_fr020_equipment_conflicts_one_history_entry_and_undo(self):
        c = character("SwordIron", "ShieldWood", "AtgeirBronze")
        c.items[0].equipped = c.items[1].equipped = True
        c = Character(c.serialize())
        s = Session(c, Path("synthetic.fch"))
        before = s.working.serialize()
        plan, proposed = s.preview_operation(("item", 2), "equip", (True,))
        self.assertEqual([i.equipped for i in proposed.values()], [False, False, True])
        s.apply_operation(plan)
        after = s.working.serialize()
        self.assertEqual(len(s.history.past), 1)
        self.assertEqual(len(s.changes()), 3)
        s.undo()
        self.assertEqual(s.working.serialize(), before)
        s.redo()
        self.assertEqual(s.working.serialize(), after)

    def test_fr072_stale_preview_and_direct_flag_edit_rejected(self):
        s = Session(character("SwordIron", "ShieldWood"), Path("synthetic.fch"))
        plan, _ = s.preview_operation(("item", 0), "equip", (True,))
        s.edit_item(("item", 0), {"quality": 2})
        s.undo()  # Even returning to identical bytes requires a new preview.
        before = s.working.serialize()
        with self.assertRaises(FormatError):
            s.apply_operation(plan)
        with self.assertRaises(FormatError):
            s.edit_item(("item", 0), {"equipped": True})
        self.assertEqual(s.working.serialize(), before)
