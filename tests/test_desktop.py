"""Offscreen Qt regressions with synthetic saves and native dialogs mocked."""

import copy
import os
from pathlib import Path
import socket
import struct
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

from core.fch import Character, Item, stable_hash
from desktop.app import Window
from desktop.inventory import ACCESSIBLE, CatalogDialog
from desktop.session import Session
from synthetic import character_bytes, current_character_bytes


class DesktopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.source = Path(folder.name) / "source.fch"
        self.target = self.source.with_name("export.fch")
        self.window = Window()
        self.addCleanup(self.close_window)
        self.load_fixture(character_bytes())
        self.window.show()
        self.application.processEvents()

    def close_window(self):
        self.wait_for_job()
        with patch.object(self.window, "confirm_discard", return_value=True):
            self.window.close()
        self.window.deleteLater()
        self.application.processEvents()

    def load_fixture(self, data):
        self.source.write_bytes(data)
        self.window.set_session(Session(Character(data), self.source))

    @property
    def session(self):
        return self.window.session

    @property
    def inventory(self):
        return self.window.inventory

    def wait_for_job(self):
        for _ in range(200):
            if self.window.job is None:
                return
            QTest.qWait(10)
        self.fail("File worker did not complete")

    def select(self, x, y):
        self.inventory.grid.setCurrentIndex(self.inventory.model.index(y, x))

    def set_item_value(self, field, value):
        self.inventory.fields.editors[field].lineEdit().setText(value)

    def create_item(self, prefab, stack="1", query=None):
        dialog = CatalogDialog(self.inventory, self.session, self.inventory.position)
        self.addCleanup(dialog.deleteLater)
        dialog.search.setText(query or prefab)
        dialog.results.setCurrentRow(0)
        self.assertEqual(dialog.entry.prefab, prefab)
        dialog.fields.editors["stack"].lineEdit().setText(stack)
        dialog.add.click()
        if dialog.result() == QDialog.DialogCode.Accepted:
            self.window.refresh_editors()
        return dialog

    def export_to(self, path):
        with patch("desktop.app.QFileDialog.getSaveFileName", return_value=(str(path), "")):
            self.window.export()
            self.wait_for_job()

    def test_fr011_quality_only_preserves_prefab_and_other_properties(self):
        original = copy.deepcopy(self.session.working.items[0])
        self.set_item_value("quality", "65535")
        self.assertIn("vanilla maximum", self.inventory.warning.text())
        self.inventory.apply_button.click()
        original.quality = 65535
        self.assertEqual(self.session.working.items[0], original)
        self.assertIn("65535", self.window.changes[0].details[0])
        self.assertTrue(self.window.changes[0].warning)

    def test_fr012_rejects_stack_overflow_atomically(self):
        original = self.session.working.serialize()
        self.set_item_value("stack", "51")
        self.set_item_value("quality", "8")
        self.inventory.apply_button.click()
        self.assertEqual(self.session.working.serialize(), original)
        self.assertIn("50", self.inventory.error.text())
        self.assertTrue(self.inventory.fields.editors["stack"].property("invalid"))
        for value in ("0", "-1", "65536"):
            with self.subTest(value=value):
                self.set_item_value("stack", value)
                self.inventory.apply_button.click()
                self.assertEqual(self.session.working.serialize(), original)
        self.set_item_value("stack", "50")
        self.inventory.apply_button.click()
        self.assertEqual((self.session.working.items[0].stack, self.session.working.items[0].quality), (50, 8))

    def test_fr018_durability_has_exact_hundredth_precision(self):
        original = self.session.working.serialize()
        self.set_item_value("durability_raw", "18.257")
        self.inventory.apply_button.click()
        self.assertEqual(self.session.working.serialize(), original)
        self.set_item_value("durability_raw", "21474836.47")
        self.inventory.apply_button.click()
        self.assertEqual(self.session.working.items[0].durability_raw, 2**31 - 1)

    def test_fr043_invalid_batch_stops_export(self):
        original = self.session.working.serialize()
        self.window.tabs.setCurrentWidget(self.window.skills)
        self.window.skills.rows[1].level.setText("40")
        self.window.skills.rows[2].level.setText("invalid")
        self.window.skills.apply_button.click()
        self.assertTrue(self.window.skills.rows[2].level.property("invalid"))
        self.assertEqual(self.session.working.serialize(), original)
        with patch("desktop.app.QFileDialog.getSaveFileName") as dialog:
            self.window.export()
        dialog.assert_not_called()
        self.assertFalse(self.window.review.export.isEnabled())

    def test_fr005_inventory_refresh_preserves_pending_skill_text(self):
        row = self.window.skills.rows[1]
        row.level.setText("42.25")
        self.set_item_value("quality", "9")
        self.inventory.apply_button.click()
        self.assertEqual(row.level.text(), "42.25")
        self.assertEqual(self.session.working.skills[0][1], 10.125)

    def test_fr044_slider_and_precise_input_preserve_untouched_experience(self):
        row = self.window.skills.rows[1]
        self.window.tabs.setCurrentWidget(self.window.skills)
        row.level.setText("42.251234")
        self.assertEqual(row.slider.value(), 423)
        self.assertEqual(row.level.text(), "42.251234")
        row.slider.setFocus()
        QTest.keyClick(row.slider, Qt.Key.Key_Right)
        self.assertEqual(row.level.text(), "42.4")
        row.level.setText("42.251234")
        self.window.skills.apply_button.click()
        saved = Character(self.session.working.serialize())
        self.assertAlmostEqual(saved.skills[0][1], 42.251234, places=5)
        self.assertEqual(saved._skill_bytes[0][8:], self.session.baseline._skill_bytes[0][8:])
        self.assertFalse(self.session.has_drafts)

    def test_fr040_unusual_skill_values_survive_explicit_correction(self):
        level = struct.pack("<If", 1, 105.0)
        unusual_xp = bytes.fromhex("4523c17f")
        unknown = struct.pack("<iff", 999, -0.0, 12)
        self.load_fixture(character_bytes(skill_bytes=[level + unusual_xp, unknown]))
        row = self.window.skills.rows[1]
        self.assertEqual(row.level.text(), "")
        self.assertIn("105", row.applied.text())
        self.assertIn("Unknown skill (ID 999)", self.window.skills.diagnostics.text())
        row.level.setText("100")
        self.window.skills.apply_button.click()
        saved = Character(self.session.working.serialize())
        self.assertEqual(saved.skills[0][1], 100)
        self.assertEqual(saved._skill_bytes[0][8:], unusual_xp)
        self.assertEqual(saved._skill_bytes[1], unknown)

    def test_fr042_experience_disclosure_and_explicit_edit(self):
        row = self.window.skills.rows[1]
        self.assertTrue(row.experience_area.isHidden())
        row.toggle.click()
        self.assertFalse(row.experience_area.isHidden())
        row.experience.setText("45.125")
        self.window.skills.apply_button.click()
        saved = Character(self.session.working.serialize())
        self.assertEqual(saved.skills[0], [1, 10.125, 45.125])

    def test_fr051_desktop_export_roundtrip(self):
        self.set_item_value("quality", "33")
        self.inventory.apply_button.click()
        self.window.skills.rows[1].level.setText("70")
        self.window.skills.apply_button.click()
        self.assertIn("Export pending", self.window.pending.text())
        self.export_to(self.target)
        reopened = Character(self.target.read_bytes())
        self.assertEqual(reopened.items[0].prefab_hash, stable_hash("Wood"))
        self.assertEqual(reopened.items[0].quality, 33)
        self.assertEqual(reopened.items[0].tail, 5)
        self.assertTrue(reopened.used_cheats)
        self.assertEqual(reopened.skills[0], [1, 70, 0.375])
        self.assertEqual(self.source.read_bytes(), self.session.baseline.original)
        self.assertIn("Export verified", self.window.pending.text())
        self.assertIn(str(self.target), self.window.status.text())
        self.assertFalse(self.session.unsaved)

    def test_fr051_desktop_current_format_open_edit_review_export_reopen(self):
        raw = current_character_bytes()
        self.source.write_bytes(raw)
        self.window.load_path(self.source)
        self.wait_for_job()
        self.assertIn("SHA-512", self.window.validation.text())
        self.assertIn("Saved cheated flag: set", self.inventory.metadata.text())
        self.assertEqual(self.session.working.profile_version, 47)
        self.set_item_value("quality", "60000")
        self.inventory.apply_button.click()
        self.create_item("Stone")
        row = self.window.skills.rows[1]
        row.slider.setValue(420)
        self.assertEqual(row.level.text(), "42")
        row.level.setText("42.125")
        self.window.skills.apply_button.click()
        self.assertEqual(len(self.window.changes), 3)
        self.export_to(self.target)
        self.window.load_path(self.target)
        self.wait_for_job()
        self.assertEqual(self.session.working.items[0].quality, 60000)
        self.assertEqual(self.session.working.skills[0], [1, 42.125, 0.375])
        self.assertEqual(self.source.read_bytes(), raw)

    def test_fr050_save_as_rejects_alias_and_retains_edits(self):
        alias = self.source.with_name("alias.fch")
        os.link(self.source, alias)
        self.set_item_value("quality", "9")
        self.inventory.apply_button.click()
        with patch("desktop.app.QMessageBox.exec", return_value=QMessageBox.StandardButton.Ok):
            self.export_to(alias)
        self.assertIsNone(self.session.export_path)
        self.assertIn("refers to the original", self.window.status.text())
        self.assertEqual(alias.read_bytes(), self.session.baseline.original)
        self.assertEqual(self.session.working.items[0].quality, 9)

    def test_fr056_changed_source_and_canceled_save_keep_pending_changes(self):
        self.set_item_value("quality", "9")
        self.inventory.apply_button.click()
        with patch("desktop.app.QFileDialog.getSaveFileName", return_value=("", "")):
            self.window.export()
        self.assertTrue(self.session.unsaved)
        self.source.write_bytes(b"externally modified")
        with patch("desktop.app.QMessageBox.exec", return_value=QMessageBox.StandardButton.Ok):
            self.export_to(self.target)
        self.assertIn("Reload", self.window.status.text())
        self.assertFalse(self.target.exists())
        self.assertEqual(self.session.working.items[0].quality, 9)

    def test_fr014_remove_then_add_different_prefab_and_discard_both(self):
        with patch("desktop.inventory.QMessageBox.question", return_value=QMessageBox.StandardButton.Yes):
            self.inventory.remove_button.click()
        self.assertFalse(self.session.working.items)
        dialog = self.create_item("Stone")
        self.assertEqual(dialog.result(), QDialog.DialogCode.Accepted)
        self.assertEqual(self.session.working.items[0].prefab_hash, stable_hash("Stone"))
        self.assertIsNone(self.session.working.items[0].origin_index)
        self.assertFalse(self.session.working.items[0].cheated)
        self.assertEqual(len(self.window.changes), 2)
        removal = self.window.changes[0]
        with patch("desktop.app.QMessageBox.question", return_value=QMessageBox.StandardButton.Cancel):
            self.window.discard_change(removal)
        self.assertEqual(len(self.window.changes), 2)
        with patch("desktop.app.QMessageBox.question", return_value=QMessageBox.StandardButton.Discard):
            self.window.discard_change(removal)
        self.assertEqual(self.session.working.serialize(), self.session.baseline.original)
        self.assertFalse(self.session.unsaved)

    def test_fr031_search_invalidates_stale_item_and_rejects_creation_overflow(self):
        dialog = self.create_item("Wood", "51")
        self.assertEqual(dialog.result(), QDialog.DialogCode.Rejected)
        self.assertIn("50", dialog.error.text())
        dialog.search.setText("missing prefab name")
        self.assertIsNone(dialog.entry)
        self.assertFalse(dialog.add.isEnabled())
        self.assertEqual(len(self.session.working.items), 1)

    def test_fr014_restore_original_after_replacement_was_removed(self):
        with patch("desktop.inventory.QMessageBox.question", return_value=QMessageBox.StandardButton.Yes):
            self.inventory.remove_button.click()
            self.create_item("Stone")
            self.inventory.remove_button.click()
        self.assertEqual(len(self.window.changes), 1)
        self.window.discard_change(self.window.changes[0])
        self.assertEqual(self.session.working.serialize(), self.session.baseline.original)

    def test_fr017_edit_higher_row_and_keep_creation_within_writable_rows(self):
        item = Item(stable_hash("Wood"), 2, 17, stack=5)
        self.load_fixture(character_bytes(item_bytes=[item.to_bytes()]))
        self.select(2, 17)
        self.set_item_value("quality", "4")
        self.inventory.apply_button.click()
        self.assertEqual(self.session.working.items[0].quality, 4)
        dialog = self.create_item("Stone")
        self.assertEqual(dialog.result(), QDialog.DialogCode.Accepted)
        self.assertTrue(all(dialog.slot.itemData(i)[1] < 6 for i in range(dialog.slot.count())))
        self.assertEqual((self.session.working.items[-1].x, self.session.working.items[-1].y), (0, 0))

    def test_fr032_unknown_and_ambiguous_records_stay_visible_and_protected(self):
        records = [
            Item(stable_hash("Wood"), 0, 0),
            Item(stable_hash("Stone"), 0, 0),
            Item(-76543, 1, 255, tail=5),
            Item(stable_hash("Wood"), 10, 3),
        ]
        self.load_fixture(character_bytes(item_bytes=[item.to_bytes() for item in records]))
        self.assertEqual(self.inventory.model.rowCount(), 256)
        self.assertEqual(self.inventory.model.columnCount(), 8)
        self.assertEqual(self.inventory.diagnostics.count(), 3)
        self.assertFalse(self.window.review.export.isEnabled())
        self.select(1, 255)
        self.assertIn("-76543", self.inventory.name.text())
        self.assertFalse(self.inventory.fields.isEnabled())
        self.inventory.diagnostics.setCurrentRow(2)
        self.assertIn("column 11", self.inventory.position_label.text())
        self.assertFalse(self.inventory.fields.isEnabled())

    def test_fr032_unknown_record_bytes_survive_gui_export(self):
        unknown = Item(-12345, 2, 11, stack=13, tail=5)
        wood = Item(stable_hash("Wood"), 0, 0, stack=5)
        self.load_fixture(character_bytes(item_bytes=[wood.to_bytes(), unknown.to_bytes()]))
        self.set_item_value("quality", "8")
        self.inventory.apply_button.click()
        self.export_to(self.target)
        exported = Character(self.target.read_bytes())
        self.assertEqual(exported.items[1].to_bytes(), unknown.to_bytes())

    def test_fr071_item_draft_survives_selection_and_can_be_reverted(self):
        self.set_item_value("quality", "18")
        self.select(1, 0)
        self.assertIn("Unapplied edits", self.window.pending.text())
        self.assertIn("Draft", self.window.tabs.tabText(0))
        self.window.show_review()
        self.window.review.inventory_drafts.click()
        self.assertEqual(self.inventory.fields.editors["quality"].text(), "18")
        self.inventory.revert_button.click()
        self.assertFalse(self.session.has_drafts)
        self.assertEqual(self.session.working.items[0].quality, 1)

    def test_fr071_discard_all_reverts_both_editors(self):
        self.set_item_value("quality", "9")
        self.inventory.apply_button.click()
        self.window.skills.rows[1].level.setText("80")
        self.window.show_review()
        with patch("desktop.app.QMessageBox.question", return_value=QMessageBox.StandardButton.Discard):
            self.window.review.discard_all.click()
        self.assertFalse(self.session.unsaved)
        self.assertEqual(self.session.working.serialize(), self.session.baseline.original)
        self.assertEqual(self.window.skills.rows[1].level.text(), "10.125")

    def test_fr001_file_selection_failure_then_recovery_keeps_current_session(self):
        original = self.session
        candidate = self.source.with_name("candidate.fch")
        candidate.write_bytes(b"invalid")
        self.set_item_value("quality", "12")
        with patch("desktop.app.QFileDialog.getOpenFileName", return_value=(str(candidate), "")):
            with patch("desktop.app.QMessageBox.question", return_value=QMessageBox.StandardButton.Discard):
                with patch("desktop.app.QMessageBox.exec", return_value=QMessageBox.StandardButton.Ok):
                    self.window.open_file()
                    self.wait_for_job()
                self.assertIs(self.session, original)
                self.assertTrue(self.session.has_drafts)
                candidate.write_bytes(character_bytes())
                self.window.open_file()
                self.wait_for_job()
        self.assertEqual(self.session.path, candidate)
        self.assertTrue(self.session.working.roundtrip)
        self.assertFalse(self.session.has_drafts)

    def test_fr073_keyboard_and_compact_layout(self):
        self.window.resize(800, 600)
        self.application.processEvents()
        self.assertEqual(self.window.width(), 800)
        self.assertTrue(self.inventory.compact)
        self.inventory.grid.setFocus()
        QTest.keyClick(self.inventory.grid, Qt.Key.Key_Right)
        index = self.inventory.grid.currentIndex()
        self.assertEqual(index.column(), 1)
        self.assertIn("Empty slot", index.data(ACCESSIBLE))
        QTest.keyClick(self.inventory.grid, Qt.Key.Key_Return)
        self.assertTrue(self.inventory.inspector.isVisible())
        self.assertFalse(self.inventory.grid_panel.isVisible())
        QTest.keyClick(self.inventory.back, Qt.Key.Key_Space)
        self.assertTrue(self.inventory.grid.hasFocus())
        for width, height in ((1366, 768), (1920, 1080)):
            with self.subTest(width=width, height=height):
                self.window.resize(width, height)
                self.application.processEvents()
                self.assertTrue(self.inventory.grid_panel.isVisible())
                self.assertTrue(self.inventory.inspector.isVisible())
                self.assertGreaterEqual(min(self.inventory.grid.columnWidth(i) for i in range(8)), 44)

    def test_nfr003_offline_catalog_load_edit_export(self):
        with patch.object(socket, "socket", side_effect=AssertionError("Unexpected network socket")):
            self.window.load_path(self.source)
            self.wait_for_job()
            dialog = self.create_item("AmberPearl", query="Amber Pearl")
            self.assertEqual(dialog.result(), QDialog.DialogCode.Accepted)
            self.assertEqual(self.session.working.items[-1].prefab_hash, stable_hash("AmberPearl"))
            self.export_to(self.target)
        self.assertTrue(Character(self.target.read_bytes()).roundtrip)
