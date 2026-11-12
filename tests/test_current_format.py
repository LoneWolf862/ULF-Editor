"""Synthetic compatibility regressions for the Valheim 1.0.21 layout."""

from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

from core.editing import apply_item, apply_skills, remove_item
from core.export import export_character
from core.fch import Character, FormatError, Item, stable_hash
from synthetic import character_bytes, current_character_bytes


class CurrentFormatTests(unittest.TestCase):
    def test_fr003_current_layout_and_metadata_round_trip(self):
        raw = current_character_bytes()
        character = Character(raw)
        self.assertEqual((character.profile_version, character.player_version,
                          character.inventory_version, character.skills_version), (47, 34, 110, 2))
        self.assertTrue(character.roundtrip)
        self.assertEqual(character.serialize(), raw)
        self.assertTrue(character.used_cheats)
        self.assertTrue(character.item_cheat_status(character.items[0]))
        legacy = Character(character_bytes())
        self.assertIsNone(legacy.item_cheat_status(legacy.items[0]))
        self.assertEqual(legacy.items[0].tail, character.items[0].tail)

    def test_fr003_rejects_mixed_and_future_layouts(self):
        for override in ({"profile_version": 48}, {"profile_version": 46}, {"player_version": 33},
                         {"player_version": 35}, {"inventory_version": 109}, {"inventory_version": 111},
                         {"skills_version": 3}):
            with self.subTest(override=override), self.assertRaises(FormatError):
                Character(current_character_bytes(**override))

    def test_fr002_rejects_corruption_and_truncation(self):
        raw = current_character_bytes()
        with self.assertRaisesRegex(FormatError, "SHA-512"):
            Character(raw[:-1] + bytes([raw[-1] ^ 1]))
        for end in range(len(raw)):
            with self.assertRaises(FormatError):
                Character(raw[:end])
        tail = Character(raw).tail
        # These fixtures have valid checksums and lengths for their damaged bodies.
        for bad_tail in (tail[:-1], tail + b"extra", struct.pack("<i", -1) + tail[4:],
                         tail[:-12] + struct.pack("<i", 100000) + tail[-8:]):
            with self.subTest(length=len(bad_tail)), self.assertRaises(FormatError):
                Character(current_character_bytes(player_tail=bad_tail))

    def test_fr013_creation_respects_current_character_pockets(self):
        for entries, rows in (((), 4), (("INVROWS 5",), 5), (("invrows 9",), 6),
                              (("invrows 0",), 0), (("invrows 4", "INVROWS 6"), 0),
                              (("invrows 00000000001",), 0)):
            with self.subTest(entries=entries):
                character = Character(current_character_bytes(unique_entries=entries))
                self.assertEqual(character.writable_inventory_rows, rows)
                if rows:
                    character.add("Stone", 1, rows - 1)
                with self.assertRaisesRegex(FormatError, "Slot out of bounds"):
                    character.add("Stone", 1, rows)

    def test_fr053_current_export_preserves_protected_bytes_and_expected_edits(self):
        wood = Item(stable_hash("Wood"), 0, 0, stack=5, equipped=True, crafter_id=42,
                    crafter_name="Synthetic crafter", custom=[("key", "value")], tail=0xA5)
        stone = Item(stable_hash("Stone"), 1, 0)
        # Nonminimal encoded strings and an explicitly present default quality.
        unknown = (struct.pack("<iBBBBHi", 12345, 2, 0, 1, 0xC4, 1, -7654321)
                   + b"\x80\x01\x81\x00K\x81\x00V\xA5")
        level_record = struct.pack("<iff", 1, 10.125, 0.375)
        unknown_skill = struct.pack("<iII", 999, 0x7f800001, 0x80000000)
        raw = current_character_bytes(item_bytes=[wood.to_bytes(), stone.to_bytes(), unknown],
                                      skill_bytes=[level_record, unknown_skill])
        character = Character(raw)
        with self.assertRaises(FormatError):
            apply_item(character, character.items[0], {"stack": 51, "quality": 65535})
        with self.assertRaises(FormatError):
            apply_skills(character, [(1, 11, None), (2, -1, None)])
        self.assertEqual(character.serialize(), raw)
        apply_item(character, character.items[0], {"stack": 50, "quality": 65535, "durability_raw": 8125})
        remove_item(character, character.items[1])
        character.add("Wood", 1, 0, stack=3)
        apply_skills(character, [(1, 42.25, None), (2, 4.5, 1.125)])
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "source.fch"
            target = Path(folder) / "copy.fch"
            source.write_bytes(raw)
            export_character(character, source, target)
            reopened = Character(target.read_bytes())
            self.assertTrue(reopened.roundtrip)
            self.assertEqual(source.read_bytes(), raw)
        original = Character(raw)
        for field in ("prefix", "head", "middle", "tail", "suffix"):
            self.assertEqual(getattr(reopened, field), getattr(original, field), field)
        self.assertEqual(reopened._skill_bytes[0][8:], level_record[8:])
        self.assertEqual(reopened._skill_bytes[1], unknown_skill)
        self.assertEqual(reopened.skills[2], [2, 4.5, 1.125])
        self.assertEqual(reopened.items[1].to_bytes(), unknown)
        self.assertEqual(reopened.items[2].tail, 0)
        self.assertEqual(reopened.items[2].prefab_hash, stable_hash("Wood"))
        self.assertEqual((reopened.items[2].x, reopened.items[2].y, reopened.items[2].stack), (1, 0, 3))
        wood.stack, wood.quality, wood.durability_raw = 50, 65535, 8125
        self.assertEqual(reopened.items[0], wood)

    def test_fr013_export_rechecks_current_writable_slots(self):
        raw = current_character_bytes()
        character = Character(raw)
        character.items.append(Item(stable_hash("Stone"), 0, 4))
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "source.fch"
            target = Path(folder) / "copy.fch"
            source.write_bytes(raw)
            with self.assertRaisesRegex(FormatError, "writable slots"):
                export_character(character, source, target)
            self.assertFalse(target.exists())
            self.assertEqual(source.read_bytes(), raw)

    def test_fr060_current_export_rejects_item_flag_changes(self):
        raw = current_character_bytes()
        character = Character(raw)
        character.items[0].tail ^= 1
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "source.fch"
            target = Path(folder) / "copy.fch"
            source.write_bytes(raw)
            with self.assertRaisesRegex(FormatError, "protected metadata"):
                export_character(character, source, target)
            self.assertFalse(target.exists())

    def test_fr051_current_corrupt_disk_readback_cleans_up_without_publication(self):
        raw = current_character_bytes()
        character = Character(raw)
        apply_item(character, character.items[0], {"quality": 7})
        read_bytes = Path.read_bytes

        def corrupt_temporary(path):
            data = read_bytes(path)
            return data[:-1] + bytes([data[-1] ^ 1]) if path.suffix == ".tmp" else data

        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "source.fch"
            target = Path(folder) / "copy.fch"
            source.write_bytes(raw)
            target.write_bytes(b"previous destination")
            with patch.object(Path, "read_bytes", corrupt_temporary):
                with self.assertRaisesRegex(FormatError, "SHA-512"):
                    export_character(character, source, target)
            self.assertEqual(target.read_bytes(), b"previous destination")
            self.assertEqual(source.read_bytes(), raw)
            self.assertFalse(list(Path(folder).glob(".ulf-*.tmp")))
