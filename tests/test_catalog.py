import json
from pathlib import Path
import re
import unittest

from core.catalog import CATALOG
from core.editing import apply_item
from core.fch import Character, FormatError, stable_hash
from desktop.item_catalog import BY_PREFAB, LABELS, search_catalog
from synthetic import character_bytes


class CatalogTests(unittest.TestCase):
    def test_fr033_localized_catalog_matches_pinned_references(self):
        references = Path(__file__).resolve().parents[1] / "docs/references"
        jotunn = {}
        for line in (references / "jotunn-item-list.md").read_text(encoding="utf-8").splitlines():
            fields = line.split("|")
            if len(fields) >= 7 and re.fullmatch("[a-f0-9]{32}", fields[2]):
                jotunn[fields[1].split("<br>")[0]] = fields[4:6]
        self.assertEqual(set(BY_PREFAB), set(CATALOG))
        self.assertEqual(LABELS, {prefab: jotunn[prefab] for prefab in CATALOG})
        valid = set()
        for line in (references / "items.tsv").read_text(encoding="utf-8").splitlines()[1:]:
            prefab, inventory_valid, *_ = line.split("\t")
            if inventory_valid == "true":
                valid.add(prefab)
        self.assertLessEqual(valid, CATALOG.keys())
        self.assertEqual(search_catalog("amber pearl", "Material")[0].prefab, "AmberPearl")
        self.assertEqual(search_catalog("AmberPearl", None)[0].prefab, "AmberPearl")
        self.assertFalse(search_catalog("amber pearl", "Armor"))

    def test_fr030_hashes_are_unambiguous(self):
        hashes = [stable_hash(name) for name in CATALOG]
        self.assertEqual(len(hashes), len(set(hashes)))

    def test_fr097_verified_local_game_limits(self):
        reference = Path(__file__).resolve().parents[1] / "docs/references/local-game-item-limits.json"
        items = json.loads(reference.read_text(encoding="utf-8"))["items"]
        self.assertGreaterEqual(len(items), 13)
        for prefab, metadata in items.items():
            with self.subTest(prefab=prefab):
                self.assertEqual(CATALOG[prefab]["max_stack"], metadata["max_stack"])
                character = Character(character_bytes())
                character.add(prefab, 1, 0, stack=metadata["max_stack"], quality=65535)
                item = character.items[-1]
                with self.assertRaises(FormatError):
                    apply_item(character, item, {"stack": metadata["max_stack"] + 1})
                reopened = Character(character.serialize())
                self.assertEqual(reopened.items[-1], item)

    def test_fr030_previously_unresolved_hash_vectors(self):
        vectors = {"FistGold": 690355706, "FistGold_BloodLightning": -987977923,
                   "FistGold_FrostFire": 1990120219, "OrbThunderBlood": 1263128497,
                   "StaffFrostOrbs": -97147916, "StaffOrbofAhri": -1819695760,
                   "StaffSpiritCaller": -1724175458, "StaffThunderBlood": -677306358}
        for prefab, expected in vectors.items():
            with self.subTest(prefab=prefab):
                self.assertEqual(stable_hash(prefab), expected)
                self.assertIsNotNone(CATALOG[prefab]["max_stack"])
