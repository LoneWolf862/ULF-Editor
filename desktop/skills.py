"""Skill rows with precise numeric drafts and atomic application."""

from collections import defaultdict
import math
import re

from PySide6.QtCore import QSignalBlocker, Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QPushButton, QSlider, QVBoxLayout, QWidget

from core.fch import FormatError, SKILLS
from desktop.session import display_number, float32, same_number
from desktop.theme import heading, label, panel, primary_button, scroll_area, set_invalid


def parse_number(text, column):
    error = ("Enter a finite skill level between 0 and 100." if column == 0 else
             "Enter finite experience from 0 to below 1,000,000,000.")
    if not re.fullmatch(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?", text.strip()):
        raise FormatError(error)
    value = float(text)
    if not math.isfinite(value) or value < 0 or (value > 100 if column == 0 else value >= 1e9):
        raise FormatError(error)
    value = float32(value)
    if column == 1 and value >= 1e9:
        raise FormatError(error)
    return value


def ordinary(value, column):
    return math.isfinite(value) and value >= 0 and (value <= 100 if column == 0 else value < 1e9)


class SkillRow(QWidget):
    edited = Signal(int)

    def __init__(self, skill_id, name):
        super().__init__()
        self.skill_id = skill_id
        self.values = (0.0, 0.0)
        self.original = ("0", "0")
        self.updating = False
        self.ambiguous = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        card = panel()
        layout.addWidget(card)
        card_layout = QVBoxLayout(card)
        row = QHBoxLayout()
        identity = QVBoxLayout()
        title = heading(name, 1.15)
        title.setMinimumWidth(125)
        identity.addWidget(title)
        self.applied = label(role="muted", wrap=True)
        identity.addWidget(self.applied)
        row.addLayout(identity, 2)
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setAccessibleName(f"{name} level slider")
        self.slider.setAccessibleDescription("Range 0 to 100, arrow keys adjust by 0.1.")
        self.slider.setRange(0, 1000)
        self.slider.setSingleStep(1)
        self.slider.setPageStep(50)
        row.addWidget(self.slider, 4)
        self.level = QLineEdit()
        self.level.setAccessibleName(f"{name} level")
        self.level.setMaxLength(36)
        self.level.setFixedWidth(103)
        row.addWidget(self.level)
        self.toggle = QPushButton("Experience")
        self.toggle.setAccessibleName(f"Show {name} experience")
        self.toggle.setCheckable(True)
        row.addWidget(self.toggle)
        card_layout.addLayout(row)
        self.experience_area = QWidget()
        xp = QHBoxLayout(self.experience_area)
        xp.setContentsMargins(0, 0, 0, 0)
        self.xp_label = label(role="muted", wrap=True)
        xp.addWidget(self.xp_label, 1)
        self.experience = QLineEdit()
        self.experience.setAccessibleName(f"{name} experience")
        self.experience.setMaxLength(36)
        self.experience.setFixedWidth(130)
        xp.addWidget(self.experience)
        card_layout.addWidget(self.experience_area)
        self.experience_area.hide()
        self.marker = label(role="warning", wrap=True)
        card_layout.addWidget(self.marker)
        self.marker.hide()
        self.toggle.toggled.connect(self.show_experience)
        self.slider.valueChanged.connect(self.move_slider)
        self.level.textChanged.connect(self.changed)
        self.experience.textChanged.connect(self.changed)

    def show_experience(self, shown):
        self.experience_area.setVisible(shown)
        name = SKILLS[self.skill_id]
        self.toggle.setAccessibleName(f"{'Hide' if shown else 'Show'} {name} experience")

    def populate(self, records, draft):
        self.updating = True
        self.ambiguous = len(records) > 1
        self.values = tuple(records[0][1:]) if records else (0.0, 0.0)
        self.original = tuple(
            display_number(value) if ordinary(value, column) else ""
            for column, value in enumerate(self.values)
        )
        if self.ambiguous:
            self.applied.setText(f"{len(records)} duplicate records · Read-only")
        elif records:
            value = display_number(self.values[0])
            self.applied.setText(f"Applied {value}" if self.original[0] else f"Saved {value} · Enter a correction")
        else:
            self.applied.setText("Applied 0 · No saved record")
        self.xp_label.setText(f"Saved experience {display_number(self.values[1])} · Preserved unless edited")
        texts = draft or self.original
        for field, text in zip((self.level, self.experience), texts):
            field.setText(text)
            field.setEnabled(not self.ambiguous)
            set_invalid(field, False)
        self.slider.setEnabled(not self.ambiguous)
        self.sync_slider()
        self.show_marker()
        self.updating = False

    def move_slider(self, tick):
        self.level.setText(f"{tick / 10:g}")

    def sync_slider(self):
        with QSignalBlocker(self.slider):
            try:
                level = parse_number(self.level.text(), 0)
            except FormatError:
                if not self.level.text():
                    self.slider.setValue(0)
            else:
                self.slider.setValue(round(level * 10))

    def draft(self):
        texts = (self.level.text(), self.experience.text())
        for column, text in enumerate(texts):
            if text == self.original[column]:
                continue
            try:
                value = parse_number(text, column)
            except FormatError:
                return texts
            if not same_number(value, self.values[column]):
                return texts
        return None

    def show_marker(self):
        draft = self.draft()
        parts = []
        if draft:
            for column, (text, original) in enumerate(zip(draft, self.original)):
                if text == original:
                    continue
                name = "Level" if column == 0 else "XP"
                try:
                    value = parse_number(text, column)
                except FormatError:
                    parts.append(f"{name}: invalid input")
                else:
                    if not same_number(value, self.values[column]):
                        parts.append(f"{name}  {display_number(self.values[column])} → {display_number(value)}")
        self.marker.setText("Draft · " + " · ".join(parts) if parts else "")
        self.marker.setVisible(bool(parts))

    def changed(self):
        if self.updating:
            return
        self.sync_slider()
        self.show_marker()
        set_invalid(self.level, False)
        set_invalid(self.experience, False)
        self.edited.emit(self.skill_id)

    def proposal(self):
        result = []
        for column, (field, original) in enumerate(zip((self.level, self.experience), self.original)):
            value = None
            if field.text() != original:
                try:
                    value = parse_number(field.text(), column)
                except FormatError:
                    if column == 1:
                        self.toggle.setChecked(True)
                    set_invalid(field, True)
                    field.setFocus()
                    raise
                if same_number(value, self.values[column]):
                    value = None
            result.append(value)
        return (self.skill_id, *result)


class SkillsPage(QWidget):
    changed = Signal()
    drafts_changed = Signal()

    def __init__(self):
        super().__init__()
        self.session = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(heading("Skills"))
        self.summary = label(role="muted", wrap=True)
        layout.addWidget(self.summary)
        content = QWidget()
        rows = QVBoxLayout(content)
        rows.setContentsMargins(0, 0, 9, 0)
        self.rows = {key: SkillRow(key, name) for key, name in SKILLS.items()}
        for row in self.rows.values():
            rows.addWidget(row)
            row.edited.connect(self.update_draft)
        self.diagnostics = label(role="warning", wrap=True)
        rows.addWidget(self.diagnostics)
        self.scroll = scroll_area(content)
        layout.addWidget(self.scroll, 1)
        self.error = label(role="error", wrap=True)
        self.error.setAccessibleName("Skill validation error")
        layout.addWidget(self.error)
        buttons = QHBoxLayout()
        self.apply_button = primary_button("Apply Skill Changes")
        self.discard_button = QPushButton("Discard Skill Drafts")
        buttons.addWidget(self.apply_button)
        buttons.addWidget(self.discard_button)
        buttons.addStretch(1)
        layout.addLayout(buttons)
        self.apply_button.clicked.connect(self.apply)
        self.discard_button.clicked.connect(self.discard)

    def set_session(self, session):
        if session is not self.session:
            for row in self.rows.values():
                row.toggle.setChecked(False)
            self.scroll.verticalScrollBar().setValue(0)
        self.session = session
        self.refresh()

    def refresh(self):
        records = defaultdict(list)
        for record in self.session.working.skills:
            records[record[0]].append(record)
        for key, row in self.rows.items():
            row.populate(records[key], self.session.skill_drafts.get(key))
        diagnostics = []
        for key, entries in records.items():
            if key not in SKILLS or len(entries) > 1:
                for _, level, xp in entries:
                    diagnostics.append(f"{SKILLS.get(key, 'Unknown skill')} (ID {key}) · "
                                       f"Level {display_number(level)} · XP {display_number(xp)}")
        self.diagnostics.setText("Preserved skill records\n" + "\n".join(diagnostics) if diagnostics else "")
        self.diagnostics.setVisible(bool(diagnostics))
        self.error.clear()
        self.update_summary()

    def update_summary(self):
        count = len(self.session.skill_drafts)
        self.summary.setText(f"{count} skill draft{'s' if count != 1 else ''}" if count else "No unapplied skill edits")
        self.apply_button.setEnabled(bool(count))
        self.discard_button.setEnabled(bool(count))

    def update_draft(self, key):
        if self.session is None:
            return
        draft = self.rows[key].draft()
        if draft:
            self.session.skill_drafts[key] = draft
        else:
            self.session.skill_drafts.pop(key, None)
        self.error.clear()
        self.update_summary()
        self.drafts_changed.emit()

    def apply(self):
        try:
            changes = [row.proposal() for key, row in self.rows.items() if key in self.session.skill_drafts]
            self.session.apply_skill_batch(changes)
        except FormatError as error:
            self.error.setText(str(error))
            focus = self.focusWidget()
            if focus is not None and self.scroll.widget().isAncestorOf(focus):
                self.scroll.ensureWidgetVisible(focus)
        else:
            self.refresh()
            self.changed.emit()

    def discard(self):
        self.session.skill_drafts.clear()
        self.refresh()
        self.drafts_changed.emit()
