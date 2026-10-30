import sys, json, copy, pathlib
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QTableWidget,QTableWidgetItem,QTabWidget,QFileDialog,QMessageBox,QSpinBox,QDoubleSpinBox,QLineEdit,QComboBox,QFormLayout,QGroupBox,QHeaderView,QAbstractItemView,QCheckBox)
from PySide6.QtCore import Qt
from core.fch import Character,FormatError,SKILLS,stable_hash

ROOT=pathlib.Path(__file__).resolve().parents[1]
CATALOG=json.loads((ROOT/'core/catalog.json').read_text())
HASHES={stable_hash(k):k for k in CATALOG}
STYLE='''
QWidget{background:#12171a;color:#e7dcc5;font-family:"Noto Sans", "Segoe UI",sans-serif;font-size:12px}
QMainWindow{background:#12171a}
QLabel#hero{font-family:serif;font-weight:bold;font-size:28px;color:#d9a65e}
QLabel#sub{color:#8d999e;font-size:12px}
QTabWidget::pane,QGroupBox{border:1px solid #554637;border-radius:7px;background:#1c2426}
QGroupBox{margin-top:13px;padding:12px;font-weight:bold;color:#d7ac6c}
QGroupBox::title{subcontrol-origin:margin;left:12px;padding:0 5px}
QTabBar::tab{background:#263033;color:#baaea1;padding:12px 25px;border:1px solid #344044}
QTabBar::tab:selected{background:#5a3d22;color:#ffe2a4}
QPushButton{background:#5d4227;color:#f7dfbc;border:1px solid #926d41;border-radius:5px;padding:8px 14px;font-weight:bold}
QPushButton:hover{background:#775331} QPushButton:disabled{color:#666;background:#303434}
QLineEdit,QSpinBox,QDoubleSpinBox,QComboBox{background:#101719;color:#f7e6ca;border:1px solid #596364;padding:7px;border-radius:4px}
QTableWidget{background:#1a2224;alternate-background-color:#20292b;gridline-color:#40413a;border:1px solid #554637;selection-background-color:#735027;selection-color:#fff}
QHeaderView::section{background:#302f2b;color:#eac78b;border:1px solid #504435;padding:7px}
'''
class Window(QMainWindow):
 def __init__(self):
  super().__init__();self.ch=None;self.path=None;self.selected=None
  self.setWindowTitle('ULF — Valheim Character Workshop · WolfWorks Labs');self.resize(1170,800)
  central=QWidget();self.setCentralWidget(central);outer=QVBoxLayout(central);outer.setSpacing(15)
  hero=QLabel('ᚢ  ULF  /  CHARACTER WORKSHOP');hero.setObjectName('hero');outer.addWidget(hero)
  self.subtitle=QLabel('WOLFWORKS LABS     •     LOCAL FCH EDITING     •     ORIGINAL SAVE PRESERVED');self.subtitle.setObjectName('sub');outer.addWidget(self.subtitle)
  toolbar=QHBoxLayout();outer.addLayout(toolbar)
  self.openbtn=QPushButton('Open .fch');self.openbtn.clicked.connect(self.open_file);toolbar.addWidget(self.openbtn)
  self.savebtn=QPushButton('Export edited .fch');self.savebtn.clicked.connect(self.export);toolbar.addWidget(self.savebtn)
  toolbar.addStretch();self.status=QLabel('No character loaded');toolbar.addWidget(self.status)
  tabs=QTabWidget();outer.addWidget(tabs)
  inv=QWidget();tabs.addTab(inv,'⚔  INVENTORY');invrow=QHBoxLayout(inv)
  left=QVBoxLayout();invrow.addLayout(left,4)
  self.table=QTableWidget(6,8);self.table.setSelectionMode(QAbstractItemView.SingleSelection);self.table.setEditTriggers(QAbstractItemView.NoEditTriggers);self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch);self.table.verticalHeader().setDefaultSectionSize(83)
  self.table.setHorizontalHeaderLabels([str(x+1) for x in range(8)]);self.table.setVerticalHeaderLabels([str(y+1) for y in range(6)]);self.table.cellClicked.connect(self.select_slot);left.addWidget(self.table)
  right=QVBoxLayout();invrow.addLayout(right,2)
  self.group=QGroupBox('SLOT EDITOR');form=QFormLayout(self.group);right.addWidget(self.group)
  self.slotlabel=QLabel('Select an inventory slot');form.addRow('Slot',self.slotlabel)
  self.search=QLineEdit();self.search.setPlaceholderText('Search or enter exact prefab…');self.search.textChanged.connect(self.filter_catalog);form.addRow('Item search',self.search)
  self.prefab=QComboBox();self.prefab.setEditable(True);form.addRow('Prefab',self.prefab);self.filter_catalog('')
  self.qty=QSpinBox();self.qty.setRange(1,65535);form.addRow('Quantity',self.qty)
  self.quality=QSpinBox();self.quality.setRange(1,65535);form.addRow('Quality',self.quality)
  self.durability=QDoubleSpinBox();self.durability.setRange(0,2000000);self.durability.setDecimals(2);form.addRow('Durability',self.durability)
  self.equipped=QCheckBox('Equipped');form.addRow('',self.equipped)
  self.apply=QPushButton('Apply to slot / Add item');self.apply.clicked.connect(self.apply_slot);right.addWidget(self.apply)
  remove=QPushButton('Remove selected item');remove.clicked.connect(self.remove_slot);right.addWidget(remove)
  right.addWidget(QLabel('Tip: Quality and quantity support values up to 65,535.\nUnusual values may not behave normally in-game.'))
  right.addStretch()
  skillpage=QWidget();tabs.addTab(skillpage,'ᛟ  SKILLS');sl=QVBoxLayout(skillpage)
  self.skilltable=QTableWidget(0,3);self.skilltable.setHorizontalHeaderLabels(['Skill','Level (0–100)','Progress / XP']);self.skilltable.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch);sl.addWidget(self.skilltable)
  bar=QHBoxLayout();sl.addLayout(bar);b=QPushButton('Apply skill changes');b.clicked.connect(self.apply_skills);bar.addWidget(b)
  b=QPushButton('Set all to 100');b.clicked.connect(self.max_skills);bar.addWidget(b);bar.addStretch()
  foot=QLabel('SAFETY  •  SHA-512 checked  •  Byte-exact no-change round trip required  •  Save As only  •  No cheat-flag scrubbing');foot.setObjectName('sub');outer.addWidget(foot)
  self.savebtn.setEnabled(False)
 def filter_catalog(self,term):
  current=self.prefab.currentText() if hasattr(self,'prefab') else ''
  self.prefab.blockSignals(True);self.prefab.clear()
  for prefab,data in sorted(CATALOG.items(),key=lambda x:x[1]['name']):
   if term.lower() in (prefab+' '+data['name']).lower():self.prefab.addItem(data['name']+'  ['+prefab+']',prefab)
  if current:self.prefab.setEditText(current)
  self.prefab.blockSignals(False)
 def open_file(self):
  filename,_=QFileDialog.getOpenFileName(self,'Open Valheim character','','Valheim Character (*.fch)')
  if not filename:return
  try:
   ch=Character(pathlib.Path(filename).read_bytes())
   if not ch.roundtrip:raise FormatError('Byte-exact round trip failed; edits disabled for this save')
   self.ch=ch;self.path=pathlib.Path(filename);self.refresh();self.savebtn.setEnabled(True)
  except Exception as e:QMessageBox.critical(self,'Invalid/unsupported save',str(e))
 def refresh(self):
  self.table.clearContents();self.selected=None
  for it in self.ch.items:
   if it.x>=8 or it.y>=6:continue
   name=HASHES.get(it.prefab_hash,f'#{it.prefab_hash}')
   display=CATALOG.get(name,{}).get('name',name)
   cell=QTableWidgetItem(f'{display}\n★ {it.quality}    ×{it.stack}'+ ('  ⚠' if it.cheated else ''))
   cell.setTextAlignment(Qt.AlignCenter);cell.setToolTip(name);self.table.setItem(it.y,it.x,cell)
  self.status.setText(f'{self.ch.name}  •  {len(self.ch.items)} items  •  '+('Cheat flag set' if self.ch.used_cheats else 'Character cheat flag clear'))
  self.skilltable.setRowCount(len(SKILLS))
  existing={x[0]:x for x in self.ch.skills}
  for row,(id,name) in enumerate(SKILLS.items()):
   self.skilltable.setItem(row,0,QTableWidgetItem(name));self.skilltable.item(row,0).setData(Qt.UserRole,id)
   lv=existing.get(id,[id,0,0]);self.skilltable.setItem(row,1,QTableWidgetItem(f'{lv[1]:.3f}'));self.skilltable.setItem(row,2,QTableWidgetItem(f'{lv[2]:.3f}'))
 def select_slot(self,y,x):
  self.selected=(x,y);self.slotlabel.setText(f'Column {x+1} / Row {y+1}')
  it=next((a for a in self.ch.items if (a.x,a.y)==(x,y)),None)
  if it:
   prefab=HASHES.get(it.prefab_hash,'')
   self.prefab.setEditText(prefab if prefab else f'#{it.prefab_hash}')
   self.qty.setValue(it.stack);self.quality.setValue(it.quality);self.durability.setValue(it.durability_raw/100);self.equipped.setChecked(it.equipped)
  else:self.prefab.setEditText('Wood');self.qty.setValue(1);self.quality.setValue(1);self.durability.setValue(100);self.equipped.setChecked(False)
 def apply_slot(self):
  if not self.ch or self.selected is None:return
  x,y=self.selected;it=next((a for a in self.ch.items if (a.x,a.y)==(x,y)),None)
  prefab=self.prefab.currentData() or self.prefab.currentText().strip()
  if '[' in prefab and prefab.endswith(']'):prefab=prefab.rsplit('[',1)[-1][:-1]
  if not prefab or prefab.startswith('#'):QMessageBox.warning(self,'Item','Enter a valid prefab name');return
  if not it:self.ch.add(prefab,x,y);it=self.ch.items[-1]
  else:it.prefab_hash=stable_hash(prefab)
  it.stack=self.qty.value();it.quality=self.quality.value();it.durability_raw=round(self.durability.value()*100);it.equipped=self.equipped.isChecked()
  self.refresh();self.table.setCurrentCell(y,x)
 def remove_slot(self):
  if self.ch and self.selected is not None:
   x,y=self.selected;self.ch.items=[a for a in self.ch.items if (a.x,a.y)!=(x,y)];self.refresh()
 def apply_skills(self):
  if not self.ch:return
  try:
   for row in range(self.skilltable.rowCount()):
    id=self.skilltable.item(row,0).data(Qt.UserRole);level=float(self.skilltable.item(row,1).text());xp=float(self.skilltable.item(row,2).text())
    if not 0<=level<=100 or not 0<=xp<1e9:raise ValueError('Skill values out of range')
    old=next((a for a in self.ch.skills if a[0]==id),None)
    if old:
     old[1]=level;old[2]=xp
    elif level or xp:self.ch.skills.append([id,level,xp])
   QMessageBox.information(self,'Skills','Skill edits applied in memory. Export to produce a save file.')
  except Exception as e:QMessageBox.warning(self,'Invalid skill',str(e))
 def max_skills(self):
  for row in range(self.skilltable.rowCount()):self.skilltable.item(row,1).setText('100');self.skilltable.item(row,2).setText('0')
 def export(self):
  if not self.ch:return
  # Apply skills before writing to avoid accidentally losing edits on that tab.
  self.apply_skills()
  default=self.path.with_name(self.path.stem+'_ULF_edited.fch')
  filename,_=QFileDialog.getSaveFileName(self,'Export edited character',str(default),'Valheim Character (*.fch)')
  if not filename:return
  try:
   out=self.ch.serialize();verified=Character(out)
   if not verified.roundtrip:raise FormatError('Export verification failed')
   if verified.profile_version!=self.ch.profile_version or verified.used_cheats!=self.ch.used_cheats:raise FormatError('Unexpected metadata change')
   target=pathlib.Path(filename)
   if target.resolve()==self.path.resolve():raise FormatError('Refusing to overwrite the original character')
   target.write_bytes(out)
   QMessageBox.information(self,'Export complete',f'Saved {target.name}.\n\nOriginal was not modified.\nClose Valheim before testing the new file.\nAchievement eligibility is not guaranteed.')
  except Exception as e:QMessageBox.critical(self,'Export failed',str(e))

def main():
 app=QApplication(sys.argv);app.setStyleSheet(STYLE);w=Window();w.show()
 if len(sys.argv)>1:
  try:
   p=pathlib.Path(sys.argv[1]);c=Character(p.read_bytes())
   if not c.roundtrip:raise FormatError('Roundtrip failed')
   w.ch=c;w.path=p;w.refresh();w.savebtn.setEnabled(True)
  except Exception as e:QMessageBox.warning(w,'Failed to load',str(e))
 sys.exit(app.exec())
if __name__=='__main__':main()
