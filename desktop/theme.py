"""Original ULF styling and locally drawn item silhouettes."""

from functools import lru_cache

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase, QIcon, QPainter, QPen, QPixmap, QPolygonF
from PySide6.QtWidgets import QApplication, QFrame, QLabel, QPushButton, QScrollArea


STYLE = """
QWidget { color: #f2e9da; }
QMainWindow, QDialog, QScrollArea, QWidget#canvas { background: #151617; }
QFrame#panel { background: #222426; border: 1px solid #514940; border-radius: 8px; }
QFrame#band { background: #1c1d1e; border-bottom: 1px solid #514940; }
QLabel#muted { color: #bdb5a9; }
QLabel#warning { color: #f0c583; }
QLabel#error { color: #ffbaa9; }
QLabel#verified { color: #b5d3b3; }
QLabel#brand { color: #e3bb79; font-weight: bold; }
QLabel#section { font-weight: bold; }
QPushButton, QToolButton {
    background: #302e2b; border: 1px solid #89796c; border-radius: 5px; padding: 6px 12px;
}
QPushButton:hover, QToolButton:hover { background: #443a2f; }
QPushButton[primary="true"] { background: #e3bb79; color: #251b10; font-weight: bold; }
QPushButton[primary="true"]:hover { background: #f0cf99; }
QPushButton[destructive="true"] { color: #ffbaa9; }
QLineEdit, QAbstractSpinBox, QComboBox, QListWidget, QTableView {
    background: #18191a; border: 1px solid #89796c; border-radius: 5px;
}
QLineEdit, QAbstractSpinBox, QComboBox { padding: 5px 8px; selection-background-color: #785735; }
QAbstractSpinBox::up-button, QAbstractSpinBox::down-button {
    width: 18px; background: #302e2b; border-left: 1px solid #89796c;
}
QAbstractSpinBox::up-arrow, QAbstractSpinBox::down-arrow { width: 0; height: 0; }
QLineEdit[invalid="true"], QAbstractSpinBox[invalid="true"] { border: 2px solid #ffbaa9; }
QPushButton:focus, QToolButton:focus, QLineEdit:focus, QAbstractSpinBox:focus, QComboBox:focus,
QListWidget:focus, QSlider:focus, QCheckBox:focus {
    border: 2px solid #faf2de;
}
QWidget:disabled { color: #aaa194; }
QPushButton:disabled { background: #292929; border-color: #58534b; color: #aaa194; }
QListWidget::item { padding: 5px; }
QListWidget::item:selected { background: #59412a; color: #fff1d9; }
QTabWidget::pane { border: 0; }
QTabBar::tab { background: #1c1d1e; color: #d1c7b9; padding: 9px 16px; border-bottom: 2px solid transparent; }
QTabBar::tab:selected { color: #f0c583; border-bottom: 2px solid #e3bb79; }
QTabBar::tab:focus { border: 2px solid #faf2de; }
QSlider { border: 2px solid transparent; min-height: 26px; }
QSlider::groove:horizontal { height: 5px; background: #827367; border-radius: 2px; }
QSlider::sub-page:horizontal { background: #c6985e; }
QSlider::handle:horizontal { background: #f0cf99; width: 16px; margin: -5px 0; border-radius: 8px; }
QScrollBar:vertical { background: #191a1b; width: 14px; margin: 0; }
QScrollBar::handle:vertical { background: #89796c; border: 3px solid #191a1b; min-height: 24px; border-radius: 5px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
"""


def apply_theme(widget):
    palette = QApplication.palette()
    if palette.color(palette.ColorRole.Window).lightness() < 32 and palette.color(
        palette.ColorRole.WindowText
    ).lightness() > 245:
        return
    widget.setStyleSheet(STYLE)


def theme_active(widget):
    while widget is not None:
        if widget.styleSheet() == STYLE:
            return True
        widget = widget.parentWidget()
    return False


def label(text="", role="", *, wrap=False):
    result = QLabel(text)
    result.setTextFormat(Qt.TextFormat.PlainText)
    result.setWordWrap(wrap)
    result.setObjectName(role)
    return result


def heading(text, scale=1.4, serif=False):
    result = label(text, "section")
    font = result.font()
    font.setPointSizeF(max(8, font.pointSizeF()) * scale)
    if serif:
        font.setStyleHint(QFont.StyleHint.Serif)
        font.setFamilies(["Georgia", "Noto Serif", "DejaVu Serif", "Liberation Serif",
                          QFontDatabase.systemFont(QFontDatabase.SystemFont.GeneralFont).family()])
    result.setFont(font)
    return result


def panel():
    result = QFrame()
    result.setObjectName("panel")
    return result


def primary_button(text):
    button = QPushButton(text)
    button.setProperty("primary", True)
    return button


