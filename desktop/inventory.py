"""Inventory grid, item inspector and offline item creation."""

from collections import defaultdict
from decimal import Decimal, InvalidOperation
import re

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QAbstractItemView, QAbstractSpinBox, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout,
    QHBoxLayout, QHeaderView, QLineEdit, QListWidget, QListWidgetItem, QMessageBox,
    QPlainTextEdit, QProgressBar, QPushButton, QStyledItemDelegate, QStyle,
    QStyleOptionSpinBox, QTableView, QVBoxLayout, QWidget,
)

from core.fch import FormatError
from core.item_stats import GAME_VERSION, SNAPSHOT, calculate_item_stats
from desktop.item_catalog import CATALOG_VERSION, ENTRIES, item_entry, search_catalog
from desktop.session import durability_text, item_name, slot_name
from desktop.theme import heading, item_icon, label, panel, primary_button, scroll_area, set_invalid, theme_active


DISPLAY = Qt.ItemDataRole.DisplayRole
ACCESSIBLE = Qt.ItemDataRole.AccessibleTextRole
CELL = Qt.ItemDataRole.UserRole


class InventoryModel(QAbstractTableModel):
    def __init__(self, parent):
        super().__init__(parent)
        self.positions = {}
        self.height = 6

    def set_items(self, items):
        self.beginResetModel()
        positions = defaultdict(list)
        for key, item in items.items():
            positions[item.x, item.y].append((key, item))
        self.positions = positions
        self.height = max((y + 1 for x, y in positions if x < 8), default=6)
        self.height = max(6, self.height)
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else self.height

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else 8

    def data(self, index, role=DISPLAY):
        if not index.isValid():
            return None
        position = (index.column(), index.row())
        records = self.positions.get(position, ())
        if role == CELL:
            return records
        if role in (DISPLAY, ACCESSIBLE, Qt.ItemDataRole.ToolTipRole):
            if not records:
                text = "Empty slot"
            elif len(records) > 1:
                text = f"Conflicting slot, {len(records)} records"
            else:
                item = records[0][1]
                text = f"{item_name(item)}, quantity {item.stack}, quality {item.quality}"
            return f"{text} · {slot_name(position)}"


class SlotDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        painter.save()
        rect = option.rect.adjusted(3, 3, -3, -3)
        records = index.data(CELL)
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        focused = bool(option.state & QStyle.StateFlag.State_HasFocus)
        high_contrast = not option.widget.window().styleSheet()
        if high_contrast:
            background = option.palette.highlight().color() if selected else option.palette.base().color()
            foreground = option.palette.highlightedText().color() if selected else option.palette.text().color()
            border = foreground
        else:
            background = QColor("#503923" if selected else "#302a24" if records else "#191a1b")
            foreground = QColor("#f2e9da")
            border = QColor("#e3bb79" if selected else "#89796c")
        painter.setBrush(background)
        painter.setPen(QPen(border, 2 if selected else 1))
        painter.drawRoundedRect(rect, 5, 5)
        if focused:
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(foreground, 1, Qt.PenStyle.DashLine))
            painter.drawRoundedRect(rect.adjusted(3, 3, -3, -3), 3, 3)
        painter.setPen(foreground)
        if len(records) > 1:
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "Conflict")
        elif records:
            item = records[0][1]
            font = option.font
            font.setPointSizeF(max(8, font.pointSizeF() - 1))
            painter.setFont(font)
            metrics = painter.fontMetrics()
            caption = rect.adjusted(5, 0, -5, -4)
            badge = QRect(rect.left() + 4, rect.top() + 3, rect.width() - 8, metrics.height())
            quality, stack = f"Q{item.quality}", f"×{item.stack}"
            if metrics.horizontalAdvance(quality + " " + stack) <= badge.width():
                painter.drawText(badge, Qt.AlignmentFlag.AlignLeft, quality)
                painter.drawText(badge, Qt.AlignmentFlag.AlignRight, stack)
                icon_size = min(28, rect.height() - 31, rect.width() - 8)
            else:
                painter.drawText(badge, Qt.AlignmentFlag.AlignCenter, stack)
                badge.translate(0, metrics.height())
                painter.drawText(badge, Qt.AlignmentFlag.AlignCenter, quality)
                icon_size = min(18, rect.bottom() - badge.bottom() - metrics.height() - 6)
            if icon_size > 0:
                icon_rect = QRect(rect.center().x() - icon_size // 2, badge.bottom() + 1,
                                  icon_size, icon_size)
                item_icon(item_entry(item)).paint(painter, icon_rect)
            name = metrics.elidedText(item_name(item), Qt.TextElideMode.ElideRight, caption.width())
            painter.drawText(caption, Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter, name)
        elif selected:
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "+")
        painter.restore()


