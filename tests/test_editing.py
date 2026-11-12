import copy
import unittest
from types import SimpleNamespace

from core.editing import apply_skills, apply_item
from core.fch import FormatError, Character, Item, stable_hash
from synthetic import character_bytes


class SkillTransactionTests(unittest.TestCase):
    def setUp(self):
        self.character = SimpleNamespace(
            roundtrip=True,
            skills=[[1, 10.123456789, 0.123456789], [2, 20.0, 7.0]],
        )

    def test_fr043_invalid_later_change_preserves_entire_batch(self):
        original = copy.deepcopy(self.character.skills)
        with self.assertRaises(FormatError):
            apply_skills(self.character, [(1, 40, None), (2, 101, None)])
        self.assertEqual(original, self.character.skills)

    def test_fr042_level_edit_preserves_experience(self):
        apply_skills(self.character, [(1, 50, None)])
        self.assertEqual(self.character.skills[0], [1, 50, 0.123456789])
        self.assertEqual(self.character.skills[1], [2, 20, 7])

    def test_fr005_no_changes_preserve_values(self):
        original = copy.deepcopy(self.character.skills)
        apply_skills(self.character, [])
        self.assertEqual(original, self.character.skills)

    def test_fr041_nonfinite_and_invalid_values_are_atomic(self):
        for value in (float("nan"), float("inf"), -1, 101):
            with self.subTest(value=value):
                original = copy.deepcopy(self.character.skills)
                with self.assertRaises(FormatError):
                    apply_skills(self.character, [(1, value, None)])
                self.assertEqual(original, self.character.skills)

    def test_fr042_explicit_experience_edit(self):
        apply_skills(self.character, [(1, None, 12.5)])
        self.assertEqual(self.character.skills[0], [1, 10.123456789, 12.5])

    def test_fr004_failed_roundtrip_blocks_edits(self):
        self.character.roundtrip = False
        with self.assertRaises(FormatError):
            apply_skills(self.character, [(1, 50, None)])

    def test_fr043_duplicate_skill_records_are_not_ambiguously_edited(self):
        self.character.skills.append([1, 15.0, 1.0])
        original = copy.deepcopy(self.character.skills)
        with self.assertRaisesRegex(FormatError, "ambiguous"):
            apply_skills(self.character, [(1, 50, None)])
        self.assertEqual(self.character.skills, original)

    def test_fr041_invalid_types_are_rejected(self):
        for value in (True, "10", None):
            with self.subTest(value=value):
                with self.assertRaises(FormatError):
                    apply_skills(self.character, [(value, 50, None)])


class ItemTransactionTests(unittest.TestCase):
    def setUp(self):
        self.character = Character(character_bytes())

    def test_fr012_quantity_boundaries(self):
        item = self.character.items[0]
        for valid in (1, 50):
            apply_item(self.character, item, {"stack": valid})
            self.assertEqual(item.stack, valid)
        for invalid in (0, -1, 51, 65536, 1.5):
            with self.subTest(invalid=invalid):
                before = item.to_bytes()
                with self.assertRaises(FormatError):
                    apply_item(self.character, item, {"stack": invalid, "quality": 7})
                self.assertEqual(item.to_bytes(), before)

    def test_fr013_add_defaults_and_collision(self):
        self.character.add("Wood", 1, 0, quality=65535, stack=50)
        added = self.character.items[-1]
        self.assertFalse(added.cheated)
        self.assertEqual(added.prefab_hash, stable_hash("Wood"))
        with self.assertRaises(FormatError):
            self.character.add("Wood", 1, 0)
        with self.assertRaises(FormatError):
            self.character.add("MisspelledPrefab", 2, 0)

    def test_fr013_rejects_invalid_creation_coordinates_and_quantities(self):
        for x,y in ((-1,0),(8,0),(0,6),(1.5,0),(True,0)):
            with self.subTest(x=x,y=y), self.assertRaises(FormatError):
                self.character.add("Wood",x,y)
        for stack in (0,-1,51,65536,True,1.5):
            with self.subTest(stack=stack), self.assertRaises(FormatError):
                self.character.add("Wood",1,0,stack=stack)

    def test_fr032_unknown_item_preserved(self):
        unknown = Item(123, 2, 0, custom=[("opaque", "value")], tail=7)
        self.character.items.append(unknown)
        original = unknown.to_bytes()
        with self.assertRaises(FormatError):
            apply_item(self.character, unknown, {"quality": 10})
        self.assertEqual(unknown.to_bytes(), original)

    def test_fr011_quality_and_durability_boundaries(self):
        item = self.character.items[0]
        apply_item(self.character, item, {"quality": 65535, "durability_raw": 12345})
        self.assertEqual(item.quality, 65535)
        self.assertEqual(item.durability_raw, 12345)
        for quality in (0, 65536):
            with self.assertRaises(FormatError):
                apply_item(self.character, item, {"quality": quality})
