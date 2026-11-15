"""Appearance drafts, explicit previews and normalized RGB controls."""
import math

from PySide6.QtCore import Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
                              QComboBox, QLineEdit, QPushButton, QColorDialog, QPlainTextEdit)

from core.appearance import CATALOG, FIELDS, propose, same
from core.fch import FormatError
from desktop.session import appearance_value, display_number
from desktop.theme import heading, label, scroll_area


class AppearancePage(QWidget):
    changed = Signal()
    drafts_changed = Signal()

    def __init__(self):
        super().__init__()
        self.session = None
        self.loading = False
        outer = QVBoxLayout(self)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.addWidget(heading("Character Appearance"))
        self.overview = label(wrap=True)
        layout.addWidget(self.overview)
        layout.addWidget(label("Name is read-only: renaming may affect future item-upgrade seeds.", "muted", wrap=True))
        self.model = QComboBox()
        self.model.setAccessibleName("Body model")
        self.model.currentIndexChanged.connect(self.edited)
        form = QFormLayout()
        form.addRow("Body model", self.model)
        self.styles, self.searches = {}, {}
        for field in ('hair', 'beard'):
            box = QWidget(); row = QVBoxLayout(box); row.setContentsMargins(0,0,0,0)
            search = QLineEdit(); search.setPlaceholderText(f"Search {field} name or identifier")
            search.setAccessibleName(f"Search {field} styles")
            combo = QComboBox(); combo.setAccessibleName(f"{field.title()} style")
            row.addWidget(search);row.addWidget(combo)
            self.styles[field], self.searches[field] = combo, search
            search.textChanged.connect(lambda text, f=field: self.filter_styles(f))
            combo.currentIndexChanged.connect(self.edited)
            form.addRow(field.title(), box)
        self.colors, self.swatches, self.color_buttons = {}, {}, {}
        for field in ('hair_color', 'skin_color'):
            box=QWidget(); rows=QVBoxLayout(box); rows.setContentsMargins(0,0,0,0)
            swatches=QHBoxLayout(); current=label(); proposed=label()
            current.setAccessibleName(field+' current swatch');proposed.setAccessibleName(field+' proposed swatch')
            swatches.addWidget(current);swatches.addWidget(proposed);rows.addLayout(swatches)
            channels=QHBoxLayout(); editors=[]
            for channel in 'RGB':
                editor=QLineEdit();editor.setAccessibleName(f"{field.replace('_',' ')} {channel}")
                editor.textChanged.connect(self.edited)
                channels.addWidget(label(channel));channels.addWidget(editor);editors.append(editor)
            rows.addLayout(channels)
            buttons=QHBoxLayout(); picker=QPushButton("Choose color…"); reset=QPushButton("Revert color")
            picker.clicked.connect(lambda checked=False,f=field:self.pick_color(f))
            reset.clicked.connect(lambda checked=False,f=field:self.revert_color(f))
            buttons.addWidget(picker);buttons.addWidget(reset);rows.addLayout(buttons)
            form.addRow(field.replace('_',' ').title(),box)
            self.colors[field],self.swatches[field]=editors,(current,proposed)
            self.color_buttons[field]=(picker,reset)
        layout.addLayout(form)
        layout.addWidget(label("RGB uses normalized float32 values (0–1). Swatches are approximate screen colors, "
                               "not a game render or vanilla tone-slider palette. Unknown saved values remain unchanged "
                               "until explicitly edited. Model 1 requires an explicit No Beard selection.","muted",wrap=True))
        self.error=label(role="error",wrap=True);layout.addWidget(self.error)
        self.preview=QPlainTextEdit();self.preview.setReadOnly(True)
        self.preview.setAccessibleName("Appearance change preview");self.preview.setMinimumHeight(100)
        layout.addWidget(self.preview)
        buttons=QHBoxLayout();self.apply_button=QPushButton("Apply Changes");self.revert_button=QPushButton("Revert Draft")
        self.apply_button.clicked.connect(self.apply);self.revert_button.clicked.connect(self.revert)
        buttons.addWidget(self.apply_button);buttons.addWidget(self.revert_button);layout.addLayout(buttons)
        outer.addWidget(scroll_area(content))

    def set_session(self, session):
        self.session=session
        self.refresh()

    def filter_styles(self, field):
        if not self.session:return
        combo=self.styles[field];selected=combo.currentData()
        if selected is None:selected=getattr(self.session.working.appearance,field)
        query=self.searches[field].text().casefold()
        blocked=combo.blockSignals(True);combo.clear()
        rows=CATALOG[field]
        keys=[selected]+[k for k,v in rows.items() if k!=selected and query in (k+' '+v['name']).casefold()]
        for key in keys:
            text=f"{rows[key]['name']} · {key}" if key in rows else f"Unknown preserved · {key or '(empty)'}"
            combo.addItem(text,key)
        combo.setCurrentIndex(0);combo.blockSignals(blocked)

    def refresh(self):
        if not self.session:return
        self.loading=True
        c=self.session.working;a=c.appearance;drafts=self.session.appearance_drafts
        self.overview.setText(f"{c.name} · Profile {c.profile_version} / Player {c.player_version}\n"+
                              "\n".join(f"Current {f.replace('_',' ')}: {appearance_value(getattr(a,f))}" for f in FIELDS))
        self.model.clear();self.model.addItem("Model 0 · Male",0);self.model.addItem("Model 1 · Female",1)
        target=drafts.get('model',a.model)
        if target not in (0,1):self.model.addItem(f"Unknown preserved model {target}",target)
        self.model.setCurrentIndex(self.model.findData(target))
        for field,combo in self.styles.items():
            combo.clear();combo.addItem('',drafts.get(field,getattr(a,field)));self.filter_styles(field)
        for field,editors in self.colors.items():
            texts=drafts.get(field,tuple(display_number(v) for v in getattr(a,field)))
            for editor,text in zip(editors,texts):editor.setText(text)
        self.loading=False
        self.update_preview()

    def raw_values(self):
        return dict(model=self.model.currentData(), **{f:c.currentData() for f,c in self.styles.items()},
                    **{f:tuple(e.text() for e in editors) for f,editors in self.colors.items()})

    def edited(self, *args):
        if self.loading or not self.session:return
        a=self.session.working.appearance
        self.session.appearance_drafts={f:v for f,v in self.raw_values().items()
            if v != (tuple(display_number(n) for n in getattr(a,f)) if f in self.colors else getattr(a,f))}
        self.update_preview();self.drafts_changed.emit()

    def proposal(self):
        changes={}
        for field,value in self.session.appearance_drafts.items():
            if field in self.colors:
                try:value=tuple(float(v) for v in value)
                except ValueError:raise FormatError("Enter numeric RGB values from 0 to 1.")
            changes[field]=value
        return changes,propose(self.session.working,changes)

    @staticmethod
    def swatch(widget, caption, values):
        valid=len(values)==3 and all(math.isfinite(v) and 0<=v<=1 for v in values)
        widget.setText(caption if valid else caption+" · outside preview range")
        if valid:
            color=QColor.fromRgbF(*values)
            foreground='#000000' if sum(values)>1.5 else '#ffffff'
            widget.setStyleSheet(f"background-color:{color.name()};color:{foreground};padding:8px;")
        else:widget.setStyleSheet('')

    def update_preview(self):
        a=self.session.working.appearance; proposed=a
        supported=(self.session.working.profile_version,self.session.working.player_version)==(47,34)
        self.apply_button.setEnabled(False);self.error.setText('')
        try:
            _,proposed=self.proposal()
            lines=[f"{f.replace('_',' ').title()}: {appearance_value(getattr(a,f))} → "
                   f"{appearance_value(getattr(proposed,f))}" for f in FIELDS if not same(getattr(a,f),getattr(proposed,f))]
            self.preview.setPlainText('\n'.join(lines) or 'No serialized appearance changes.')
            self.apply_button.setEnabled(bool(lines))
        except FormatError as error:
            self.error.setText(str(error));self.preview.setPlainText('Resolve the proposal before applying.')
        self.model.setEnabled(supported)
        for widget in (*self.styles.values(),*self.searches.values()):widget.setEnabled(supported)
        for field,editors in self.colors.items():
            for editor in editors:editor.setEnabled(supported)
            for button in self.color_buttons[field]:button.setEnabled(supported)
            self.swatch(self.swatches[field][0],'Current',getattr(a,field))
            self.swatch(self.swatches[field][1],'Proposed',getattr(proposed,field))
        self.revert_button.setEnabled(bool(self.session.appearance_drafts))

    def pick_color(self,field):
        if self.session.working.player_version!=34:return
        try:
            values=tuple(float(e.text()) for e in self.colors[field])
        except ValueError:
            values=getattr(self.session.working.appearance,field)
        if all(math.isfinite(v) and 0<=v<=1 for v in values):initial=QColor.fromRgbF(*values)
        else:initial=QColor('white')
        color=QColorDialog.getColor(initial,self,"Choose "+field.replace('_',' '))
        if color.isValid():
            self.loading=True
            for editor,value in zip(self.colors[field],(color.redF(),color.greenF(),color.blueF())):editor.setText(format(value,'.9g'))
            self.loading=False;self.edited()

    def revert_color(self,field):
        self.loading=True
        for editor,value in zip(self.colors[field],getattr(self.session.working.appearance,field)):editor.setText(display_number(value))
        self.loading=False;self.edited()

    def revert(self):
        self.session.appearance_drafts.clear();self.refresh();self.drafts_changed.emit()

    def apply(self):
        try:
            changes,_=self.proposal();self.session.apply_appearance_batch(changes)
        except FormatError as error:self.error.setText(str(error))
        else:self.refresh();self.changed.emit()