class SlotGrid(QTableView):
    inspect = Signal()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.inspect.emit()
            return
        super().keyPressEvent(event)


class NumberEdit(QAbstractSpinBox):
    """Keep exact entered text, including invalid or unusual saved values."""

    def __init__(self, step):
        super().__init__()
        self.step = Decimal(step)
        self.setMinimumWidth(115)

    def stepEnabled(self):
        if self.isReadOnly():
            return self.StepEnabledFlag.StepNone
        return self.StepEnabledFlag.StepUpEnabled | self.StepEnabledFlag.StepDownEnabled

    def stepBy(self, steps):
        try:
            value = Decimal(self.text())
            if value.is_finite() and value.adjusted() < 12:
                self.lineEdit().setText(format(value + self.step * steps, "f"))
        except InvalidOperation:
            pass

    def paintEvent(self, event):
        super().paintEvent(event)
        if not theme_active(self):
            return
        option = QStyleOptionSpinBox()
        self.initStyleOption(option)
        with QPainter(self) as painter:
            painter.setPen(QPen(QColor("#e3bb79" if self.isEnabled() else "#aaa194"), 1))
            for control, offset in ((QStyle.SubControl.SC_SpinBoxUp, -2),
                                    (QStyle.SubControl.SC_SpinBoxDown, 2)):
                rect = self.style().subControlRect(QStyle.ComplexControl.CC_SpinBox, option, control, self)
                point = rect.center()
                painter.drawLine(point.x() - 3, point.y() - offset, point.x(), point.y() + offset)
                painter.drawLine(point.x(), point.y() + offset, point.x() + 3, point.y() - offset)


class ItemFields(QWidget):
    changed = Signal()

    def __init__(self):
        super().__init__()
        form = QFormLayout(self)
        form.setContentsMargins(0, 0, 0, 0)
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        self.editors = {}
        for key, title, step in (
            ("quality", "Quality", "1"), ("stack", "Quantity", "1"),
            ("durability_raw", "Durability", "0.01"),
        ):
            field = NumberEdit(step)
            field.setAccessibleName(title)
            field.lineEdit().textChanged.connect(self.changed)
            self.editors[key] = field
            form.addRow(title, field)
        self.equipped = QCheckBox("Equipped")
        self.equipped.toggled.connect(self.changed)
        form.addRow(self.equipped)
        self.original = {}
        self.updating = False

    def populate(self, item=None, draft=None, editable=True):
        self.updating = True
        self.original = {
            "quality": str(item.quality) if item else "1",
            "stack": str(item.stack) if item else "1",
            "durability_raw": durability_text(item.durability_raw) if item else "100.00",
            "equipped": item.equipped if item else False,
        }
        values = self.original | (draft or {})
        for key, field in self.editors.items():
            field.lineEdit().setText(values[key])
            set_invalid(field, False)
        self.equipped.setChecked(values["equipped"])
        self.setEnabled(editable)
        self.updating = False

    def draft(self):
        values = {key: field.text() for key, field in self.editors.items()}
        values["equipped"] = self.equipped.isChecked()
        return {key: value for key, value in values.items() if value != self.original[key]}

    def values(self, maximum):
        draft = self.draft()
        result = {}
        for key, field in self.editors.items():
            set_invalid(field, False)
            if key not in draft:
                continue
            raw = field.text().strip()
            if key == "durability_raw":
                valid = bool(re.fullmatch(r"[0-9]{1,8}(?:\.[0-9]{1,2})?", raw))
                value = int(Decimal(raw) * 100) if valid else -1
                limit = 2**31 - 1
                valid = 0 <= value <= limit
                error = "Enter durability from 0 to 21,474,836.47 with up to two decimal places."
            else:
                value = int(raw) if re.fullmatch(r"[0-9]{1,5}", raw) else 0
                limit = min(maximum, 65535) if key == "stack" else 65535
                valid = 1 <= value <= limit
                error = f"{field.accessibleName()} must be a whole number from 1 to {limit:,}."
            if not valid:
                set_invalid(field, True)
                field.setFocus()
                raise FormatError(error)
            original = Decimal(self.original[key])
            if value != (original * 100 if key == "durability_raw" else original):
                result[key] = value
        if "equipped" in draft:
            result["equipped"] = draft["equipped"]
        return result


