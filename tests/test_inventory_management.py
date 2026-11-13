"""Synthetic Alpha 0.4 transactions, history and safe-export acceptance."""

from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from core.fch import Character, FormatError, Item, stable_hash
from core.export import export_character
from core.inventory_ops import move_item, duplicate_item, replace_item
from desktop.session import Session
from synthetic import current_character_bytes


def fixture():
    rows = [Item(stable_hash("SwordIron"), 0, 0, quality=32, durability_raw=109210,
                 equipped=True, crafter_id=42, crafter_name="Synthetic"),
            Item(stable_hash("Wood"), 1, 0, stack=3),
            Item(stable_hash("ShieldWood"), 2, 0, durability_raw=100),
            Item(-7654321, 3, 0, custom=[("mod", "opaque")], tail=5)]
    return current_character_bytes(item_bytes=[i.to_bytes() for i in rows])


class InventoryManagementTests(unittest.TestCase):
    def setUp(self):
        self.raw = fixture()
        self.session = Session(Character(self.raw), Path("synthetic.fch"))

    def cycle(self, action):
        s = self.session
        before = s.working.serialize()
        count = len(s.history.past)
        action()
        after = s.working.serialize()
        self.assertNotEqual(before, after)
        self.assertEqual(len(s.history.past), count + 1)
        s.undo()
        self.assertEqual(s.working.serialize(), before)
        s.redo()
        self.assertEqual(s.working.serialize(), after)

    def test_fr020_all_supported_operations_restore_exact_bytes(self):
        actions = [
            lambda s: s.edit_item(("item", 0), {"quality": 65535}),
            lambda s: s.edit_item(("item", 1), {"stack": 4}),
            lambda s: s.edit_item(("item", 0), {"durability_raw": 109211}),
            lambda s: s.edit_item(("item", 0), {"equipped": False}),
            lambda s: s.add_item("Stone", (4, 0), 1, 1, {}),
            lambda s: s.remove_item(("item", 1)),
            lambda s: s.apply_repairs(s.repair_plan([("item", 0)])),
            lambda s: s.apply_repairs(s.repair_plan()),
            lambda s: s.organize(("item", 0), "move", (4, 0)),
            lambda s: s.organize(("item", 0), "swap", (1, 0)),
            lambda s: s.organize(("item", 0), "duplicate", (4, 0)),
            lambda s: s.organize(("item", 0), "replace", ("AxeBronze", 8, 1)),
            lambda s: s.organize(("item", 1), "fill"),
            lambda s: s.apply_skill_batch([(1, 40, 5), (2, 30, 0)]),
        ]
        for index, action in enumerate(actions):
            with self.subTest(operation=index):
                self.setUp()
                self.cycle(lambda: action(self.session))

    def test_fr019_move_swap_preserve_all_noncoordinate_bytes(self):
        c = self.session.working
        c.items[0].custom = [("synthetic", "opaque")]
        c.items[0].tail = 255
        before = [i.to_bytes() for i in c.items]
        move_item(c, c.items[0], (1, 0), swap=True)
        for old, item in zip(before, c.items):
            new = item.to_bytes()
            self.assertEqual(old[:4] + old[6:], new[:4] + new[6:])
        self.assertEqual([(i.x, i.y) for i in c.items[:2]], [(1, 0), (0, 0)])

    def test_fr019_invalid_moves_and_unknowns_are_atomic(self):
        c = self.session.working
        for destination, swap in [((-1, 0), False), ((8, 0), False), ((0, 99), False),
                                  ((True, 0), False), ((1, 0), False), ((4, 0), True),
                                  ((3, 0), True), ((0, 0), False)]:
            before = c.serialize()
            with self.subTest(destination=destination, swap=swap), self.assertRaises(FormatError):
                move_item(c, c.items[0], destination, swap=swap)
            self.assertEqual(c.serialize(), before)
        with self.assertRaises(FormatError):
            move_item(c, c.items[3], (4, 0))
        c.items[1].x = 0
        before = c.serialize()
        with self.assertRaises(FormatError):
            move_item(c, c.items[0], (4, 0))
        self.assertEqual(c.serialize(), before)

    def test_fr013_duplicate_preserves_original_and_documented_metadata(self):
        c = self.session.working
        before = [i.to_bytes() for i in c.items]
        new = duplicate_item(c, c.items[0], (4, 0))
        self.assertEqual([i.to_bytes() for i in c.items[:-1]], before)
        expected = deepcopy(c.items[0])
        expected.x, expected.equipped, expected.origin_index = 4, False, None
        self.assertEqual(new.to_bytes(), expected.to_bytes())
        self.assertEqual(new.tail, 0)
        self.assertEqual(new.crafter_id, 42)

    def test_fr013_opaque_copy_rejected_without_mutation(self):
        for field, value in [("custom", [("mod", "data")]), ("tail", 1), ("tail", 128),
                             ("variant", 2), ("world_level", 1), ("stack", 2),
                             ("quality", 0), ("durability_raw", -1)]:
            with self.subTest(field=field):
                c = Character(self.raw)
                setattr(c.items[0], field, value)
                before = c.serialize()
                for action in (lambda: duplicate_item(c, c.items[0], (4, 0)),
                               lambda: replace_item(c, c.items[0], "AxeBronze")):
                    with self.assertRaises(FormatError):
                        action()
                    self.assertEqual(c.serialize(), before)

    def test_fr013_full_inventory_duplicate_rejected(self):
        rows = [Item(stable_hash("Wood"), x, y) for y in range(6) for x in range(8)]
        c = Character(current_character_bytes(item_bytes=[i.to_bytes() for i in rows]))
        before = c.serialize()
        with self.assertRaises(FormatError):
            duplicate_item(c, c.items[0], (7, 5))
        self.assertEqual(c.serialize(), before)

    def test_fr054_replacement_explicit_defaults_and_maximum(self):
        c = self.session.working
        others = [i.to_bytes() for i in c.items[1:]]
        new = replace_item(c, c.items[0], "AxeBronze", 8, 1)
        self.assertEqual((new.quality, new.durability_raw), (8, 47500))
        self.assertFalse(new.equipped)
        self.assertTrue(new.picked)
        self.assertEqual((new.crafter_id, new.crafter_name, new.custom, new.variant, new.tail),
                         (0, "", [], 0, 0))
        self.assertEqual([i.to_bytes() for i in c.items[1:]], others)
        before = c.serialize()
        for prefab, quantity in [("missing", 1), ("SwordIron", 2)]:
            with self.assertRaises(FormatError):
                replace_item(c, new, prefab, 1, quantity)
            self.assertEqual(c.serialize(), before)

    def test_fr020_divergence_invalid_actions_and_drafts(self):
        s = self.session
        s.organize(("item", 0), "move", (4, 0))
        s.undo()
        with self.assertRaises(FormatError):
            s.organize(("item", 0), "move", (3, 0))
        self.assertEqual(len(s.history.future), 1)
        s.item_drafts[("item", 0)] = {"quality": "9"}
        with self.assertRaises(FormatError):
            s.redo()
        with self.assertRaises(FormatError):
            s.organize(("item", 1), "fill")
        self.assertEqual(s.working.serialize(), self.raw)
        s.item_drafts.clear()
        s.organize(("item", 1), "fill")
        self.assertFalse(s.history.future)

    def test_fr020_export_revision_and_long_operation_chain(self):
        s = self.session
        states = [s.working.serialize()]
        for destination in ((4, 0), (5, 0), (6, 0), (7, 0), (0, 1)):
            s.organize(("item", 0), "move", destination)
            states.append(s.working.serialize())
        s.exported_revision = s.revision
        self.assertFalse(s.unsaved)
        for before in reversed(states[:-1]):
            s.undo()
            self.assertEqual(s.working.serialize(), before)
            self.assertTrue(s.unsaved)
        for after in states[1:]:
            s.redo()
            self.assertEqual(s.working.serialize(), after)
        self.assertFalse(s.unsaved)

    def test_fr051_organization_exports_preserving_protected_sections(self):
        s = self.session
        s.organize(("item", 0), "swap", (1, 0))
        new = s.organize(("item", 0), "duplicate", (4, 0))
        s.organize(new, "replace", ("ShieldWood", 3, 1))
        s.undo(); s.redo()
        with tempfile.TemporaryDirectory() as directory:
            source, target = Path(directory)/"input.fch", Path(directory)/"output.fch"
            source.write_bytes(self.raw)
            export_character(s.working, source, target)
            reopened = Character(target.read_bytes())
            self.assertEqual(source.read_bytes(), self.raw)
            self.assertEqual(reopened.serialize(), s.working.serialize())
            for field in ("head", "middle", "tail", "prefix", "suffix", "_skill_bytes"):
                self.assertEqual(getattr(reopened, field), getattr(s.baseline, field))
            self.assertEqual(reopened.items[3].to_bytes(), s.baseline.items[3].to_bytes())
            with self.assertRaises(FormatError):
                export_character(s.working, source, source)

    def test_fr050_export_rejects_bypassed_move_bounds_and_unknown_move(self):
        with tempfile.TemporaryDirectory() as directory:
            source, target = Path(directory)/"input.fch", Path(directory)/"output.fch"
            source.write_bytes(self.raw)
            for index, position in [(0, (7, 99)), (3, (4, 0))]:
                c = Character(self.raw)
                c.items[index].x, c.items[index].y = position
                with self.assertRaises(FormatError):
                    export_character(c, source, target)
                self.assertFalse(target.exists())

    def test_fr072_late_failure_never_enters_history(self):
        s = self.session
        with patch.object(s, "publish", side_effect=FormatError("Injected serialization failure")):
            with self.assertRaises(FormatError):
                s.organize(("item", 0), "duplicate", (4, 0))
        self.assertEqual(s.working.serialize(), self.raw)
        self.assertFalse(s.history.past)
