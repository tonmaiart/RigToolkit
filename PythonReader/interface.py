from tmlib.module.PySide import QtCore, QtGui, QtWidgets

import os
import importlib.util
import inspect
import ast
import subprocess
from pathlib import Path
import maya.cmds as cmds
from tmlib.ui.interface_template import ToolkitWindow
import platform
import sys

import tmlib
from tmlib.core import QuickData, File
import json


# class LocalScriptModel(QtCore.QAbstractListModel):


# ------------------------------------------------------------------
# Helper Functions
# ------------------------------------------------------------------


def import_all_functions(file_path):
    path = Path(file_path)
    module_name = path.stem
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    function_list = []

    # ดึงรายการชื่อฟังก์ชันทั้งหมดที่ถูกนิยามไว้ในไฟล์นี้จริงๆ
    # (เช็คจากสคริปต์ที่เราเพิ่ง exec_module ไป)
    for name, obj in inspect.getmembers(module):
        # 1. เช็คว่าชื่อนี้มีอยู่ใน module's dict และไม่ใช่การ import มาจากที่อื่น
        # ฟังก์ชันที่โดน decorate จะยังอยู่ใน module.__dict__ ของไฟล์ตัวเอง
        if name in module.__dict__:
            # ตรวจสอบว่าเป็นสิ่งที่เรียกใช้งานได้ (Function หรือ Wrapped Function)
            if inspect.isfunction(obj) or inspect.isroutine(obj):

                # ข้ามพวกตัวแปรระบบ __name__, __doc__
                if name.startswith("__"):
                    continue

                # 2. พยายามเจาะหาฟังก์ชันดั้งเดิม (Unwrap) เพื่อเอาค่า Signature/Docstring
                # ถ้า decorator ไม่ได้ใช้ wraps เราจะดึงข้อมูลยากหน่อย
                # แต่เราสามารถดึงข้อมูลพื้นฐานได้
                try:
                    # ใช้ __wrapped__ ถ้า decorator มีการใช้ functools.wraps
                    real_obj = getattr(obj, "__wrapped__", obj)
                    signature = inspect.signature(real_obj)
                    docstring = inspect.getdoc(real_obj) or "No docstring available."
                except:
                    # ถ้าดึง signature ไม่ได้จริงๆ (กรณี decorator ซับซ้อน)
                    signature = None
                    docstring = "Decorated function (Docstring hidden)"

                args_details = {}
                is_pure = True

                if signature:
                    params = signature.parameters
                    if not params:
                        is_pure = True
                    else:
                        for param_name, param in params.items():
                            has_default = param.default is not inspect._empty
                            if not has_default:
                                is_pure = False

                            args_details[param_name] = {
                                "type": (
                                    str(param.annotation)
                                    if param.annotation is not inspect._empty
                                    else None
                                ),
                                "default": str(param.default) if has_default else None,
                            }

                function_list.append(
                    {
                        "name": name,
                        "docstring": docstring,
                        "arguments": args_details,
                        "pure": is_pure,
                        "path": str(file_path),
                    }
                )

    return function_list


def get_function_object(file_path, func_name):
    """
    Load or reload a module from file path, then return function object
    """

    path = Path(file_path)
    module_name = path.stem
    module_dir = str(path.parent)

    # make sure path is importable
    if module_dir not in sys.path:
        sys.path.insert(0, module_dir)

    # import or reload
    if module_name in sys.modules:
        module = importlib.reload(sys.modules[module_name])
    else:
        module = importlib.import_module(module_name)

    return getattr(module, func_name, None)


def undoable(func):
    """Maya undo wrapper"""

    def wrapper(*args, **kwargs):
        cmds.undoInfo(openChunk=True)
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            cmds.undoInfo(closeChunk=True)

    return wrapper


# ------------------------------------------------------------------
# Main Window Class
# ------------------------------------------------------------------