class CatalogDialog(QDialog):
    def __init__(self, parent, session, position):
        super().__init__(parent)
        self.session = session
        self.setWindowTitle("Add Item")
        self.resize(690, 580)
        self.entry = None
        layout = QVBoxLayout(self)
        layout.addWidget(heading("Add Item"))
        layout.addWidget(label(CATALOG_VERSION, "muted", wrap=True))
        search_row = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setAccessibleName("Search item catalog")
        self.search.setPlaceholderText("Search item name or prefab")
        self.category = QComboBox()
        self.category.setAccessibleName("Item category")
        self.category.addItem("All categories", None)
        for category in sorted({entry.category for entry in ENTRIES}):
            self.category.addItem(category, category)
        search_row.addWidget(self.search, 1)
        search_row.addWidget(self.category)
        layout.addLayout(search_row)
        self.results = QListWidget()
        self.results.setAccessibleName("Matching catalog items")
        self.results.setIconSize(QSize(30, 30))
        layout.addWidget(self.results, 1)
        self.details = label(role="muted", wrap=True)
        layout.addWidget(self.details)
        self.slot = QComboBox()
        self.slot.setAccessibleName("Destination slot")
        free_slots = session.free_slots()
        for free in free_slots:
            self.slot.addItem(slot_name(free), free)
        if position in free_slots:
            self.slot.setCurrentIndex(free_slots.index(position))
        form = QFormLayout()
        form.addRow("Destination", self.slot)
        layout.addLayout(form)
        self.fields = ItemFields()
        self.fields.populate()
        layout.addWidget(self.fields)
        self.error = label(role="error", wrap=True)
        self.warning = label(role="warning", wrap=True)
        layout.addWidget(self.error)
        layout.addWidget(self.warning)
        buttons = QHBoxLayout()
        self.add = primary_button("Add to Inventory")
        self.add.setAutoDefault(False)
        cancel = QPushButton("Cancel")
        cancel.setAutoDefault(False)
        buttons.addStretch(1)
        buttons.addWidget(cancel)
        buttons.addWidget(self.add)
        layout.addLayout(buttons)
        self.search.textChanged.connect(self.filter)
        self.category.currentIndexChanged.connect(self.filter)
        self.results.currentItemChanged.connect(self.choose)
        self.search.returnPressed.connect(self.focus_results)
        self.add.clicked.connect(self.create)
        cancel.clicked.connect(self.reject)
        self.fields.changed.connect(self.update_warning)
        self.filter()
        self.search.setFocus()

    def focus_results(self):
        if self.results.count():
            self.results.setCurrentRow(0)
            self.results.setFocus()

    def filter(self):
        self.results.clear()
        for entry in search_catalog(self.search.text(), self.category.currentData()):
            stack = entry.maximum_stack if entry.maximum_stack is not None else "unverified"
            quality = entry.maximum_quality if entry.maximum_quality is not None else "unknown"
            item = QListWidgetItem(item_icon(entry),
                                   f"{entry.name}  ·  {entry.prefab}\n{entry.category}  ·  Max stack {stack}  ·  Max quality {quality}")
            item.setData(CELL, entry)
            self.results.addItem(item)
        self.choose(None)

    def choose(self, item, previous=None):
        self.entry = item.data(CELL) if item else None
        if self.entry:
            self.details.setText(f"Stack and quality source: {self.entry.source}")
        else:
            self.details.setText("Select a catalog item." if self.results.count() else "No matching catalog items.")
        eligible = bool(self.entry and self.entry.maximum_stack and self.slot.count())
        self.fields.populate(editable=eligible)
        self.add.setEnabled(eligible)
        if not self.slot.count():
            self.error.setText("The writable inventory rows have no free slots.")
        elif self.entry and not self.entry.maximum_stack:
            self.error.setText("Creation requires a verified maximum stack size.")
        else:
            self.error.clear()
        self.update_warning()

    def update_warning(self):
        self.warning.setText(quality_warning(self.fields, self.entry))

    def create(self):
        entry = self.entry
        position = self.slot.currentData()
        if not entry or not entry.maximum_stack or position is None:
            return
        try:
            values = self.fields.values(entry.maximum_stack)
            stack = values.pop("stack", 1)
            quality = values.pop("quality", 1)
            self.session.add_item(entry.prefab, position, stack, quality, values)
        except FormatError as error:
            self.error.setText(str(error))
        else:
            self.accept()


