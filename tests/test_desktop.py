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
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox, QPlainTextEdit

from core.editing import apply_item
from core.fch import Character, FormatError, Item, stable_hash
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

    def load_repair_fixture(self):
        sword = Item(stable_hash("SwordIron"), 0, 0, durability_raw=8125,
                     equipped=True, crafter_id=27, crafter_name="Synthetic crafter",
                     custom=[("test", "value")], tail=5)
        shield = Item(stable_hash("ShieldWood"), 1, 0, durability_raw=12500, quality=3)
        unknown = Item(-7654321, 2, 0, durability_raw=31, tail=7)
        wood = Item(stable_hash("Wood"), 3, 0, stack=5)
        self.load_fixture(current_character_bytes(item_bytes=[
            item.to_bytes() for item in (sword, shield, unknown, wood)
        ]))

    def test_stats_follow_draft_quality_without_repairing(self):
        self.load_repair_fixture()
        self.assertIn("81.25 / 200.00", self.inventory.stat_summary.text())
        self.assertEqual(self.inventory.durability_meter.value(), 406)
        self.set_item_value("quality", "100")
        self.assertIn("81.25 / 5150.00", self.inventory.stat_summary.text())
        self.assertIn("Slash 649", self.inventory.stat_summary.text())
        self.assertFalse(self.inventory.repair_button.isEnabled())
        self.inventory.apply_button.click()
        self.assertEqual(self.session.working.items[0].durability_raw, 8125)
        self.assertTrue(self.inventory.repair_button.isEnabled())

    def test_selected_repair_reviews_and_exports_only_durability(self):
        self.load_repair_fixture()
        original = self.source.read_bytes()
        expected = copy.deepcopy(self.session.working.items[0])
        self.inventory.repair_button.click()
        expected.durability_raw = 20000
        self.assertEqual(self.session.working.items[0], expected)
        self.assertEqual(self.window.changes[0].details, ("Durability  81.25 → 200.00",))
        self.assertFalse(self.inventory.repair_button.isEnabled())
        self.export_to(self.target)
        reopened = Character(self.target.read_bytes())
        self.assertEqual(reopened.items[0], expected)
        self.assertEqual(reopened.items[1:], self.session.baseline.items[1:])
        self.assertEqual(reopened._skill_bytes, self.session.baseline._skill_bytes)
        self.assertEqual(self.source.read_bytes(), original)

    def test_repair_all_previews_skips_and_cancel_preserves_working_state(self):
        self.load_repair_fixture()
        original = self.session.working.serialize()
        def cancel(dialog):
            preview = dialog.findChild(QPlainTextEdit).toPlainText()
            self.assertIn("81.25 → 200.00", preview)
            self.assertIn("125.00 → 300.00", preview)
            self.assertEqual(preview.count("Skipped"), 2)
            return QDialog.DialogCode.Rejected
        with patch.object(QDialog, "exec", cancel):
            self.inventory.repair_all_button.click()
        self.assertEqual(self.session.working.serialize(), original)
        with patch.object(QDialog, "exec", return_value=QDialog.DialogCode.Accepted):
            self.inventory.repair_all_button.click()
        self.assertEqual([item.durability_raw for item in self.session.working.items],
                         [20000, 30000, 31, 10000])
        self.assertEqual(len(self.window.changes), 2)

    def test_repair_all_failure_is_atomic_and_stale_preview_is_rejected(self):
        self.load_repair_fixture()
        original = self.session.working.serialize()
        plan = self.session.repair_plan()
        def fail_on_shield(character, item, changes):
            if item.x == 1:
                raise FormatError("Synthetic second-record failure")
            apply_item(character, item, changes)
        with patch("desktop.session.apply_item", side_effect=fail_on_shield):
            with self.assertRaisesRegex(FormatError, "second-record"):
                self.session.apply_repairs(plan)
        self.assertEqual(self.session.working.serialize(), original)
        self.assertFalse(self.session.commands)
        self.set_item_value("quality", "4")
        with self.assertRaisesRegex(FormatError, "fresh repair preview"):
            self.session.apply_repairs(plan)
        self.assertEqual(self.session.working.serialize(), original)

    def test_legacy_format_previews_statistics_and_remains_editable(self):
        sword = Item(stable_hash("SwordIron"), 0, 0, durability_raw=25)
        self.load_fixture(character_bytes(item_bytes=[sword.to_bytes()]))
        self.assertIn("0.25 / 200.00", self.inventory.stat_summary.text())
        self.assertFalse(self.inventory.repair_button.isEnabled())
        self.set_item_value("quality", "4")
        self.inventory.apply_button.click()
        self.export_to(self.target)
        self.assertEqual(Character(self.target.read_bytes()).items[0].durability_raw, 25)

    def test_fr018_reported_equipment_repair_all_preserves_unknown_and_cheat_metadata(self):
        rows = [
            Item(stable_hash("SwordGold_BloodLightning"), 0, 0, quality=8, durability_raw=71500,
                 equipped=True, crafter_id=42, crafter_name="Synthetic", custom=[("fixture", "keep")], tail=5),
            Item(stable_hash("StaffThunderBlood"), 1, 0, quality=8, durability_raw=73300, tail=7),
            Item(stable_hash("CapeDeepNorth"), 2, 0, quality=32, durability_raw=272700, tail=5),
            Item(stable_hash("Ice"), 3, 0, stack=3),
            Item(-7654321, 4, 0, custom=[("unknown", "preserved")], tail=255),
            Item(stable_hash("Beard1"), 5, 0),
        ]
        self.load_fixture(current_character_bytes(item_bytes=[item.to_bytes() for item in rows]))
        original = self.source.read_bytes()
        plan = self.session.repair_plan()
        self.assertEqual(len(plan.changes), 3)
        self.assertEqual(len(plan.skipped), 3)
        self.session.apply_repairs(plan)
        for item, raw in zip(rows, (75000, 75000, 275000)):
            item.durability_raw = raw
        self.assertEqual(self.session.working.items, rows)
        self.export_to(self.target)
        reopened = Character(self.target.read_bytes())
        self.assertEqual(reopened.items, rows)
        self.assertEqual(reopened.items[4].to_bytes(), self.session.baseline.items[4].to_bytes())
        self.assertEqual(reopened._skill_bytes, self.session.baseline._skill_bytes)
        self.assertEqual(self.source.read_bytes(), original)

    def test_fr018_cape_quality_preserves_current_durability_and_advanced_details(self):
        cape = Item(stable_hash("CapeDeepNorth"), 0, 0, quality=32, durability_raw=272700, tail=5)
        self.load_fixture(current_character_bytes(item_bytes=[cape.to_bytes()]))
        self.assertIn("2727.00 / 2750.00", self.inventory.stat_summary.text())
        self.assertIn("99.2%", self.inventory.stat_summary.text())
        self.assertNotIn("raw", self.inventory.metadata.text())
        self.assertNotIn("CapeDeepNorth", self.inventory.metadata.text())
        def inspect(dialog):
            self.assertIn("CapeDeepNorth", dialog.text())
            self.assertIn("272700 hundredths", dialog.text())
            self.assertIn("26249040", dialog.text())
            return QMessageBox.StandardButton.Ok
        with patch.object(QMessageBox, "exec", inspect):
            self.inventory.source_button.click()
        self.set_item_value("quality", "50")
        self.inventory.apply_button.click()
        self.assertEqual(self.session.working.items[0].durability_raw, 272700)
        self.assertIn("2727.00 / 3650.00", self.inventory.stat_summary.text())
        self.inventory.repair_button.click()
        self.assertEqual(self.session.working.items[0].durability_raw, 365000)

    def test_fr032_unknown_missing_catalog_metadata_and_missing_stats_have_distinct_messages(self):
        from dataclasses import replace
        from desktop.item_catalog import BY_HASH
        self.load_fixture(current_character_bytes(item_bytes=[Item(-7654321, 0, 0).to_bytes()]))
        self.assertIn("Unknown prefab", self.inventory.stat_summary.text())
        self.assertFalse(self.inventory.repair_button.isEnabled())
        beard = Item(stable_hash("Beard1"), 0, 0)
        self.load_fixture(current_character_bytes(item_bytes=[beard.to_bytes()]))
        self.assertIn("Missing item statistics", self.inventory.stat_summary.text())
        self.assertNotIn("Unknown prefab", self.inventory.metadata.text())
        self.assertFalse(self.inventory.repair_button.isEnabled())
        identifier = stable_hash("CapeDeepNorth")
        with patch.dict(BY_HASH, {identifier: replace(BY_HASH[identifier], maximum_stack=None)}):
            self.load_fixture(current_character_bytes(item_bytes=[Item(identifier, 0, 0).to_bytes()]))
            self.assertIn("missing catalog metadata", self.inventory.metadata.text())
            self.assertFalse(self.inventory.apply_button.isVisible())
            self.assertFalse(self.inventory.repair_button.isEnabled())

    def test_fr018_ammunition_shows_damage_without_default_block_or_repair(self):
        arrow = Item(stable_hash("ArrowBloodGold"), 0, 0, stack=100)
        self.load_fixture(current_character_bytes(item_bytes=[arrow.to_bytes()]))
        self.assertIn("Pierce 100", self.inventory.stat_summary.text())
        self.assertNotIn("Base block", self.inventory.stat_summary.text())
        self.assertNotIn("Armor:", self.inventory.stat_summary.text())
        self.assertFalse(self.inventory.repair_button.isEnabled())

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

    def load_management_fixture(self):
        self.load_fixture(current_character_bytes(item_bytes=[
            Item(stable_hash("SwordIron"), 0, 0, quality=8, durability_raw=109210,
                 crafter_id=42, crafter_name="Synthetic").to_bytes(),
            Item(stable_hash("ShieldWood"), 1, 0, durability_raw=100).to_bytes(),
            Item(stable_hash("Wood"), 2, 0, stack=3).to_bytes(),
            Item(-7654321, 3, 0, custom=[("mod", "opaque")], tail=5).to_bytes(),
        ]))

    def test_fr020_visible_history_buttons_and_keyboard_preserve_drafts(self):
        self.load_management_fixture()
        self.set_item_value("quality", "9")
        self.inventory.apply_button.click()
        after = self.session.working.serialize()
        self.assertTrue(self.window.undo_button.isEnabled())
        self.inventory.grid.setFocus()
        QTest.keyClick(self.inventory.grid, Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier)
        self.assertEqual(self.session.working.serialize(), self.session.baseline.original)
        QTest.keyClick(self.inventory.grid, Qt.Key.Key_Y, Qt.KeyboardModifier.ControlModifier)
        self.assertEqual(self.session.working.serialize(), after)
        self.window.undo_button.click()
        QTest.keyClick(self.inventory.grid, Qt.Key.Key_Z,
                       Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier)
        self.assertEqual(self.session.working.serialize(), after)
        self.set_item_value("quality", "10")
        self.assertFalse(self.window.undo_button.isEnabled())
        QTest.keyClick(self.inventory.fields.editors["quality"], Qt.Key.Key_Z,
                       Qt.KeyboardModifier.ControlModifier)
        self.assertEqual(self.session.working.serialize(), after)
        self.assertEqual(self.inventory.fields.editors["quality"].text(), "10")
        self.assertIn("drafts", self.window.status.text())

    def test_fr054_duplicate_preview_cancel_apply_undo_redo_export(self):
        from desktop.inventory_actions import operation_text
        self.load_management_fixture()
        original = self.session.working.serialize()
        def confirm(parent, title, before, after):
            text = operation_text(before, after)
            self.assertIn("Crafter ID/name: 42 / Synthetic", text)
            self.assertIn("Equipped: False", text)
            self.assertIn("Quality 8", text)
            return False
        with patch("desktop.inventory.confirm_operation", side_effect=confirm):
            self.inventory.stage_operation(("item", 0), "duplicate", (4, 0))
        self.assertEqual(self.session.working.serialize(), original)
        with patch("desktop.inventory.confirm_operation", return_value=True):
            self.inventory.stage_operation(("item", 0), "duplicate", (4, 0))
        self.assertEqual(self.inventory.position, (4, 0))
        self.assertIn("Duplicate", self.window.changes[0].title)
        self.window.undo_button.click()
        self.assertEqual(self.session.working.serialize(), original)
        self.window.redo_button.click()
        self.export_to(self.target)
        self.assertEqual(len(Character(self.target.read_bytes()).items), 5)
        self.assertEqual(self.source.read_bytes(), original)

    def test_fr019_grid_drop_uses_preview_transaction_and_rejects_external_stale(self):
        from types import SimpleNamespace
        from PySide6.QtCore import QPointF
        self.load_management_fixture()
        grid = self.inventory.grid
        # Qt requires a draggable model index before dispatching startDrag.
        self.assertTrue(self.inventory.model.flags(self.inventory.model.index(0, 0)) &
                        Qt.ItemFlag.ItemIsDragEnabled)
        self.assertFalse(self.inventory.model.flags(self.inventory.model.index(0, 4)) &
                         Qt.ItemFlag.ItemIsDragEnabled)
        grid.drag_key = ("item", 0)
        grid.drag_generation = self.session.generation
        point = grid.visualRect(self.inventory.model.index(0, 1)).center()
        accepted = []
        event = SimpleNamespace(position=lambda: QPointF(point), source=lambda: grid,
                                acceptProposedAction=lambda: accepted.append(True),
                                ignore=lambda: accepted.append(False))
        original = self.session.working.serialize()
        with patch("desktop.inventory.confirm_operation", return_value=False):
            grid.dropEvent(event)
        self.assertEqual(self.session.working.serialize(), original)
        with patch("desktop.inventory.confirm_operation", return_value=True):
            grid.dragMoveEvent(event)
            self.assertEqual(grid.drop_target, (1, 0))
            grid.dropEvent(event)
        self.assertEqual(self.session.items[("item", 0)].x, 1)
        self.assertEqual(self.session.items[("item", 1)].x, 0)
        self.assertEqual(self.inventory.key, ("item", 0))
        self.assertEqual(len(self.window.changes), 2)
        self.assertFalse(grid.can_drop((4, 0)))  # stale drag generation
        after = self.session.working.serialize()
        event.source = lambda: object()
        grid.dropEvent(event)
        self.assertEqual(self.session.working.serialize(), after)
        self.assertFalse(accepted[-1])
        self.window.undo_button.click()
        self.assertEqual(self.session.working.serialize(), original)

    def test_fr071_keyboard_destination_dialog_and_fill_quick_action(self):
        self.load_management_fixture()
        with patch("desktop.inventory.DestinationDialog.exec", return_value=QDialog.DialogCode.Accepted), \
             patch("desktop.inventory.confirm_operation", return_value=True):
            self.inventory.quick_buttons["move"].click()
        self.assertEqual(self.session.items[("item", 0)].x, 1)
        self.select(2, 0)
        with patch("desktop.inventory.confirm_operation", return_value=True):
            self.inventory.quick_buttons["fill"].click()
        self.assertEqual(self.session.items[("item", 2)].stack, 50)
        self.assertFalse(self.inventory.quick_buttons["fill"].isEnabled())
        self.select(3, 0)
        self.assertTrue(all(not b.isEnabled() for b in self.inventory.quick_buttons.values()))

    def test_fr054_replacement_dialog_full_preview_and_metadata_reset(self):
        from desktop.inventory_actions import ReplacementDialog, operation_text
        self.load_management_fixture()
        def choose(dialog):
            dialog.search.setText("AxeBronze")
            dialog.results.setCurrentRow(0)
            dialog.quality.setValue(8)
            return QDialog.DialogCode.Accepted
        def confirm(parent, title, before, after):
            text = operation_text(before, after)
            for expected in ("SwordIron", "AxeBronze", "1092.10", "475.00", "42 / Synthetic", "0 / (none)"):
                self.assertIn(expected, text)
            return True
        with patch.object(ReplacementDialog, "exec", choose), \
             patch("desktop.inventory.confirm_operation", side_effect=confirm):
            self.inventory.quick_buttons["replace"].click()
        self.assertEqual(self.session.working.items[0].prefab_hash, stable_hash("AxeBronze"))
        self.assertEqual(len(self.window.changes), 2)
        self.window.undo_button.click()
        self.assertEqual(self.session.working.serialize(), self.session.baseline.original)

    def test_fr090_equipment_preview_overview_and_flag_control(self):
        self.load_management_fixture()
        self.assertFalse(self.inventory.fields.equipped.isEnabled())
        with patch("desktop.inventory.confirm_operation", return_value=True):
            self.inventory.quick_buttons["equip"].click()
        self.assertTrue(self.session.items[("item", 0)].equipped)
        self.assertIn("Iron Sword", self.inventory.equipped_overview.text())
        self.assertIn("Equipped", self.inventory.model.index(0, 0).data(ACCESSIBLE))
        self.window.undo_button.click()
        self.assertFalse(self.session.items[("item", 0)].equipped)

    def test_fr072_changed_state_during_preview_is_rejected(self):
        self.load_management_fixture()
        def changed(parent, title, before, after):
            self.session.edit_item(("item", 1), {"quality": 2})
            return True
        with patch("desktop.inventory.confirm_operation", side_effect=changed):
            self.inventory.stage_operation(("item", 0), "move", (4, 0))
        self.assertEqual(self.session.items[("item", 0)].x, 0)
        self.assertIn("fresh operation preview", self.inventory.error.text())
