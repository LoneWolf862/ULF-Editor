"""Synthetic release gates prompted by the independent editor investigation."""

from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from core.export import export_character
from core.fch import Character, Item, stable_hash
from desktop.session import Session
from synthetic import current_character_bytes


class ReleaseAcceptanceTests(unittest.TestCase):
    def test_fr004_fr018_decimal_hundredths_survive_noop_and_quality_export(self):
        # This decimal loses a hundredth under float * 100 truncation in the
        # reference codec. ULF must retain its integer representation.
        item = Item(stable_hash("CapeDeepNorth"), 0, 0,
                    quality=4, durability_raw=109210, tail=5)
        raw = current_character_bytes(item_bytes=[item.to_bytes()])
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.fch"
            target = Path(directory) / "copy.fch"
            source.write_bytes(raw)
            session = Session(Character(raw), source)
            export_character(session.working, source, target)
            self.assertEqual(target.read_bytes(), raw)
            session.edit_item(("item", 0), {"quality": 32})
            export_character(session.working, source, target)
            reopened = Character(target.read_bytes())
            expected = deepcopy(item)
            expected.quality = 32
            self.assertEqual(reopened.items[0].to_bytes(), expected.to_bytes())
            self.assertEqual(reopened.items[0].durability_raw, 109210)
            self.assertEqual(source.read_bytes(), raw)

    def test_fr018_fr054_fr060_bulk_count_excludes_overmaximum_without_clamping(self):
        rows = [
            Item(stable_hash("SwordGold_BloodLightning"), 0, 0,
                 quality=8, durability_raw=71500, tail=5),
            Item(stable_hash("StaffThunderBlood"), 1, 0,
                 quality=8, durability_raw=73300, tail=7),
            Item(stable_hash("SwordIron"), 2, 0,
                 quality=13, durability_raw=160000, tail=5),
        ]
        raw = current_character_bytes(item_bytes=[item.to_bytes() for item in rows])
        session = Session(Character(raw), Path("synthetic.fch"))
        plan = session.repair_plan()
        self.assertEqual(len(plan.changes), 2)
        self.assertEqual(plan.skipped, ((("item", 2),
                         "Durability is already at or above the repair target."),))
        self.assertEqual(session.working.serialize(), raw)
        session.apply_repairs(plan)
        reopened = Character(session.working.serialize())
        changed = [i for i, (old, new) in enumerate(zip(rows, reopened.items))
                   if old.to_bytes() != new.to_bytes()]
        self.assertEqual(changed, [0, 1])
        self.assertEqual(len(session.changes()), len(plan.changes))
        self.assertEqual(reopened.items[2].to_bytes(), rows[2].to_bytes())
        for old, new in zip(rows[:2], reopened.items[:2]):
            expected = deepcopy(old)
            expected.durability_raw = 75000
            self.assertEqual(new.to_bytes(), expected.to_bytes())
        for field in ("prefix", "suffix", "head", "middle", "tail", "_skill_bytes"):
            self.assertEqual(getattr(reopened, field), getattr(session.baseline, field))
