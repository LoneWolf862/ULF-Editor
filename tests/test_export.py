import os
from pathlib import Path
import tempfile
import unittest
from contextlib import contextmanager
from unittest.mock import patch

from core.export import export_character
from core.fch import Character, FormatError, Item
from core.editing import remove_item
from synthetic import character_bytes


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.folder = Path(self.directory.name)
        self.source = self.folder / "source.fch"
        self.raw = character_bytes()
        self.source.write_bytes(self.raw)
        self.character = Character(self.raw)
        self.target = self.folder / "edited.fch"

    def test_fr051_disk_export_preserves_source_and_metadata(self):
        self.character.items[0].quality = 60000
        export_character(self.character, self.source, self.target)
        reopened = Character(self.target.read_bytes())
        self.assertTrue(reopened.roundtrip)
        self.assertEqual(reopened.items[0].quality, 60000)
        self.assertEqual(reopened.items[0].tail, 5)
        self.assertTrue(reopened.used_cheats)
        self.assertEqual(self.source.read_bytes(), self.raw)
        self.assertFalse(list(self.folder.glob(".ulf-*")))

    def test_fr050_rejects_source_and_hardlink(self):
        with self.assertRaises(FormatError):
            export_character(self.character, self.source, self.source)
        os.link(self.source, self.target)
        with self.assertRaises(FormatError):
            export_character(self.character, self.source, self.target)
        self.assertEqual(self.source.read_bytes(), self.raw)

    def test_fr052_publication_failure_preserves_existing_target(self):
        self.target.write_bytes(b"previous output")
        with patch("core.export.os.replace", side_effect=OSError("injected")):
            with self.assertRaises(FormatError):
                export_character(self.character, self.source, self.target)
        self.assertEqual(self.target.read_bytes(), b"previous output")
        self.assertFalse(list(self.folder.glob(".ulf-*")))

    def test_fr056_changed_source_blocks_export(self):
        self.source.write_bytes(b"external change")
        with self.assertRaises(FormatError):
            export_character(self.character, self.source, self.target)
        self.assertFalse(self.target.exists())

    def test_fr002_corrupt_checksum_rejected(self):
        damaged = bytearray(self.raw)
        damaged[-1] ^= 1
        with self.assertRaises(FormatError):
            Character(bytes(damaged))

    def test_fr051_corrupt_disk_readback_cancels_publication(self):
        original_read = Path.read_bytes
        def read(path):
            data = original_read(path)
            return data[:-1] + bytes([data[-1] ^ 1]) if path.suffix == ".tmp" else data
        with patch.object(Path, "read_bytes", read):
            with self.assertRaises(FormatError):
                export_character(self.character, self.source, self.target)
        self.assertFalse(self.target.exists())
        self.assertFalse(list(self.folder.glob(".ulf-*")))

    def test_fr012_export_rejects_bypassed_stack_limit(self):
        self.character.items[0].stack = 51
        with self.assertRaises(FormatError):
            export_character(self.character, self.source, self.target)
        self.assertFalse(self.target.exists())

    def test_fr060_export_rejects_flag_change(self):
        self.character.items[0].tail = 0
        with self.assertRaises(FormatError):
            export_character(self.character, self.source, self.target)

    def test_fr053_export_rejects_unrelated_metadata_change(self):
        self.character.tail = b"modified"
        with self.assertRaises(FormatError):
            export_character(self.character, self.source, self.target)

    def test_fr014_remove_replace_same_slot_exports(self):
        remove_item(self.character, self.character.items[0])
        self.character.add("Stone", 0, 0, quality=65535, stack=50)
        export_character(self.character, self.source, self.target)
        reopened = Character(self.target.read_bytes())
        self.assertEqual(reopened.items, self.character.items)
        self.assertEqual(reopened.items[0].tail, 0)
        self.assertEqual(self.source.read_bytes(), self.raw)

    def test_fr041_export_rejects_bypassed_skill_validation(self):
        for value in (-1, 101, float("nan"), float("inf"), "bad"):
            with self.subTest(value=value):
                self.character.skills[0][1] = value
                with self.assertRaises(FormatError):
                    export_character(self.character, self.source, self.target)
                self.assertFalse(self.target.exists())

    def test_fr052_temporary_creation_failure_leaves_no_output(self):
        with patch("core.export.tempfile.mkstemp", side_effect=PermissionError("injected")):
            with self.assertRaisesRegex(FormatError, "creating the temporary"):
                export_character(self.character, self.source, self.target)
        self.assertFalse(self.target.exists())

    def test_fr052_write_failure_preserves_existing_target(self):
        fdopen = os.fdopen
        @contextmanager
        def failing_output(*args):
            with fdopen(*args) as output:
                with patch.object(output, "write", side_effect=OSError("injected")):
                    yield output
        self.target.write_bytes(b"previous output")
        with patch("core.export.os.fdopen", failing_output):
            with self.assertRaisesRegex(FormatError, "writing and flushing"):
                export_character(self.character, self.source, self.target)
        self.assertEqual(self.target.read_bytes(), b"previous output")
        self.assertEqual(self.source.read_bytes(), self.raw)
        self.assertFalse(list(self.folder.glob(".ulf-*")))

    def test_fr032_unknown_record_survives_export_and_cannot_be_removed(self):
        unknown = Item(123456789, 0, 0, custom=[("mod", "opaque")], tail=253)
        self.raw = character_bytes(item_bytes=[unknown.to_bytes()])
        self.source.write_bytes(self.raw)
        self.character = Character(self.raw)
        self.character.set_skill(1, 50)
        export_character(self.character, self.source, self.target)
        self.assertEqual(Character(self.target.read_bytes()).items[0].to_bytes(), unknown.to_bytes())
        self.character.items.clear()
        with self.assertRaisesRegex(FormatError, "unverified inventory item was removed"):
            export_character(self.character, self.source, self.target)

    def test_fr052_flush_failure_preserves_both_files(self):
        self.target.write_bytes(b"previous output")
        with patch("core.export.os.fsync", side_effect=OSError("injected")):
            with self.assertRaisesRegex(FormatError, "writing and flushing"):
                export_character(self.character, self.source, self.target)
        self.assertEqual(self.source.read_bytes(), self.raw)
        self.assertEqual(self.target.read_bytes(), b"previous output")
        self.assertFalse(list(self.folder.glob(".ulf-*")))

    def test_fr052_cleanup_failure_is_actionable(self):
        with patch("core.export.os.replace", side_effect=OSError("injected")):
            with patch.object(Path, "unlink", side_effect=PermissionError("injected")):
                with self.assertRaisesRegex(FormatError, "could not be removed"):
                    export_character(self.character, self.source, self.target)
        self.assertFalse(self.target.exists())
        self.assertEqual(self.source.read_bytes(), self.raw)

    def test_fr051_readback_occurs_after_close(self):
        read_bytes = Path.read_bytes
        def read(path):
            if path.suffix == ".tmp":
                moved = path.with_suffix(".closed")
                path.rename(moved)
                moved.rename(path)
            return read_bytes(path)
        with patch.object(Path, "read_bytes", read):
            export_character(self.character, self.source, self.target)
        self.assertEqual(self.target.read_bytes(), self.raw)
