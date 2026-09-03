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
from pathlib import Path
import tmlib
from tmlib.core import QuickData, File
import json

from UkoreMaya.core import Plugin

# class LocalScriptModel(QtCore.QAbstractListModel):


# ------------------------------------------------------------------
# Helper Functions
# ------------------------------------------------------------------


def import_all_functions(file_path):
    path = Path(file_path)
    module_name = path.stem
    module_dir = str(path.parent)

    # Make sure the directory is importable
    if module_dir not in sys.path:
        sys.path.insert(0, module_dir)

    # Force reload if already cached, otherwise fresh import
    if module_name in sys.modules:
        module = importlib.reload(sys.modules[module_name])
    else:
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module  # register before exec to allow self-import
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

        self.documents_path = Path.home() / "Documents"
        self.cache_path = os.path.join(self.documents_path,"QuickScriptHistory.json")
        self.quick_data_folder = QuickData.get_quick_data_dir()
        self.dict_current_description = {}
        self.list_current_local_script_file = []
        self.list_function_data = []
        self.target_file_paths = []
        # self.list.model().rowsMoved.connect(self.drag_drop_happened)

        self.load_functions()
        self.reload_list_widget_library()
        self.load_cache()
        self.reload_list_widget_functions()
        self.load_cache()

        self.connect_signal_ui()


    def load_cache(self):
        """ Load Exist Lastest History Opened"""
        if not os.path.exists(self.cache_path):
            return
        else:
            data = File.load_json_file_to_dict(self.cache_path)

            if data["library"] != "":
                items = self.ui.listWidget_library.findItems(data["library"], QtCore.Qt.MatchExactly)
                
                if items:
                    self.ui.listWidget_library.setCurrentItem(items[0])

            if data["function"] != "":
                items = self.ui.listWidget_functions.findItems(data["function"], QtCore.Qt.MatchExactly)
                
                if items:
                    self.ui.listWidget_functions.setCurrentItem(items[0])

    def save_cache(self):
        """ Update Current Cache"""

        if self.ui.listWidget_library.currentItem():
            library = self.ui.listWidget_library.currentItem().text()
        else:
            library = ""

        if self.ui.listWidget_functions.currentItem():
            function = self.ui.listWidget_functions.currentItem().text()
        else:
            function = ""

        data = {
            "library": library,
            "function": function
        }

        with open(self.cache_path, 'w') as f:
            json.dump(data, f, indent=4)
    
    def load_functions(self):
        self.list_function_data = []

        tool_root = os.path.dirname(__file__)
        config_path = os.path.join(tool_root, "config")
        global_path = os.path.join(config_path, "GlobalPaths.json")
        dict_global_paths = File.load_json_file_to_dict(file_path=global_path)

        print(dict_global_paths)
        # paths in GlobalPaths.json are relative to this tool's own folder
        # (custom_library/ ships bundled with QuickScript) rather than
        # machine-specific absolute paths
        self.target_file_paths = [
            os.path.join(tool_root, relative_path)
            for relative_path in dict_global_paths["paths"]
        ]

        for path in self.target_file_paths:
            if os.path.exists(path):
                self.list_function_data += import_all_functions(path)


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

    def reload_list_widget_library(self):
        self.ui.listWidget_library.clear()

        for path in self.target_file_paths:
            print("combobox:", path)
            self.ui.listWidget_library.addItem(os.path.basename(path))

        try:
            self.ui.listWidget_library.setCurrentRow(0)
        except:
            pass
    
    def reload_list_widget_functions(self):
        """Populate the list widget with colors and data"""

        self.ui.listWidget_functions.clear()

        try:
            self.ui.listWidget_functions.setCurrentRow(0)
        except:
            pass

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
        self.ui.pushButton_reload.clicked.connect(self.reload_button_clicked)
        self.ui.pushButton_edit_extra_path.clicked.connect(self.open_extra_path_file)
        self.ui.listWidget_library.itemDoubleClicked.connect(self.edit_library_script)
        
        # Run Script Signals
        self.ui.listWidget_functions.itemDoubleClicked.connect(
            self.quick_run_pure_function
        )
        self.ui.listWidget_functions.itemClicked.connect(self.save_cache)
        self.ui.listWidget_library.itemClicked.connect(self.save_cache)

        # Search Signals
        self.ui.lineEdit_search.textChanged.connect(self.reload_list_widget_functions)
        self.ui.listWidget_library.itemSelectionChanged.connect(
            self.reload_list_widget_functions
        )

        # Right Click to function Menu
        self.ui.listWidget_functions.setContextMenuPolicy(
            QtCore.Qt.CustomContextMenu
        )
        self.ui.listWidget_functions.customContextMenuRequested.connect(
            self.show_context_menu
        )
    
    def reload_button_clicked(self):
        Plugin.reload_plugins()

        self.load_functions()

        self.reload_list_widget_library()
        self.load_cache()

        self.reload_list_widget_functions()

        self.load_cache()

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
        config_path = os.path.join(os.path.dirname(__file__), "config")
        global_path = os.path.join(config_path, "GlobalPaths.json")

        self.launch_script_file(global_path)


    def show_context_menu(self, position):
            item = self.ui.listWidget_functions.itemAt(position)
            if not item:
                return

            func_data = item.data(QtCore.Qt.UserRole)

            menu = QtWidgets.QMenu()
            info_action = menu.addAction("What is this?")
            menu.addSeparator()
            edit_action = menu.addAction("Edit Script...")

            action = menu.exec_(self.ui.listWidget_functions.mapToGlobal(position))

            if action == info_action:
                # FIXED QUOTES BELOW
                info_text = f"{func_data['name']} \n {func_data['docstring']}"

                cmds.confirmDialog(
                    title=f"Function: {func_data['name']}", message=info_text
                )
            elif action == edit_action:
                self.launch_script_file(func_data["path"])

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

    def clear_layout(self, layout):
        if layout is None:
            return
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                self.clear_layout(child.layout())