class MainWindow(ToolkitWindow):
    def __init__(self):
        super(MainWindow, self).__init__(os.path.basename(os.path.dirname(__file__)))

        self.quick_data_folder = QuickData.get_quick_data_dir()
        self.dict_current_description = {}
        self.list_current_local_script_file = []
        self.list_function_data = []
        self.target_file_paths = []
        # self.list.model().rowsMoved.connect(self.drag_drop_happened)

        # self.import_functions()
        # self.reload_list_widget_library()
        # self.reload_list_widget_functions()

        self.init_quick_data_button()
        self.on_reload_local_script_clicked()
        self.reload_quick_data_button()

        self.connect_signal_ui()

        cmds.scriptJob(
            event=["SceneOpened", self.scene_opened_action],
            parent=self.objectName(),
        )

    def scene_opened_action(self):
        self.reload_quick_data_button()

        if self.quick_data_folder:
            self.reload_local_script_combobox()
            self.reload_local_script_list_widget()
            self.make_local_library_metadata_exists()

    def import_functions(self):
        config_path = os.path.join(os.path.dirname(__file__), "Config")
        global_path = os.path.join(config_path, "GlobalPaths.json")
        dict_global_paths = File.load_json_file_to_dict(file_path=global_path)

        print(dict_global_paths)
        self.target_file_paths = dict_global_paths["paths"]

        for path in self.target_file_paths:
            if os.path.exists(path):
                self.list_function_data += import_all_functions(path)

    def on_reload_local_script_clicked(self):
        if self.quick_data_folder:
            self.reload_local_script_combobox()
            self.reload_local_script_list_widget()
            self.make_local_library_metadata_exists()



    def reload_local_script_combobox(self):
        # clear combo box
        self.ui.comboBox_local_scripts.clear()

        # add item to combo box
        if self.quick_data_folder is False:
            return

        for dir_name in os.listdir(os.path.join(self.quick_data_folder, "Python")):
            if os.path.isdir(os.path.join(self.quick_data_folder, "Python", dir_name)):
                self.ui.comboBox_local_scripts.addItem(dir_name)

        # set combobox to match current file key name
        self.ui.comboBox_local_scripts.setCurrentText(
            self.get_current_file_info()["key"]
        )

    def get_current_file_info(self):
        current_absolute_file_path = cmds.file(q=True, sceneName=True)
        current_file_name = os.path.basename(current_absolute_file_path)
        current_name = current_file_name.split(".")[0]
        current_key_name = current_name.split("_")[0]

        return {
            "path": current_absolute_file_path,
            "file_name": current_key_name,
            "name": current_name,
            "key": current_key_name,
        }

    def reload_local_script_list_widget(self):
        """
        Load local script list widget items
        """

        if self.quick_data_folder is False:
            return

        
        # clear widget
        self.ui.listWidget_local_scripts.clear()

        # prepare path
        current_key_name = self.ui.comboBox_local_scripts.currentText()
        current_key_script_path = os.path.join(
            self.quick_data_folder, "Python", current_key_name
        )

        # make sure path exist
        os.makedirs(current_key_script_path, exist_ok=True)

        # add item to list widget
        self.list_current_local_script_file = []
        for name in os.listdir(current_key_script_path):
            if not ".py" in name:
                continue

            self.list_current_local_script_file.append(
                {
                    "name": name.split(".")[0],
                    "filename": name,
                    "path": os.path.join(current_key_script_path, name),
                    "muted": False,
                }
            )

            self.ui.listWidget_local_scripts.addItem(name.split(".")[0])

        # # ====================================
        # # Update if json data metadata exists 
        # # ====================================

        # data = File.load_json_file_to_dict(os.path.join(current_key_script_path, current_key_name + ".json"))

        # if data is None:
        #     return

        # if "order" not in data:
        #     return
        
        # if data["order"] is None:
        #     return
        
        # # Build a dict of {text: row_index}
        # item_map = {self.ui.listWidget_local_scripts.item(i).text(): i for i in range(self.ui.listWidget_local_scripts.count())}

        # # Build sorted row list, skip if not found
        # sorted_rows = [item_map[text] for text in data["order"] if text in item_map]

        # # Reorder by taking rows out and re-inserting
        # for target_index, source_row in enumerate(sorted_rows):
        #     # source_row may have shifted, find current position
        #     current_row = next(
        #         i for i in range(self.ui.listWidget_local_scripts.count())
        #         if self.ui.listWidget_local_scripts.item(i).text() == data["order"][target_index]
        #     )
        #     if current_row != target_index:
        #         item = self.ui.listWidget_local_scripts.takeItem(current_row)
        #         self.ui.listWidget_local_scripts.insertItem(target_index, item)

    def reload_list_widget_library(self):
        self.ui.listWidget_library.clear()
        self.ui.listWidget_library.addItem("All")

        for path in self.target_file_paths:
            print("combobox:", path)
            self.ui.listWidget_library.addItem(os.path.basename(path))

    def reload_list_widget_functions(self):
        """Populate the list widget with colors and data"""

        self.ui.listWidget_functions.clear()
        # self.ui.listWidget_functions.setCurrentRow(0)

        current_selected = self.ui.listWidget_library.selectedItems()

        print("current selected : ",current_selected)
        if not current_selected:
            return
        else:
            current_selected = current_selected[0]

        current_file_filter = current_selected.text()
        search_text = self.ui.lineEdit_search.text().lower().strip()

        for func_data in self.list_function_data:
            # Filter: Filename
            if current_file_filter != "All":
                if os.path.basename(func_data["path"]) != current_file_filter:
                    continue

            # Filter: Search Text
            if search_text and search_text not in func_data["name"].lower():
                continue

            item = QtWidgets.QListWidgetItem(func_data["name"])
            item.setData(QtCore.Qt.UserRole, func_data)  # เก็บ dict ไว้ใน item

            # Color: Yellow if Pure
            if func_data["pure"]:
                item.setForeground(QtGui.QColor("yellow"))

            self.ui.listWidget_functions.addItem(item)

    def connect_signal_ui(self):
        # edit extra path
        # self.ui.pushButton_edit_extra_path.clicked.connect(self.open_extra_path_file)
        # self.ui.listWidget_library.itemDoubleClicked.connect(self.edit_library_script)

        # Standard Signals
        # self.ui.listWidget_functions.itemClicked.connect(self.load_description)
        # self.ui.listWidget_functions.itemDoubleClicked.connect(
            # self.quick_run_pure_function
        # )
        # self.ui.pushButton_run_script.clicked.connect(self.run_script)
        self.ui.pushButton_run_local_scripts.clicked.connect(self.run_local_script)

        # # Filter Signals
        # self.ui.lineEdit_search.textChanged.connect(self.reload_list_widget_functions)
        # self.ui.listWidget_library.itemSelectionChanged.connect(
        #     self.reload_list_widget_functions
        # )

        # # Context Menu
        # self.ui.listWidget_functions.setContextMenuPolicy(
        #     QtCore.Qt.CustomContextMenu
        # )
        # self.ui.listWidget_functions.customContextMenuRequested.connect(
        #     self.show_context_menu
        # )

        # Quick Data / Local Script
        self.ui.pushButton_path_quick_data_folder.clicked.connect(
            self.quick_data_path_button_action
        )

        self.ui.listWidget_local_scripts.setContextMenuPolicy(
            QtCore.Qt.CustomContextMenu
        )
        self.ui.listWidget_local_scripts.customContextMenuRequested.connect(
            self.show_local_scripts_context_menu
        )
        self.ui.listWidget_local_scripts.model().rowsMoved.connect(self.on_rows_moved)

        self.ui.comboBox_local_scripts.currentTextChanged.connect(
            self.reload_local_script_list_widget
        )
        

    def edit_library_script(self):
        sel = self.ui.listWidget_library.selectedItems()

        if not sel:
            return
        
        sel= sel[0].text()
        print("Target File Paths ",self.target_file_paths)
        for each in self.target_file_paths:
            if sel in each:
                self.launch_script_file(each)
        
    def launch_script_file(self,path):
        if platform.system() == "Windows":
            os.startfile(path)

        else:
            # macOS and Linux
            subprocess.Popen(["code", "--goto", path])

    def open_extra_path_file(self):
        config_path = os.path.join(os.path.dirname(__file__), "Config")
        global_path = os.path.join(config_path, "GlobalPaths.json")

        self.launch_script_file(global_path)


    def edit_local_script(self):
        item = self.ui.listWidget_local_scripts.currentItem().text()

        result = [
            each
            for each in self.list_current_local_script_file
            if each.get("name") == item
        ]

        path_edit = result[0]["path"]
        print("Open Script File : {}".format(path_edit))

        if platform.system() == "Windows":
            os.startfile(path_edit)

        else:
            # macOS and Linux
            subprocess.Popen(["code", "--goto", path_edit])

    def show_local_scripts_context_menu(self, position):
        # ตรวจสอบว่ามีไอเทมอยู่ที่ตำแหน่งที่คลิกหรือไม่
        selected_item = self.ui.listWidget_local_scripts.selectedItems()
        popup_item = self.ui.listWidget_local_scripts.itemAt(position)

        menu = QtWidgets.QMenu()

        if popup_item:
            # --- เมนูสำหรับตอนคลิกที่ตัวไอเทม ---

            action_edit_script = menu.addAction("Edit Scripts...")
            menu.addSeparator()
            action_mute_toggle = menu.addAction("Mute Toggle")
            menu.addSeparator()

            action_run = menu.addAction("Run Selected Scripts")
            menu.addSeparator()

            # ใส่ตัวอย่างการทำงาน
            action = menu.exec_(self.ui.listWidget_local_scripts.mapToGlobal(position))

            if action == action_mute_toggle:
                first_mute_state = None

                for i, sel_item in enumerate(selected_item):
                    font = popup_item.font()
                    data = [
                        each
                        for each in self.list_current_local_script_file
                        if each.get("name") == sel_item.text()
                    ][0]

                    isMute = data["muted"]
                    self.list_current_local_script_file.remove(data)

                    if first_mute_state:
                        print("Set State for ", sel_item, first_mute_state)
                        font.setStrikeOut(first_mute_state)
                        data["muted"] = first_mute_state
                    elif isMute:
                        font.setStrikeOut(False)
                        data["muted"] = False
                    else:
                        font.setStrikeOut(True)
                        data["muted"] = True

                    sel_item.setFont(font)
                    self.list_current_local_script_file.append(data)

                    if i == 0:
                        first_mute_state = data["muted"]

                        print(first_mute_state)

            elif action == action_edit_script:
                self.edit_local_script()
        else:
            # --- เมนูสำหรับตอนคลิกที่พื้นที่ว่าง (Empty Space) ---
            action_refresh = menu.addAction("Refresh List")
            action_open_dir = menu.addAction("Open Local Directory")
            action_new_file = menu.addAction("Create New Script")

            action = menu.exec_(self.ui.listWidget_local_scripts.mapToGlobal(position))

            if action == action_refresh:
                self.on_reload_local_script_clicked()  # หรือฟังก์ชันโหลดลิสต์ของคุณ
            elif action == action_open_dir:
                self.open_local_script_folder()  # ฟังก์ชันเปิด Folder ในเครื่อง
            elif action == action_new_file:
                self.create_new_local_script()  # ฟังก์ชันเปิด Folder ในเครื่อง

    def create_new_local_script(self):
        new_name = input("Input New Script Name")
        QuickData.create_script(name=new_name)

        self.on_reload_local_script_clicked()
        self.make_local_library_metadata_exists()

    def open_local_script_folder(self):
        current_key = self.ui.comboBox_local_scripts.currentText()
        os.startfile(os.path.join(self.quick_data_folder, "Python", current_key))

    def show_context_menu(self, position):
        item = self.ui.listWidget_functions.itemAt(position)
        if not item:
            return

        func_data = item.data(QtCore.Qt.UserRole)

        menu = QtWidgets.QMenu()
        edit_action = menu.addAction("Edit Script...")
        info_action = menu.addAction("Info")

        action = menu.exec_(self.ui.listWidget_functions.mapToGlobal(position))

        if action == edit_action:
            file_path = func_data["path"]
            command = ["code", "--goto", file_path]

            # Check if the OS is Windows
            is_windows = platform.system() == "Windows"

            try:
                subprocess.Popen(command, shell=is_windows)
            except FileNotFoundError:
                print(
                    "Error: 'code' command not found. Ensure VS Code is in your PATH."
                )
        elif action == info_action:
            info_text = json.dumps(func_data, indent=4)
            cmds.confirmDialog(
                title=f"Function: {func_data['name']}", message=info_text
            )

    def quick_run_pure_function(self, item):
        """Double-click handler for pure functions"""
        func_data = item.data(QtCore.Qt.UserRole)

        if not func_data["pure"]:
            cmds.warning(
                f"'{func_data['name']}' is not a pure function. Please fill arguments."
            )
            return

        func_obj = get_function_object(func_data["path"], func_data["name"])
        if func_obj:
            print(f"Quick Running: {func_data['name']}")
            undoable(func_obj)()

    def load_description(self):
        item = self.ui.listWidget_functions.currentItem()
        if not item:
            return

        func_data = item.data(QtCore.Qt.UserRole)

        self.ui.textBrowser_docstring.setPlainText(func_data["docstring"])
        self.clear_layout(self.ui.layout_arguments)
        self.ui.label_function_name.setText(func_data["name"])

        self.dict_current_description = {
            "func_name": func_data["name"],
            "path": func_data["path"],
            "args": {},
        }

        for arg_name, arg_info in func_data["arguments"].items():
            _, _, line_edit = add_input_row(
                self.ui.layout_arguments,
                arg_name,
                default=arg_info["default"],
                type=arg_info["type"],
            )
            self.dict_current_description["args"][arg_name] = {
                "input": line_edit,
                "type": arg_info["type"],
            }

    def run_script(self):
        func_name = self.dict_current_description.get("func_name")
        file_path = self.dict_current_description.get("path")
        if not func_name:
            return

        func_obj = get_function_object(file_path, func_name)

        prepared_args = {}
        for arg_name, data in self.dict_current_description["args"].items():
            ui_value = data["input"].text()
            prepared_args[arg_name] = self.cast_to_type(ui_value)

        if func_obj:
            undoable(func_obj)(**prepared_args)

    def run_local_script(self):
        list_order = []

        for i in range(self.ui.listWidget_local_scripts.count()):
            item = self.ui.listWidget_local_scripts.item(i)
            data = [
                each
                for each in self.list_current_local_script_file
                if each.get("name") == item.text()
            ][0]

            if not data["muted"]:
                list_order.append(item.text())

        print(list_order)
        QuickData.run_script_file(
            script_path=os.path.join(
                self.quick_data_folder, "Python", self.get_current_file_info()["key"]
            ),
            order=list_order,
        )

    def cast_to_type(self, value_str):
        if not value_str or value_str.strip() == "":
            return None
        value_str = value_str.strip()
        if value_str.lower() in ("true", "yes", "on"):
            return True
        if value_str.lower() in ("false", "no", "off"):
            return False
        try:
            return ast.literal_eval(value_str)
        except:
            if "," in value_str:
                return [i.strip() for i in value_str.split(",") if i.strip()]
        return value_str

    def clear_layout(self, layout):
        if layout is None:
            return
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                self.clear_layout(child.layout())


    # Quick Data
    def reload_quick_data_button(self):
        print("# Reload Quick Data Path")

        self.quick_data_folder = QuickData.get_quick_data_dir()

        if self.quick_data_folder is False:
            self.ui.pushButton_path_quick_data_folder.setText(
                "<<< Quick Data Folder Missing - Click to Create >>>"
            )
        else:
            self.ui.pushButton_path_quick_data_folder.setText(
                str(self.quick_data_folder)
            )

    def init_quick_data_button(self):
        if self.quick_data_folder:
            self.ui.pushButton_path_quick_data_folder.setText(self.quick_data_folder)
        else:
            self.ui.pushButton_path_quick_data_folder.setText(
                "<<< Quick Data Folder Missing - Click to Create >>>"
            )

    def quick_data_path_button_action(self):
        # ===============
        # Clicked Action
        # ===============

        print(self.quick_data_folder)
        # if not exist - create new folder
        if self.quick_data_folder is False:
            print("# Create New Quick data folder : ", self.quick_data_folder)

            QuickData.create_quick_data_folder_template()
            self.quick_data_folder = QuickData.get_quick_data_dir()
            self.ui.pushButton_path_quick_data_folder.setText(self.quick_data_folder)

        # if already exist - open exist folder
        elif self.quick_data_folder == self.quick_data_folder:
            QuickData.open_quick_data_folder()
            print("# Open Exist Quick Data Folder : ", self.quick_data_folder)

    def on_rows_moved(self):
        """
        Update order
        """
        self.make_local_library_metadata_exists()
        self.update_local_library_metadata()

    def edit_local_rig_json(self):
        # File.open_file(file_path=)
        os.startfile(self.local_rig_file_json)

    def update_local_library_metadata(self):
        current_quick_data_folder_dir = self.quick_data_folder
        current_python_folder_name = self.ui.comboBox_local_scripts.currentText()
        json_path = os.path.join(current_quick_data_folder_dir,"Python",current_python_folder_name,current_python_folder_name+".json")


        data = File.load_json_file_to_dict(json_path)

        # update order based on current one to json file metadata
        all_items = []
        for i in range(self.ui.listWidget_local_scripts.count()):
            all_items.append(self.ui.listWidget_local_scripts.item(i).text())

        data["order"] = all_items

        if os.path.exists(json_path):
            with open(json_path,'w') as json_file:
                json.dump(data,json_file,indent=4)
    
    def make_local_library_metadata_exists(self):
        """
        Used for store order and proxy path
        """

        current_quick_data_folder_dir = self.quick_data_folder
        current_python_folder_name = self.ui.comboBox_local_scripts.currentText()
        json_path = os.path.join(current_quick_data_folder_dir,"Python",current_python_folder_name,current_python_folder_name+".json")

        # make sure json path created
        data = {}

        if not os.path.exists(json_path):
            with open(json_path,'w') as json_file:
                json.dump(data,json_file,indent=4)
        