def quality_warning(fields, entry):
    if not entry:
        return ""
    text = fields.draft().get("quality", "").strip()
    if not re.fullmatch(r"[0-9]{1,5}", text) or not 1 <= int(text) <= 65535:
        return ""
    maximum = entry.maximum_quality
    if maximum is None:
        return "Vanilla quality maximum unavailable. Gameplay may differ."
    if int(text) > maximum:
        return f"Quality exceeds the vanilla maximum ({maximum}). Gameplay may differ."
    return ""


class InventoryPage(QWidget):
    changed = Signal()
    drafts_changed = Signal()

    def __init__(self):
        super().__init__()
        self.session = None
        self.key = None
        self.compact = False
        self.inspecting = False
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.grid_panel = panel()
        grid_layout = QVBoxLayout(self.grid_panel)
        header = QHBoxLayout()
        title = QVBoxLayout()
        title.addWidget(heading("Inventory"))
        self.count = label(role="muted")
        title.addWidget(self.count)
        header.addLayout(title, 1)
        self.inspect_button = QPushButton("Inspect Slot")
        self.add_button = primary_button("Add Item")
        self.repair_all_button = QPushButton("Repair All…")
        header.addWidget(self.inspect_button)
        header.addWidget(self.repair_all_button)
        header.addWidget(self.add_button)
        grid_layout.addLayout(header)
        self.model = InventoryModel(self)
        self.grid = SlotGrid()
        self.grid.setAccessibleName("Inventory slots, eight columns")
        self.grid.setModel(self.model)
        self.grid.setItemDelegate(SlotDelegate(self.grid))
        self.grid.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.grid.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.grid.setShowGrid(False)
        self.grid.setCornerButtonEnabled(False)
        self.grid.horizontalHeader().hide()
        self.grid.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.grid.horizontalHeader().setMinimumSectionSize(50)
        self.grid.verticalHeader().hide()
        self.grid.verticalHeader().setDefaultSectionSize(67)
        self.grid.setMinimumWidth(422)
        grid_layout.addWidget(self.grid, 1)
        self.diagnostics_title = label(role="warning", wrap=True)
        self.diagnostics = QListWidget()
        self.diagnostics.setAccessibleName("Inventory diagnostics")
        self.diagnostics.setMaximumHeight(105)
        grid_layout.addWidget(self.diagnostics_title)
        grid_layout.addWidget(self.diagnostics)
        layout.addWidget(self.grid_panel, 2)

        inspector = panel()
        inspector_layout = QVBoxLayout(inspector)
        self.back = QPushButton("Back to Inventory")
        inspector_layout.addWidget(self.back)
        self.position_label = label(role="muted", wrap=True)
        inspector_layout.addWidget(self.position_label)
        item_header = QHBoxLayout()
        self.icon = label()
        self.name = heading("Select a slot")
        self.name.setWordWrap(True)
        item_header.addWidget(self.icon)
        item_header.addWidget(self.name, 1)
        inspector_layout.addLayout(item_header)
        self.metadata = label(role="muted", wrap=True)
        inspector_layout.addWidget(self.metadata)
        self.source_button = QPushButton("Advanced Item Details")
        self.source_button.clicked.connect(self.show_source)
        inspector_layout.addWidget(self.source_button, alignment=Qt.AlignmentFlag.AlignLeft)
        self.fields = ItemFields()
        self.fields.populate()
        inspector_layout.addWidget(self.fields)
        self.stat_summary = label(role="muted", wrap=True)
        self.stat_summary.setAccessibleName("Calculated item statistics")
        inspector_layout.addWidget(self.stat_summary)
        self.durability_meter = QProgressBar()
        self.durability_meter.setRange(0, 1000)
        self.durability_meter.setTextVisible(False)
        self.durability_meter.setAccessibleName("Durability percentage")
        self.durability_meter.setMaximumHeight(10)
        inspector_layout.addWidget(self.durability_meter)
        self.repair_button = QPushButton("Repair")
        inspector_layout.addWidget(self.repair_button, alignment=Qt.AlignmentFlag.AlignLeft)
        self.warning = label(role="warning", wrap=True)
        self.error = label(role="error", wrap=True)
        self.error.setAccessibleName("Item validation error")
        inspector_layout.addWidget(self.warning)
        inspector_layout.addWidget(self.error)
        self.apply_button = primary_button("Apply Item")
        self.revert_button = QPushButton("Revert Draft")
        actions = QHBoxLayout()
        actions.addWidget(self.apply_button)
        actions.addWidget(self.revert_button)
        inspector_layout.addLayout(actions)
        self.remove_button = QPushButton("Remove Item…")
        self.remove_button.setProperty("destructive", True)
        inspector_layout.addWidget(self.remove_button)
        self.add_here = primary_button("Add Item Here")
        inspector_layout.addWidget(self.add_here)
        inspector_layout.addStretch(1)
        self.inspector = scroll_area(inspector)
        self.inspector.setMinimumWidth(280)
        layout.addWidget(self.inspector, 1)

        self.grid.selectionModel().currentChanged.connect(self.select_slot)
        self.grid.clicked.connect(self.select_slot)
        self.grid.inspect.connect(self.open_inspector)
        self.grid.doubleClicked.connect(self.open_inspector)
        self.inspect_button.clicked.connect(self.open_inspector)
        self.back.clicked.connect(self.return_to_grid)
        self.diagnostics.currentItemChanged.connect(self.inspect_diagnostic)
        self.diagnostics.itemActivated.connect(self.open_inspector)
        self.add_button.clicked.connect(self.open_catalog)
        self.add_here.clicked.connect(self.open_catalog)
        self.fields.changed.connect(self.update_draft)
        self.apply_button.clicked.connect(self.apply_item)
        self.revert_button.clicked.connect(self.revert_item)
        self.remove_button.clicked.connect(self.remove_item)
        self.repair_button.clicked.connect(self.repair_selected)
        self.repair_all_button.clicked.connect(self.repair_all)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.compact = event.size().width() < 850
        self.update_panes()

    def update_panes(self):
        self.back.setVisible(self.compact)
        self.inspect_button.setVisible(self.compact)
        self.grid_panel.setVisible(not self.compact or not self.inspecting)
        self.inspector.setVisible(not self.compact or self.inspecting)

    def open_inspector(self, *_):
        self.inspecting = True
        self.update_panes()
        (self.fields.editors["quality"] if self.fields.isEnabled() else
         self.back if self.compact else self.grid).setFocus()

    def return_to_grid(self):
        self.inspecting = False
        self.update_panes()
        self.grid.setFocus()

    def set_session(self, session):
        if session is not self.session:
            self.session = session
            self.inspecting = False
            self.grid.clearSelection()
            self.grid.setCurrentIndex(QModelIndex())
        self.refresh()

    def refresh(self, position=None):
        index = self.grid.currentIndex()
        if position is None:
            position = (index.column(), index.row()) if index.isValid() else (0, 0)
        items = self.session.items if self.session else {}
        self.model.set_items(items)
        self.count.setText(f"{len(items)} items · {self.model.height * 8} displayed slots")
        self.diagnostics.clear()
        for pos, records in self.model.positions.items():
            if pos[0] >= 8 or len(records) > 1:
                for key, item in records:
                    reason = "Invalid column" if pos[0] >= 8 else "Duplicate slot"
                    row = QListWidgetItem(f"{reason} · {item_name(item)} · {slot_name(pos)}")
                    row.setData(CELL, key)
                    self.diagnostics.addItem(row)
        self.diagnostics_title.setText("Inventory diagnostics · Records are preserved")
        for widget in (self.diagnostics_title, self.diagnostics):
            widget.setVisible(bool(self.diagnostics.count()))
        self.add_button.setEnabled(bool(self.session and self.session.free_slots()))
        self.repair_all_button.setEnabled(bool(items))
        x, y = position
        index = self.model.index(min(y, self.model.height - 1), x)
        self.grid.setCurrentIndex(index)
        self.select_slot(index)
        self.update_panes()

    def select_slot(self, index, previous=None):
        if not index.isValid():
            return
        self.diagnostics.clearSelection()
        records = index.data(CELL)
        position = (index.column(), index.row())
        self.show_record(records[0][0] if len(records) == 1 else None, position, len(records) > 1)

    def inspect_diagnostic(self, current, previous=None):
        if current:
            key = current.data(CELL)
            item = self.session.items[key]
            self.show_record(key, (item.x, item.y), True)

    def show_source(self):
        item = self.session.items[self.key]
        prefab = self.entry.prefab if self.entry else "Unknown prefab"
        source = self.entry.source if self.entry else "No verified identity or catalog metadata"
        stats = SNAPSHOT["items"].get(prefab)
        evidence = (f"Valheim {GAME_VERSION}, build {SNAPSHOT['steam_build']}\n"
                    f"{SNAPSHOT['verification']}\nBundle SHA-256: {SNAPSHOT['sha256']}"
                    if stats else "Statistics have not been verified for this prefab.")
        dialog = QMessageBox(QMessageBox.Icon.Information, "Advanced Item Details",
                             f"Prefab: {prefab}\nHash: {item.prefab_hash}\n"
                             f"Serialized durability: {item.durability_raw} hundredths\n\n"
                             f"{CATALOG_VERSION}\n{source}\n\nStatistics: {evidence}",
                             QMessageBox.StandardButton.Ok, self)
        dialog.setTextFormat(Qt.TextFormat.PlainText)
        dialog.exec()

    def show_record(self, key, position, conflict=False):
        self.key, self.position = key, position
        item = self.session.items[key] if self.session and key is not None else None
        entry = item_entry(item) if item else None
        editable = bool(entry and entry.maximum_stack and not conflict)
        writable_rows = self.session.working.writable_inventory_rows if self.session else 0
        flag_text = ""
        if item:
            cheated = self.session.working.item_cheat_status(item)
            flag_text = ("Legacy item flag byte preserved" if cheated is None else
                         f"Saved cheated flag: {'set' if cheated else 'clear'}")
        self.entry = entry
        self.source_button.setVisible(item is not None)
        self.position_label.setText(slot_name(position))
        self.name.setText(item_name(item) if item else "Conflicting slot" if conflict else "Empty slot")
        self.icon.setPixmap(item_icon(entry).pixmap(42, 42) if item else item_icon(None).pixmap(0, 0))
        self.icon.setVisible(item is not None)
        if entry:
            stack_text = str(entry.maximum_stack) if entry.maximum_stack is not None else "unavailable (missing catalog metadata)"
            meta = (f"{entry.category}\nVerified stack maximum: {stack_text}\n"
                    f"Vanilla quality maximum: {entry.maximum_quality if entry.maximum_quality is not None else 'unavailable'}\n"
                    f"{flag_text}")
            self.metadata.setToolTip(f"{CATALOG_VERSION}\n{entry.source}")
        elif item:
            meta = (f"Unknown prefab · Hash {item.prefab_hash}. This record is preserved.\n"
                    f"{flag_text}")
            self.metadata.setToolTip("")
        elif conflict:
            meta = "Open Inventory diagnostics to inspect each record."
        else:
            if position[1] < writable_rows:
                meta = "Choose an item from the offline catalog."
            elif writable_rows:
                meta = f"Item creation is available in rows 1–{writable_rows}."
            else:
                meta = "This save has no verified writable inventory rows."
        self.metadata.setText(meta)
        self.fields.setVisible(item is not None)
        draft = self.session.item_drafts.get(key) if self.session else None
        self.fields.populate(item, draft, editable)
        self.error.clear()
        self.warning.setText(quality_warning(self.fields, entry))
        if conflict and item:
            self.warning.setText("This saved position is read-only." if position[0] >= 8 else
                                 "This saved position is read-only. Duplicate slots prevent export.")
        elif editable and not 1 <= item.stack <= min(entry.maximum_stack, 65535):
            self.warning.setText("The saved stack is outside its verified limit. Correct it explicitly before export.")
        self.remove_button.setVisible(editable)
        self.apply_button.setVisible(editable)
        self.revert_button.setVisible(editable)
        self.apply_button.setEnabled(bool(draft))
        self.revert_button.setEnabled(bool(draft))
        self.add_here.setVisible(bool(self.session and not item and not conflict and position[1] < writable_rows))
        self.refresh_statistics()

    def refresh_statistics(self):
        item = self.session.items.get(self.key) if self.session else None
        self.stat_summary.setVisible(item is not None)
        self.repair_button.setVisible(item is not None)
        self.durability_meter.hide()
        if item is None:
            return
        draft = self.fields.draft()
        quality_text = self.fields.editors["quality"].text().strip()
        quality = int(quality_text) if re.fullmatch(r"[0-9]{1,5}", quality_text) else 0
        stats = calculate_item_stats(item, quality)
        stored = durability_text(item.durability_raw)
        lines = [f"Valheim {GAME_VERSION} · {'Draft quality' if 'quality' in draft else 'Calculated stats'}"]
        if stats is None or stats.maximum_durability is None:
            lines.append(f"Durability (current / max): {stored} / unavailable")
            if stats is not None:
                lines.append("This prefab does not use a verified positive durability maximum.")
        else:
            maximum = stats.maximum_durability
            fraction = stats.durability_fraction(item.durability_raw)
            lines.append(f"Durability (current / max): {stored} / {maximum:.2f} · {fraction:.1%}")
            if item.durability_raw / 100 > maximum:
                lines.append("Stored durability exceeds the calculated maximum.")
            self.durability_meter.setValue(round(fraction * 1000))
            self.durability_meter.setAccessibleDescription(f"{fraction:.1%}")
            self.durability_meter.show()
        category = self.entry.category if self.entry else None
        if stats is None:
            lines.append("Unknown prefab: identity must be verified before statistics can be calculated."
                         if self.entry is None else
                         "Missing item statistics or unsupported quality: maximum durability is unavailable.")
        elif category in ("Weapon", "Armor", "Shield", "Tool", "Ammo"):
            if category == "Armor":
                lines.append(f"Armor: {stats.armor:g}" if stats.armor is not None else "Armor unavailable at this world level.")
            if category in ("Weapon", "Tool", "Ammo"):
                if stats.damage is None:
                    lines.append("Damage unavailable at this world level.")
                elif stats.damage:
                    values = " · ".join(f"{channel.title()} {value:g}" for channel, value in stats.damage.items())
                    lines.append(f"Item damage: {values}")
            if category in ("Weapon", "Shield", "Tool"):
                lines.append(f"Base block {stats.block:g} · Deflection {stats.deflection:g}")
                lines.append(f"Parry ×{stats.parry:g}" if stats.parry > 1 else "No timed parry bonus")
            lines.append(f"Movement {stats.movement:+.1%}")
        plan = self.session.repair_plan((self.key,))
        if plan.skipped:
            reason = plan.skipped[0][1]
            self.repair_button.setToolTip(reason)
            self.repair_button.setAccessibleDescription(reason)
            lines.append(reason)
        else:
            self.repair_button.setToolTip("Stage a durability-only change.")
            self.repair_button.setAccessibleDescription("Stage a durability-only change.")
        self.repair_button.setEnabled(bool(plan.changes))
        self.stat_summary.setText("\n".join(lines))

    def update_draft(self):
        if self.fields.updating or self.key is None or not self.fields.isEnabled():
            return
        draft = self.fields.draft()
        if draft:
            self.session.item_drafts[self.key] = draft
        else:
            self.session.item_drafts.pop(self.key, None)
        self.apply_button.setEnabled(bool(draft))
        self.revert_button.setEnabled(bool(draft))
        self.warning.setText(quality_warning(self.fields, self.entry))
        self.error.clear()
        for field in self.fields.editors.values():
            set_invalid(field, False)
        self.refresh_statistics()
        self.drafts_changed.emit()

    def repair_selected(self):
        self.apply_repair_plan(self.session.repair_plan((self.key,)))

    def repair_all(self):
        session = self.session
        plan = session.repair_plan()
        if self.confirm_repairs(plan) and self.session is session:
            self.apply_repair_plan(plan)

    def confirm_repairs(self, plan):
        dialog = QDialog(self)
        dialog.setWindowTitle("Repair All Preview")
        dialog.resize(620, 430)
        layout = QVBoxLayout(dialog)
        layout.addWidget(label(f"{len(plan.changes)} eligible · {len(plan.skipped)} skipped", wrap=True))
        preview = QPlainTextEdit()
        preview.setAccessibleName("Repair changes and skipped items")
        preview.setReadOnly(True)
        lines = []
        for key, before, after in plan.changes:
            item = self.session.items[key]
            lines.append(f"{item_name(item)} · {slot_name((item.x, item.y))} · "
                         f"{durability_text(before)} → {durability_text(after)}")
        for key, reason in plan.skipped:
            item = self.session.items[key]
            lines.append(f"Skipped {item_name(item)} · {slot_name((item.x, item.y))} · {reason}")
        preview.setPlainText("\n".join(lines))
        layout.addWidget(preview)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        apply_button = buttons.addButton("Stage Repairs", QDialogButtonBox.ButtonRole.AcceptRole)
        apply_button.setEnabled(bool(plan.changes))
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        accepted = dialog.exec() == QDialog.DialogCode.Accepted
        dialog.deleteLater()
        return accepted

    def apply_repair_plan(self, plan):
        if not plan.changes:
            return
        try:
            self.session.apply_repairs(plan)
        except FormatError as error:
            self.error.setText(str(error))
        else:
            self.refresh(self.position)
            self.changed.emit()

    def apply_item(self):
        try:
            self.session.edit_item(self.key, self.fields.values(self.entry.maximum_stack))
        except FormatError as error:
            self.error.setText(str(error))
        else:
            self.refresh(self.position)
            self.changed.emit()

    def revert_item(self):
        self.session.item_drafts.pop(self.key, None)
        self.show_record(self.key, self.position)
        self.drafts_changed.emit()

    def remove_item(self):
        item = self.session.items[self.key]
        answer = QMessageBox.question(self, "Remove Item",
                                      f"Stage removal of {item_name(item)} from {slot_name(self.position)}?",
                                      QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                                      QMessageBox.StandardButton.Cancel)
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.session.remove_item(self.key)
        except FormatError as error:
            self.error.setText(str(error))
        else:
            self.refresh(self.position)
            self.changed.emit()

    def open_catalog(self):
        dialog = CatalogDialog(self, self.session, self.position)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh(dialog.slot.currentData())
            self.changed.emit()
        dialog.deleteLater()
