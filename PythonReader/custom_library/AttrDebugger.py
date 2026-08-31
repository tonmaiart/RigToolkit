# from PySide6 import QtWidgets, QtCore
# import maya.cmds as cmds
# import maya.OpenMayaUI as omui
# from shiboken6 import wrapInstance

# import os
# import json

# # ----------------------------
# # Config & Path Helper
# # ----------------------------
# DOC_PATH = os.path.join(os.path.expanduser("~"), "Documents", "Maya_AttrDebugger")
# if not os.path.exists(DOC_PATH):
#     os.makedirs(DOC_PATH)

# def get_preset_path():
#     scene_path = cmds.file(q=True, sn=True)
#     if not scene_path:
#         return os.path.join(DOC_PATH, "untitled_preset.json")
    
#     scene_name = os.path.basename(scene_path).rsplit('.', 1)[0]
#     return os.path.join(DOC_PATH, f"{scene_name}_preset.json")

# def get_maya_main_window():
#     ptr = omui.MQtUtil.mainWindow()
#     return wrapInstance(int(ptr), QtWidgets.QWidget)

# # ----------------------------
# # Row Widget
# # ----------------------------
# class AttrRow(QtWidgets.QWidget):
#     changed = QtCore.Signal()

#     def __init__(self, parent=None):
#         super().__init__(parent)
#         self.attr_path = ""
#         self.is_custom_name = False 
        
#         main_layout = QtWidgets.QVBoxLayout(self)
#         main_layout.setContentsMargins(4, 4, 4, 4)
#         main_layout.setSpacing(2)

#         top_row = QtWidgets.QHBoxLayout()
#         top_row.setSpacing(6)

#         self.label_display = QtWidgets.QLabel("Label")
#         self.label_display.setStyleSheet("font-size: 18px; font-weight: bold; color: #CCCCCC;")

#         self.edit_name_btn = QtWidgets.QPushButton("edit")
#         self.edit_name_btn.setFixedWidth(40)
#         self.edit_name_btn.setStyleSheet("font-size: 10px;")

#         self.value_label = QtWidgets.QLabel("...")
#         self.value_label.setStyleSheet("font-size: 22px; font-weight: bold;")
#         self.value_label.setAlignment(QtCore.Qt.AlignRight)

#         top_row.addWidget(self.label_display)
#         top_row.addWidget(self.edit_name_btn)
#         top_row.addStretch()
#         top_row.addWidget(self.value_label)

#         bottom_row = QtWidgets.QHBoxLayout()
#         bottom_row.setSpacing(4)

#         self.line_edit = QtWidgets.QLineEdit()
#         self.line_edit.setPlaceholderText("pCube1.tx")
#         self.line_edit.setStyleSheet("font-size: 11px; background-color: #2B2B2B;")

#         self.pick_btn = QtWidgets.QPushButton("Pick")
#         self.pick_btn.setFixedWidth(45)

#         self.remove_btn = QtWidgets.QPushButton("X")
#         self.remove_btn.setFixedWidth(25)
#         self.remove_btn.setStyleSheet("color: #FF5555; font-weight: bold;")

#         bottom_row.addWidget(self.line_edit)
#         bottom_row.addWidget(self.pick_btn)
#         bottom_row.addWidget(self.remove_btn)

#         main_layout.addLayout(top_row)
#         main_layout.addLayout(bottom_row)

#         self.pick_btn.clicked.connect(self.pick_attr)
#         self.edit_name_btn.clicked.connect(self.popup_rename)
#         self.line_edit.textChanged.connect(self.on_text_edited)

#     def on_text_edited(self):
#         self.auto_rename_label()
#         self.changed.emit()

#     def auto_rename_label(self):
#         if self.is_custom_name:
#             return
#         full_text = self.line_edit.text().strip()
#         if not full_text:
#             self.label_display.setText("Label")
#             return
#         node_name = full_text.split('.')[0]
#         if node_name:
#             self.label_display.setText(node_name)

#     def popup_rename(self):
#         new_name, ok = QtWidgets.QInputDialog.getText(
#             self, "Rename Label", "Enter new display name:", 
#             text=self.label_display.text()
#         )
#         if ok and new_name:
#             self.label_display.setText(new_name)
#             self.is_custom_name = True 
#             self.changed.emit()

#     def pick_attr(self):
#             """Pick an attribute, including outputs, and show current value."""
#             sel = cmds.ls(selection=True)
#             if not sel:
#                 cmds.warning("Please select an object in Maya first.")
#                 return
            
#             obj = sel[0]
            
#             # We combine keyable, connectable, and explicit output attributes
#             # Using a set to avoid duplicate entries
#             attr_set = set()
#             attr_set.update(cmds.listAttr(obj, keyable=True) or [])
#             attr_set.update(cmds.listAttr(obj, connectable=True) or [])
#             attr_set.update(cmds.listAttr(obj, output=True) or []) # Specifically include outputs
            
#             # Sort them alphabetically for easier searching
#             attrs = sorted(list(attr_set))
            
#             display_list = []
#             for a in attrs:
#                 try:
#                     # We use f=True (formatted) to handle complex types gracefully
#                     val = cmds.getAttr(f"{obj}.{a}")
#                     display_list.append(f"{a}  (val: {val})")
#                 except:
#                     # If it's a message attribute or non-readable, just show the name
#                     display_list.append(a)
            
