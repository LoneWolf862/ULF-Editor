"""ULF desktop shell and verified file workflow."""

from copy import deepcopy
from pathlib import Path
import sys

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Qt, Signal, Slot, QEvent
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication, QDialog, QFileDialog, QFormLayout, QHBoxLayout, QMainWindow,
    QMessageBox, QPushButton, QSizePolicy, QStackedWidget, QTabWidget, QVBoxLayout, QWidget,
)

from core.export import export_character
from core.fch import FormatError
from desktop.inventory import InventoryPage
from desktop.session import Session, load_character
from desktop.skills import SkillsPage
from desktop.theme import apply_theme, artwork, heading, label, panel, primary_button, scroll_area


class FileSignals(QObject):
    finished = Signal(object, str)


class FileJob(QRunnable):
    def __init__(self, operation):
        super().__init__()
        self.operation = operation
        self.signals = FileSignals()

    def run(self):
        try:
            result = self.operation()
        except Exception as error:
            self.signals.finished.emit(None, str(error) or type(error).__name__)
        else:
            self.signals.finished.emit(result, "")


class ReviewPage(QWidget):
    discard_change = Signal(object)

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(heading("Review Changes"))
        layout.addWidget(label("Compare with the loaded original. Save As exports a separate copy.", "muted", wrap=True))
        self.inventory_drafts = QPushButton("Resolve inventory drafts")
        self.skill_drafts = QPushButton("Resolve skill drafts")
        draft_actions = QHBoxLayout()
        draft_actions.addWidget(self.inventory_drafts)
        draft_actions.addWidget(self.skill_drafts)
        draft_actions.addStretch(1)
        layout.addLayout(draft_actions)
        content = QWidget()
        self.cards = QVBoxLayout(content)
        self.cards.setContentsMargins(0, 0, 8, 0)
        layout.addWidget(scroll_area(content), 1)
        self.notice = label(role="warning", wrap=True)
        layout.addWidget(self.notice)
        actions = QHBoxLayout()
        self.discard_all = QPushButton("Discard All…")
        self.export = primary_button("Export Save As…")
        actions.addWidget(self.discard_all)
        actions.addStretch(1)
        actions.addWidget(self.export)
        layout.addLayout(actions)

    def show_changes(self, changes):
        while self.cards.count():
            widget = self.cards.takeAt(0).widget()
            if widget is not None:
                widget.hide()
                widget.deleteLater()
        if not changes:
            self.cards.addWidget(label("No applied differences from the loaded original.", "muted", wrap=True))
        for group, title in (("inventory", "Inventory"), ("skills", "Skills")):
            subset = [change for change in changes if (change.position is None) == (group == "skills")]
            if not subset:
                continue
            self.cards.addWidget(heading(title, 1.15))
            for change in subset:
                card = panel()
                layout = QHBoxLayout(card)
                details = QVBoxLayout()
                details.addWidget(heading(change.title, 1.05))
                details.itemAt(0).widget().setWordWrap(True)
                details.addWidget(label("\n".join(change.details), "muted", wrap=True))
                if change.warning:
                    details.addWidget(label(change.warning, "warning", wrap=True))
                layout.addLayout(details, 1)
                discard = QPushButton("Discard Change")
                discard.setAccessibleName(f"Discard change: {change.title}")
                discard.clicked.connect(lambda checked=False, change=change: self.discard_change.emit(change))
                layout.addWidget(discard)
                self.cards.addWidget(card)
        self.cards.addStretch(1)

    def show_state(self, session, changes, duplicate_positions):
        self.inventory_drafts.setVisible(bool(session.item_drafts))
        self.skill_drafts.setVisible(bool(session.skill_drafts))
        notices = []
        if session.has_drafts:
            notices.append("Apply or discard unapplied drafts before exporting.")
        if duplicate_positions:
            notices.append("Duplicate inventory positions prevent safe export. See Inventory diagnostics.")
        if session.export_path:
            notices.append(f"Last verified export: {session.export_path}")
        self.notice.setText("\n".join(notices))
        self.notice.setVisible(bool(notices))
        self.discard_all.setEnabled(bool(changes or session.has_drafts))
        self.export.setEnabled(not session.has_drafts and not duplicate_positions)