def scroll_area(content):
    result = QScrollArea()
    if not content.objectName():
        content.setObjectName("canvas")
    result.setFrameShape(QFrame.Shape.NoFrame)
    result.setWidgetResizable(True)
    result.setWidget(content)
    return result


def set_invalid(field, invalid):
    field.setProperty("invalid", invalid)
    field.style().unpolish(field)
    field.style().polish(field)


SPECIFIC_ICONS = {
    "Wood": "wood", "FineWood": "wood", "RoundLog": "wood", "Stone": "stone",
    "Flint": "stone", "AxeBronze": "axe", "SwordIron": "sword",
    "ShieldWood": "shield", "BowFineWood": "bow",
}
CATEGORY_ICONS = {
    "Weapon": "sword", "Armor": "helm", "Food": "food", "Material": "stone",
    "Tool": "axe", "Trophy": "trophy", "Ammo": "arrow", "Shield": "shield",
}


def item_icon(entry):
    if entry is None:
        return artwork("unknown")
    return artwork(SPECIFIC_ICONS.get(entry.prefab, CATEGORY_ICONS.get(entry.category, "pack")))


@lru_cache(maxsize=20)
def artwork(kind):
    pixmap = QPixmap(96, 96)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.scale(3, 3)
    painter.setPen(Qt.PenStyle.NoPen)

    def poly(color, *points):
        painter.setBrush(QColor(color))
        painter.drawPolygon(QPolygonF([QPointF(x, y) for x, y in points]))

    def oval(color, x, y, w, h):
        painter.setBrush(QColor(color))
        painter.drawEllipse(QRectF(x, y, w, h))

    gold, bronze, ivory, shadow = "#e3bb79", "#ad7d4e", "#ddd1b8", "#66513e"
    if kind == "wolf":
        poly(gold, (2, 2), (11, 8), (21, 8), (30, 2), (28, 18), (22, 25),
             (16, 31), (10, 25), (4, 18))
        poly("#1c1d1e", (6, 13), (13, 16), (10, 18))
        poly("#1c1d1e", (26, 13), (19, 16), (22, 18))
        poly("#1c1d1e", (12, 23), (20, 23), (16, 27))
    elif kind in ("axe", "sword", "arrow"):
        poly(bronze, (4, 27), (7, 30), (23, 11), (20, 8))
        if kind == "axe":
            poly(gold, (14, 8), (28, 3), (30, 16), (19, 17))
            poly(bronze, (26, 4), (28, 3), (30, 16), (27, 16))
        else:
            poly(ivory, (10, 20), (25, 4), (30, 2), (28, 9), (14, 23))
            poly(gold, (7, 16), (18, 25), (16, 28), (5, 19))
    elif kind == "bow":
        painter.setPen(QPen(QColor(ivory), 1))
        painter.drawLine(QPointF(8, 3), QPointF(8, 29))
        painter.setPen(QPen(QColor(gold), 3))
        painter.drawArc(QRectF(-4, 3, 26, 26), -90 * 16, 180 * 16)
    elif kind == "shield":
        oval(bronze, 3, 3, 26, 26)
        oval(shadow, 6, 6, 20, 20)
        oval(gold, 12, 12, 8, 8)
    elif kind == "helm":
        poly(ivory, (3, 24), (4, 13), (10, 5), (16, 2), (22, 5), (28, 13),
             (29, 24), (21, 28), (19, 18), (13, 18), (11, 28))
        poly(bronze, (5, 13), (27, 13), (27, 16), (5, 16))
    elif kind == "wood":
        poly(bronze, (3, 15), (23, 5), (30, 16), (10, 27))
        oval(gold, 3, 15, 11, 12)
        oval(shadow, 6, 18, 5, 6)
    elif kind == "stone":
        poly(ivory, (2, 16), (12, 6), (24, 7), (30, 17), (24, 26), (7, 26))
        poly("#a49a88", (2, 16), (16, 16), (24, 7), (30, 17), (24, 26), (7, 26))
    elif kind == "food":
        oval(bronze, 6, 9, 21, 20)
        oval(gold, 6, 9, 17, 17)
        poly("#adba87", (16, 11), (16, 5), (25, 2), (22, 8))
    elif kind == "trophy":
        poly(gold, (3, 4), (29, 4), (26, 14), (19, 20), (19, 25), (26, 27),
             (26, 30), (6, 30), (6, 27), (13, 25), (13, 20), (6, 14))
    elif kind == "pack":
        poly(bronze, (5, 11), (16, 5), (27, 11), (27, 23), (16, 29), (5, 23))
        poly(gold, (5, 11), (16, 5), (27, 11), (16, 17))
    else:
        painter.setPen(QColor(ivory))
        font = painter.font()
        font.setPixelSize(23)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(QRectF(0, 0, 32, 32), Qt.AlignmentFlag.AlignCenter, "?")
    painter.end()
    return QIcon(pixmap)