# ------------------------------------------------------------------
# UI Helpers
# ------------------------------------------------------------------


def add_input_row(parent_layout, label_text, default, type):
    h_layout = QtWidgets.QHBoxLayout()
    line_edit = QtWidgets.QLineEdit()
    label = QtWidgets.QLabel(str(type.__name__) if type else "None")

    btn = QtWidgets.QPushButton(label_text)
    btn.setFixedWidth(120)

    h_layout.addWidget(btn)
    h_layout.addWidget(line_edit)
    h_layout.addWidget(label)

    if isinstance(parent_layout, QtWidgets.QGridLayout):
        parent_layout.addLayout(h_layout, parent_layout.rowCount(), 0)
    else:
        parent_layout.addLayout(h_layout)

    if default and default != "None":
        line_edit.setText(default)

    btn.clicked.connect(lambda: line_edit_action(line_edit, type))
    line_edit.setClearButtonEnabled(True)
    return label_text, btn, line_edit


def line_edit_action(line_edit, typ):
#     if (cmds.selectPref(tso=True, q=True)==0):
#     cmds.selectPref(tso=True)
    
# a = cmds.ls(orderedSelection =1,fl=1)

    sel = cmds.ls(sl=1)

    if not sel:
        return

    if typ == list:
        line_edit.setText(str(sel))
    else:
        line_edit.setText(str(sel[0]))