class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.session = None
        self.changes = []
        self.duplicate_positions = set()
        self.job = None
        self.on_success = None
        self.failure_title = ""
        self.setWindowTitle("ULF · Valheim Character Workshop")
        self.resize(1210, 760)
        self.setMinimumSize(570, 420)
        canvas = QWidget(objectName="canvas")
        self.setCentralWidget(canvas)
        shell = QVBoxLayout(canvas)
        shell.setContentsMargins(18, 12, 18, 12)
        shell.setSpacing(10)

        brand = QHBoxLayout()
        mark = label()
        mark.setPixmap(artwork("wolf").pixmap(27, 27))
        brand.addWidget(mark)
        wordmark = heading("ULF", 1.65, serif=True)
        wordmark.setObjectName("brand")
        brand.addWidget(wordmark)
        brand.addStretch(1)
        brand.addWidget(label("ᚢ   Alpha 0.4", "muted"))
        shell.addLayout(brand)

        header = panel()
        header_layout = QHBoxLayout(header)
        identity = QVBoxLayout()
        identity.setSpacing(3)
        self.character_name = heading("No character loaded", 1.85, serif=True)
        self.character_name.setWordWrap(True)
        identity.addWidget(self.character_name)
        self.source = label(role="muted", wrap=True)
        identity.addWidget(self.source)
        self.validation = label(role="verified", wrap=True)
        identity.addWidget(self.validation)
        self.pending = label(role="warning", wrap=True)
        identity.addWidget(self.pending)
        header_layout.addLayout(identity, 1)
        header_actions = QVBoxLayout()
        buttons = QHBoxLayout()
        self.open_button = QPushButton("Open Character…")
        self.review_button = primary_button("Review Changes")
        buttons.addWidget(self.open_button)
        buttons.addWidget(self.review_button)
        header_actions.addLayout(buttons)
        self.details_button = QPushButton("Character Details")
        header_actions.addWidget(self.details_button, alignment=Qt.AlignmentFlag.AlignRight)
        history_buttons = QHBoxLayout()
        self.undo_button = QPushButton("Undo")
        self.redo_button = QPushButton("Redo")
        history_buttons.addWidget(self.undo_button)
        history_buttons.addWidget(self.redo_button)
        header_actions.addLayout(history_buttons)
        header_layout.addLayout(header_actions)
        shell.addWidget(header)

        self.pages = QStackedWidget()
        empty = QWidget()
        empty_layout = QVBoxLayout(empty)
        empty_layout.addStretch()
        empty_layout.addWidget(heading("Open a Valheim character"), alignment=Qt.AlignmentFlag.AlignHCenter)
        empty_layout.addWidget(label("Choose a local .fch file to inspect and edit.", "muted"),
                               alignment=Qt.AlignmentFlag.AlignHCenter)
        open_empty = primary_button("Open Character…")
        empty_layout.addWidget(open_empty, alignment=Qt.AlignmentFlag.AlignHCenter)
        empty_layout.addStretch()
        self.pages.addWidget(empty)
        self.tabs = QTabWidget()
        self.inventory = InventoryPage()
        self.skills = SkillsPage()
        self.review = ReviewPage()
        self.tabs.addTab(self.inventory, "Inventory")
        self.tabs.addTab(self.skills, "Skills")
        self.tabs.addTab(self.review, "Review")
        self.pages.addWidget(self.tabs)
        shell.addWidget(self.pages, 1)
        self.status = label(role="muted", wrap=True)
        self.status.setAccessibleName("Session and file operation status")
        self.status.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        shell.addWidget(self.status)
        self.message = ""

        self.open_button.clicked.connect(self.open_file)
        open_empty.clicked.connect(self.open_file)
        self.review_button.clicked.connect(self.show_review)
        self.details_button.clicked.connect(self.character_details)
        self.inventory.changed.connect(self.refresh_review)
        self.inventory.drafts_changed.connect(self.refresh_status)
        self.skills.changed.connect(self.refresh_review)
        self.skills.drafts_changed.connect(self.refresh_status)
        self.review.inventory_drafts.clicked.connect(self.resolve_inventory_draft)
        self.review.skill_drafts.clicked.connect(self.resolve_skill_draft)
        self.review.discard_change.connect(self.discard_change)
        self.review.discard_all.clicked.connect(self.discard_all)
        self.review.export.clicked.connect(self.export)
        self.undo_button.clicked.connect(lambda: self.travel_history(False))
        self.redo_button.clicked.connect(lambda: self.travel_history(True))
        QApplication.instance().installEventFilter(self)
        QShortcut(QKeySequence.StandardKey.Open, self, activated=self.open_file)
        QShortcut(QKeySequence.StandardKey.SaveAs, self, activated=self.save_shortcut)
        apply_theme(self)
        self.refresh_status()

    def eventFilter(self, watched, event):
        if (event.type() in (QEvent.Type.ShortcutOverride, QEvent.Type.KeyPress)
                and isinstance(watched, QWidget) and (watched is self or self.isAncestorOf(watched))
                and event.modifiers() & Qt.KeyboardModifier.ControlModifier
                and event.key() in (Qt.Key.Key_Z, Qt.Key.Key_Y)):
            if event.type() == QEvent.Type.KeyPress:
                self.travel_history(event.key() == Qt.Key.Key_Y or
                                    bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier))
            event.accept()
            return True
        return super().eventFilter(watched, event)

    def travel_history(self, redo):
        if self.job is not None or self.session is None or QApplication.activeModalWidget() is not None:
            return
        key = self.inventory.key
        try:
            self.session.redo() if redo else self.session.undo()
        except FormatError as error:
            self.message = str(error)
            self.refresh_status()
        else:
            item = self.session.items.get(key)
            self.inventory.refresh((item.x, item.y) if item else None)
            self.skills.refresh()
            self.refresh_review()

    def start_job(self, operation, message, failure_title, on_success):
        if self.job is not None:
            return
        self.message = message
        self.failure_title = failure_title
        self.on_success = on_success
        self.job = FileJob(operation)
        self.job.signals.finished.connect(self.finish_job, Qt.ConnectionType.QueuedConnection)
        self.refresh_status()
        QThreadPool.globalInstance().start(self.job)

    @Slot(object, str)
    def finish_job(self, result, error):
        self.job = None
        on_success, self.on_success = self.on_success, None
        if error:
            self.message = f"{self.failure_title} · {error}"
            self.refresh_status()
            dialog = QMessageBox(QMessageBox.Icon.Critical, self.failure_title, error,
                                 QMessageBox.StandardButton.Ok, self)
            dialog.setTextFormat(Qt.TextFormat.PlainText)
            dialog.exec()
            return
        self.message = ""
        on_success(result)
        self.refresh_status()

    def confirm_discard(self, action):
        if not self.session or not self.session.unsaved:
            return True
        return QMessageBox.question(
            self, "Unsaved Edits", f"{action}? Unexported edits and drafts will be discarded.",
            QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        ) == QMessageBox.StandardButton.Discard

    def open_file(self):
        if self.job is not None:
            return
        filename, _ = QFileDialog.getOpenFileName(self, "Open Valheim Character", "", "Valheim character (*.fch)")
        if filename and self.confirm_discard("Open another character"):
            self.load_path(Path(filename))

    def load_path(self, path):
        self.start_job(lambda: Session(load_character(path), path), f"Validating {path.name}…",
                       "Could not open character", self.set_session)

    def set_session(self, session):
        self.session = session
        self.character_name.setText(session.baseline.name or "Unnamed character")
        self.source.setText(session.path.name)
        self.source.setToolTip(str(session.path))
        self.validation.setText("✓ SHA-512 and byte-exact round trip passed")
        self.inventory.set_session(session)
        self.skills.set_session(session)
        self.tabs.setCurrentWidget(self.inventory)
        self.pages.setCurrentWidget(self.tabs)
        self.refresh_review()
        self.inventory.grid.setFocus()

    def character_details(self):
        character = self.session.baseline
        dialog = QDialog(self)
        dialog.setWindowTitle("Character Details")
        dialog.resize(580, 290)
        layout = QVBoxLayout(dialog)
        layout.addWidget(heading(character.name or "Unnamed character", serif=True))
        rows = QFormLayout()
        for title, value in (
            ("Source", str(self.session.path)),
            ("Versions", f"Profile {character.profile_version} · Player {character.player_version}\n"
                         f"Inventory {character.inventory_version} · Skills {character.skills_version}"),
            ("Validation", "SHA-512 passed · Byte-exact round trip passed"),
            ("Saved cheat flag", "Set" if character.used_cheats else "Clear"),
        ):
            field = label(value, wrap=True)
            field.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            rows.addRow(title, field)
        layout.addLayout(rows)
        layout.addWidget(label("Achievement eligibility is unverified.", "muted", wrap=True))
        close = QPushButton("Close")
        close.clicked.connect(dialog.accept)
        layout.addWidget(close, alignment=Qt.AlignmentFlag.AlignRight)
        dialog.exec()
        dialog.deleteLater()

    def refresh_review(self):
        self.changes = self.session.changes()
        self.duplicate_positions = self.session.duplicate_positions
        self.review.show_changes(self.changes)
        self.message = ""
        self.refresh_status()

    def refresh_status(self):
        session = self.session
        busy = self.job is not None
        self.open_button.setEnabled(not busy)
        self.pages.setEnabled(not busy)
        self.review_button.setEnabled(bool(session and not busy))
        self.details_button.setEnabled(bool(session and not busy))
        for button, stack in ((self.undo_button, session.history.past if session else []),
                              (self.redo_button, session.history.future if session else [])):
            button.setEnabled(bool(stack and session and not session.has_drafts and not busy))
            button.setToolTip(("Apply or revert drafts first." if session and session.has_drafts else
                               stack[-1].label if stack else "No history"))
        if session:
            self.inventory.refresh_quick_actions()
        if not session:
            self.pending.hide()
            self.status.setText(self.message)
            return
        self.pending.show()
        self.review.show_state(session, self.changes, self.duplicate_positions)
        self.tabs.setTabText(0, "Inventory · Draft" if session.item_drafts else "Inventory")
        self.tabs.setTabText(1, "Skills · Draft" if session.skill_drafts else "Skills")
        self.tabs.setTabText(2, f"Review ({len(self.changes)})")
        parts = []
        if session.has_drafts:
            parts.append("Unapplied edits")
        if session.revision != session.exported_revision:
            count = len(self.changes)
            parts.append(f"{count} applied change{'s' if count != 1 else ''} vs original · Export pending"
                         if count else "Changes to export")
        elif session.export_path:
            parts.append("Export verified")
        elif not parts:
            parts.append("No pending changes")
        self.pending.setText(" · ".join(parts))
        if self.message:
            self.status.setText(self.message)
        elif session.export_path:
            self.status.setText(f"Last verified export · {session.export_path}")
        else:
            self.status.setText("Save As creates a separate copy.")

    def resolve_inventory_draft(self):
        key = next(iter(self.session.item_drafts))
        item = self.session.items[key]
        self.tabs.setCurrentWidget(self.inventory)
        self.inventory.grid.setCurrentIndex(self.inventory.model.index(item.y, item.x))
        self.inventory.open_inspector()

    def resolve_skill_draft(self):
        key = next(iter(self.session.skill_drafts))
        self.tabs.setCurrentWidget(self.skills)
        row = self.skills.rows[key]
        self.skills.scroll.ensureWidgetVisible(row)
        if row.level.text() != row.original[0]:
            row.level.setFocus()
        else:
            row.toggle.setChecked(True)
            row.experience.setFocus()

    def show_review(self):
        if self.session and self.job is None:
            self.tabs.setCurrentWidget(self.review)

    def save_shortcut(self):
        if self.tabs.currentWidget() is self.review:
            self.export()
        else:
            self.show_review()

    def discard_change(self, change):
        keys = {change.key}
        dependencies = self.session.discard_dependencies(change)
        if dependencies.intersection(self.session.items):
            answer = QMessageBox.question(
                self, "Discard Related Changes",
                "Restoring this item requires discarding the new item in its slot. Discard both changes?",
                QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            if answer != QMessageBox.StandardButton.Discard:
                return
        elif (change.key in self.session.item_drafts or
              change.key[0] == "skill" and change.key[1] in self.session.skill_drafts):
            answer = QMessageBox.question(
                self, "Discard Change and Draft", "Discard this applied change and its unapplied draft?",
                QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            if answer != QMessageBox.StandardButton.Discard:
                return
        try:
            self.session.discard(keys | dependencies)
        except FormatError as error:
            self.message = str(error)
            self.refresh_status()
        else:
            self.refresh_editors()

    def discard_all(self):
        answer = QMessageBox.question(
            self, "Discard All Changes", "Restore the loaded original in the editor and clear all drafts?",
            QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer == QMessageBox.StandardButton.Discard:
            self.session.discard_all()
            self.refresh_editors()

    def refresh_editors(self):
        self.inventory.refresh()
        self.skills.refresh()
        self.refresh_review()

    def export(self):
        session = self.session
        if self.job is not None or not session:
            return
        self.show_review()
        if session.has_drafts or self.duplicate_positions:
            return
        default = session.path.with_name(session.path.stem + "_ULF_edited.fch")
        filename, _ = QFileDialog.getSaveFileName(self, "Export Verified Character Copy", str(default),
                                                   "Valheim character (*.fch)")
        if not filename:
            return
        destination = Path(filename)
        if not destination.suffix:
            destination = destination.with_suffix(".fch")
            # The picker confirmed the extensionless name, so confirm a suffixed collision.
            if destination.exists() and QMessageBox.question(
                self, "Replace Export", f"Replace {destination}?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            ) != QMessageBox.StandardButton.Yes:
                return
        if destination.suffix.lower() != ".fch":
            self.message = "Choose a destination with the .fch extension."
            self.refresh_status()
            return
        snapshot = deepcopy(session.working)
        self.start_job(lambda: export_character(snapshot, session.path, destination),
                       f"Writing and verifying {destination}…", "Export failed", self.export_finished)

    def export_finished(self, destination):
        self.session.export_path = destination
        self.session.exported_revision = self.session.revision

    def closeEvent(self, event):
        if self.job is not None:
            event.ignore()
            return
        if self.confirm_discard("Close ULF"):
            event.accept()
        else:
            event.ignore()


def main():
    application = QApplication(sys.argv)
    application.setApplicationName("ULF Editor")
    window = Window()
    window.show()
    if len(sys.argv) > 1:
        window.load_path(Path(sys.argv[1]))
    sys.exit(application.exec())
