"""Small inventory dialogs; all mutations remain in validated session commands."""

from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLineEdit,
    QListWidget, QPlainTextEdit, QSpinBox, QVBoxLayout,
)
from PySide6.QtCore import Qt

from core.item_stats import calculate_item_stats
from desktop.item_catalog import ENTRIES, item_entry
from desktop.session import durability_text, item_name, slot_name
from desktop.theme import label


def item_description(item):
    if item is None:
        return "(absent)"
    entry = item_entry(item)
    stats = calculate_item_stats(item)
    maximum = stats.maximum_durability if stats else None
    return (f"{item_name(item)} [{entry.prefab if entry else item.prefab_hash}]\n"
            f"{slot_name((item.x, item.y))} · Quality {item.quality} · Quantity {item.stack}\n"
            f"Durability {durability_text(item.durability_raw)} / "
            f"{maximum if maximum is not None else 'unavailable/inapplicable'}\n"
            f"Equipped: {item.equipped} · Picked up: {item.picked}\n"
            f"Crafter ID/name: {item.crafter_id} / {item.crafter_name or '(none)'}\n"
            f"Variant {item.variant} · World level {item.world_level} · Trailing flags {item.tail}\n"
            f"Custom metadata: {item.custom or '(none)'}")


def operation_text(before, after):
    lines = []
    for key in dict.fromkeys([*before, *after]):
        old, new = before.get(key), after.get(key)
        if old and new and old.to_bytes() == new.to_bytes():
            continue
        lines.extend(("BEFORE", item_description(old), "AFTER", item_description(new), ""))
    return "\n".join(lines) or "No serialized changes."


def confirm_operation(parent, title, before, after):
    dialog = QDialog(parent)
    dialog.setWindowTitle(title + " Preview")
    dialog.resize(670, 530)
    layout = QVBoxLayout(dialog)
    layout.addWidget(label("Review all affected records. Nothing changes until you stage this operation.", wrap=True))
    text = QPlainTextEdit(operation_text(before, after))
    text.setReadOnly(True)
    text.setAccessibleName("Complete operation preview")
    layout.addWidget(text)
    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
    buttons.addButton("Stage " + title, QDialogButtonBox.ButtonRole.AcceptRole)
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)
    accepted = dialog.exec() == QDialog.DialogCode.Accepted
    dialog.deleteLater()
    return accepted


class DestinationDialog(QDialog):
    def __init__(self, parent, session, key, duplicate=False):
        super().__init__(parent)
        self.setWindowTitle("Duplicate destination" if duplicate else "Move or Swap")
        layout = QVBoxLayout(self)
        layout.addWidget(label("Choose a destination; occupied slots require a previewed swap.", wrap=True))
        self.slots = QComboBox()
        self.slots.setAccessibleName("Inventory destination")
        selected = session.items[key]
        positions = {(i.x, i.y): i for i in session.items.values()}
        for y in range(session.working.writable_inventory_rows):
            for x in range(8):
                position = (x, y)
                other = positions.get(position)
                if position == (selected.x, selected.y) or duplicate and other:
                    continue
                caption = f"{slot_name(position)} — " + (f"Swap with {item_name(other)}" if other else "Empty")
                self.slots.addItem(caption, position)
        layout.addWidget(self.slots)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(bool(self.slots.count()))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)


class ReplacementDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Replace Item")
        self.resize(580, 480)
        layout = QVBoxLayout(self)
        layout.addWidget(label("Fresh-item policy: unequipped, new metadata, calculated full durability. "
                               "The next screen shows every old and new property.", wrap=True))
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search replacement name or prefab")
        self.search.setAccessibleName("Search replacement")
        layout.addWidget(self.search)
        self.results = QListWidget()
        self.results.setAccessibleName("Replacement catalog")
        layout.addWidget(self.results)
        form = QFormLayout()
        self.quality, self.quantity = QSpinBox(), QSpinBox()
        self.quality.setRange(1, 65535)
        self.quantity.setRange(1, 1)
        self.quality.setAccessibleName("Replacement quality")
        self.quantity.setAccessibleName("Replacement quantity")
        form.addRow("Quality", self.quality)
        form.addRow("Quantity", self.quantity)
        layout.addLayout(form)
        self.notice = label("Above-normal quality is not guaranteed safe in-game.", "warning", wrap=True)
        layout.addWidget(self.notice)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.ok = buttons.button(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.search.textChanged.connect(self.filter)
        self.results.currentRowChanged.connect(self.select)
        self.filter()

    def filter(self):
        query = self.search.text().casefold()
        self.entries = [e for e in ENTRIES if query in f"{e.name} {e.prefab}".casefold()]
        self.results.clear()
        self.results.addItems([f"{e.name} · {e.prefab}" for e in self.entries])
        self.ok.setEnabled(False)

    def select(self, row):
        self.ok.setEnabled(row >= 0)
        if row >= 0:
            self.quantity.setMaximum(self.entries[row].maximum_stack or 1)

    def values(self):
        row = self.results.currentRow()
        return self.entries[row].prefab, self.quality.value(), self.quantity.value()
