from tmlib.module.PySide import QtCore, QtWidgets

import os
import subprocess
from pathlib import Path
import maya.cmds as cmds
from tmlib.ui.interface_template import ToolkitWindow
import platform

import tmlib
from tmlib.core import QuickData, File
import json


# ------------------------------------------------------------------
# Main Window Class
# ------------------------------------------------------------------


class MainWindow(ToolkitWindow):
    def __init__(self):
        super(MainWindow, self).__init__(os.path.basename(os.path.dirname(__file__)))

        self.quick_data_folder = QuickData.get_quick_data_dir()
        self.list_current_local_script_file = []

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

    def connect_signal_ui(self):
        self.ui.pushButton_run_local_scripts.clicked.connect(self.run_local_script)

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
        

