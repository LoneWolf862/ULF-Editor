import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PySide6.QtWidgets import QApplication

from core.fch import Character, stable_hash
from desktop.app import Window
from synthetic import character_bytes


class DesktopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def setUp(self):
        self.window = Window()
        self.addCleanup(self.window.close)
        self.window.ch = Character(character_bytes())
        self.window.refresh()
        self.messages = patch("desktop.app.QMessageBox.warning")
        self.messages.start()
        self.addCleanup(self.messages.stop)

    def test_fr011_quality_only_preserves_prefab_and_other_properties(self):
        original = copy.deepcopy(self.window.ch.items[0])
        self.window.select_slot(0, 0)
        self.window.quality.setValue(60000)
        self.window.apply_slot()
        expected = copy.deepcopy(original)
        expected.quality = 60000
        self.assertEqual(self.window.ch.items[0], expected)

    def test_fr012_rejects_stack_overflow_atomically(self):
        original = self.window.ch.serialize()
        self.window.select_slot(0, 0)
        self.window.qty.setValue(51)
        self.window.quality.setValue(8)
        self.window.apply_slot()
        self.assertEqual(self.window.ch.serialize(), original)

    def test_fr043_invalid_batch_stops_export(self):
        original = self.window.ch.serialize()
        self.window.skilltable.item(0, 1).setText("40")
        self.window.skilltable.item(1, 1).setText("invalid")
        with patch("desktop.app.QFileDialog.getSaveFileName") as dialog:
            self.window.export()
        dialog.assert_not_called()
        self.assertEqual(self.window.ch.serialize(), original)

    def test_fr005_inventory_refresh_preserves_pending_skill_text(self):
        self.window.skilltable.item(0, 1).setText("42.25")
        self.window.select_slot(0, 0)
        self.window.quality.setValue(9)
        self.window.apply_slot()
        self.assertEqual(self.window.skilltable.item(0, 1).text(), "42.25")

    def test_fr051_desktop_export_roundtrip(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "source.fch"
            source.write_bytes(self.window.ch.original)
            target = Path(folder) / "output.fch"
            self.window.path = source
            self.window.select_slot(0, 0)
            self.window.quality.setValue(33)
            self.window.apply_slot()
            self.window.skilltable.item(0, 1).setText("70")
            with patch("desktop.app.QFileDialog.getSaveFileName", return_value=(str(target), "")):
                with patch("desktop.app.QMessageBox.information"):
                    self.window.export()
            reopened = Character(target.read_bytes())
            self.assertEqual(reopened.items[0].prefab_hash, stable_hash("Wood"))
            self.assertEqual(reopened.items[0].quality, 33)
            self.assertEqual(reopened.skills[0], [1, 70, 0.375])
            self.assertEqual(source.read_bytes(), self.window.ch.original)

    def test_fr014_remove_then_add_different_prefab(self):
        self.window.select_slot(0, 0)
        self.window.remove_slot()
        self.assertEqual(self.window.ch.items, [])
        self.window.select_slot(0, 0)
        self.window.prefab.setEditText("Stone")
        self.window.apply_slot()
        self.assertEqual(len(self.window.ch.items), 1)
        self.assertEqual(self.window.ch.items[0].prefab_hash, stable_hash("Stone"))
        self.assertIsNone(self.window.ch.items[0].origin_index)

    def test_fr001_file_selection_failure_then_recovery(self):
        original = self.window.ch
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "synthetic.fch"
            source.write_bytes(b"invalid")
            with patch("desktop.app.QFileDialog.getOpenFileName", return_value=(str(source), "")):
                with patch("desktop.app.QMessageBox.critical") as error:
                    self.window.open_file()
                    error.assert_called_once()
                self.assertIs(self.window.ch, original)
                source.write_bytes(character_bytes())
                self.window.open_file()
            self.assertEqual(self.window.path, source)
            self.assertTrue(self.window.savebtn.isEnabled())
            self.assertTrue(self.window.ch.roundtrip)