#             attr_display, ok = QtWidgets.QInputDialog.getItem(
#                 self, "Select Attr", f"Pick attribute for {obj}:", display_list, 0, False
#             )
            
#             if ok and attr_display:
#                 actual_attr = attr_display.split("  (val:")[0]
#                 full = f"{obj}.{actual_attr}"
#                 self.line_edit.setText(full)
#                 self.update_value() 
#                 return True
#             return False

#     def update_value(self):
#         self.attr_path = self.line_edit.text().strip()
#         if not self.attr_path:
#             self.value_label.setText("---")
#             return

#         try:
#             if cmds.objExists(self.attr_path):
#                 val = cmds.getAttr(self.attr_path)
#                 if isinstance(val, list): val = val[0]
                
#                 if isinstance(val, (list, tuple)):
#                     val = [round(v, 3) for v in val]
#                     display = f"{val}"
#                     color = "#AAFF00" 
#                 else:
#                     if isinstance(val, float): val = round(val, 4)
#                     display = str(val)
#                     if isinstance(val, (int, float)):
#                         if val > 10: color = "#FF5555" 
#                         elif val < 0: color = "#55AAFF" 
#                         else: color = "white"
#                     else:
#                         color = "white"
                
#                 self.value_label.setText(display)
#                 self.value_label.setStyleSheet(f"color: {color}; font-size: 22px; font-weight: bold;")
#             else:
#                 self.value_label.setText("Missing")
#                 self.value_label.setStyleSheet("color: #666666; font-size: 18px;")
#         except:
#             self.value_label.setText("Err")

#     def get_data(self):
#         return {
#             "name": self.label_display.text(), 
#             "attr": self.line_edit.text(),
#             "is_custom": self.is_custom_name
#         }

#     def set_data(self, data):
#         self.blockSignals(True)
#         self.label_display.setText(data.get("name", "Label"))
#         self.line_edit.setText(data.get("attr", ""))
#         self.is_custom_name = data.get("is_custom", False)
#         self.blockSignals(False)

# # ----------------------------
# # Main UI
# # ----------------------------
# class AttrDebugger(QtWidgets.QWidget):
#     def __init__(self, parent=None):
#         super().__init__(parent)
#         self.setWindowTitle("Attr Debugger")
#         self.setMinimumWidth(380)
#         self.setMinimumHeight(450)
#         self.rows = []

#         main_layout = QtWidgets.QVBoxLayout(self)
#         self.add_btn = QtWidgets.QPushButton("+ Add New Tracker")
#         self.add_btn.setMinimumHeight(35)
#         self.add_btn.setStyleSheet("background-color: #3d4c3d; font-weight: bold;")
#         main_layout.addWidget(self.add_btn)

#         self.scroll = QtWidgets.QScrollArea()
#         self.scroll.setWidgetResizable(True)
#         self.container = QtWidgets.QWidget()
#         self.v_layout = QtWidgets.QVBoxLayout(self.container)
#         self.v_layout.setAlignment(QtCore.Qt.AlignTop)
#         self.v_layout.addStretch()
#         self.scroll.setWidget(self.container)
#         main_layout.addWidget(self.scroll)

#         self.add_btn.clicked.connect(self.on_add_clicked)
#         self.timer = QtCore.QTimer(self)
#         self.timer.timeout.connect(self.update_all)
#         self.timer.start(200)
#         self.load_preset()

#     def on_add_clicked(self):
#         """Handle the button click to add a row and trigger picking immediately."""
#         row = self.add_row()
#         # Trigger pick dialog. If user cancels, the row remains empty (Skip behavior)
#         row.pick_attr() 

#     def add_row(self, data=None):
#         row = AttrRow()
#         if data:
#             row.set_data(data)
#         row.remove_btn.clicked.connect(lambda: self.remove_row(row))
#         row.changed.connect(self.save_preset)
#         self.rows.append(row)
#         self.v_layout.insertWidget(self.v_layout.count() - 1, row)
#         self.save_preset()
#         return row

#     def remove_row(self, row):
#         if row in self.rows:
#             self.rows.remove(row)
#             row.setParent(None)
#             row.deleteLater()
#             self.save_preset()

#     def update_all(self):
#         for row in self.rows:
#             row.update_value()

#     def save_preset(self):
#         data = [row.get_data() for row in self.rows]
#         path = get_preset_path()
#         try:
#             with open(path, "w") as f:
#                 json.dump(data, f, indent=4)
#         except Exception as e:
#             print(f"Save failed: {e}")

#     def load_preset(self):
#         path = get_preset_path()
#         if not os.path.exists(path): return
#         for row in self.rows[:]: 
#             self.rows.remove(row)
#             row.setParent(None)
#             row.deleteLater()
#         try:
#             with open(path, "r") as f:
#                 data = json.load(f)
#             for item in data: self.add_row(data=item)
#         except Exception as e: print(f"Load failed: {e}")

# def show_attr_debugger():
#     global win
#     try:
#         win.close()
#         win.deleteLater()
#     except:
#         pass
#     parent = get_maya_main_window()
#     win = AttrDebugger(parent=parent)
#     win.setObjectName("AttrDebuggerWindow")
#     win.setWindowFlags(QtCore.Qt.Tool)
#     win.show()

# if __name__ == "__main__":
#     show_attr_debugger()