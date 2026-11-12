import copy
import struct
import unittest

from core.editing import apply_item, apply_skills
from core.fch import Character, FormatError, Item, Reader, read_item, stable_hash
from synthetic import character_bytes


class BinaryEdgeTests(unittest.TestCase):
    def optional_record(self, prefab="Wood"):
        # Explicit default quality/stack/variant, zero crafter ID with name,
        # nonminimal string lengths, and a wide custom count of one.
        raw = struct.pack("<iBBBBHHiq",12345,0,0,2,255,1,1,0,0)
        raw += b"\x81\x00C" + struct.pack("<i",stable_hash(prefab))
        raw += b"\x80\x01\x81\x00K\x81\x00V\xa5"
        return raw

    def test_fr010_optional_encodings_roundtrip(self):
        raw = character_bytes(item_bytes=[self.optional_record()])
        character=Character(raw)
        self.assertTrue(character.roundtrip)
        self.assertEqual(character.serialize(),raw)
        apply_item(character,character.items[0],{"quality":65535})
        expected=bytearray(self.optional_record())
        struct.pack_into("<H",expected,8,65535)
        self.assertEqual(character.items[0].to_bytes(),bytes(expected))

    def test_fr032_unknown_raw_metadata_unchanged(self):
        record=self.optional_record("UnlistedPrefab")
        raw=character_bytes(item_bytes=[record])
        character=Character(raw)
        apply_skills(character,[(1,70,None)])
        self.assertEqual(Character(character.serialize()).items[0].to_bytes(),record)

    def test_fr040_unknown_skill_float_bits_preserved(self):
        unknown=struct.pack("<iII",999,0x7f800001,0x80000000)
        known=struct.pack("<iff",1,1.234567,0.345678)
        character=Character(character_bytes(skill_bytes=[unknown,known]))
        self.assertTrue(character.roundtrip)
        apply_skills(character,[(1,60,None)])
        reopened=Character(character.serialize())
        self.assertEqual(reopened._skill_bytes[0],unknown)
        self.assertEqual(reopened._skill_bytes[1][8:],known[8:])

    def test_fr003_existing_version_matrix_noop(self):
        for profile in (44,46):
            for player in range(23,34):
                with self.subTest(profile=profile,player=player):
                    raw=character_bytes(profile_version=profile,player_version=player)
                    self.assertEqual(Character(raw).serialize(),raw)

    def test_fr003_unsupported_embedded_versions(self):
        for arguments in ({"player_version":34},{"inventory_version":110},{"skills_version":3}):
            with self.subTest(arguments=arguments):
                with self.assertRaises(FormatError):
                    Character(character_bytes(**arguments))

    def test_fr002_every_truncated_prefix_fails(self):
        raw=character_bytes(item_bytes=[self.optional_record()])
        for length in range(len(raw)):
            with self.assertRaises(FormatError):
                Character(raw[:length])

    def test_fr002_hostile_lengths(self):
        for raw in (b"\xff"*5,struct.pack("<i",-1),b"\x80"*5):
            with self.assertRaises(FormatError):
                Reader(raw).string()

    def test_fr030_utf16_and_null_hash_semantics(self):
        self.assertEqual(stable_hash("Wood"),-151837501)
        self.assertEqual(stable_hash("Wood\x00ignored"),stable_hash("Wood"))
        self.assertEqual(stable_hash("\U0001f43a"),stable_hash("\ud83d\udc3a"))
