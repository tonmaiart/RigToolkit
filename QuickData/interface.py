from tmlib.core import (
    Scene,
    Utility,
    Transform,
    Connection,
    SkinWeight,
    Controller,
    File,
    QuickData,
    BlendShape,
    System,
)
from tmlib.module.PySide import QtCore, QtGui, QtWidgets, QAction

import os, importlib, webbrowser, inspect, configparser, re, json
from tmlib.ui.interface_template import ToolkitWindow
import maya.cmds as mc


class MainWindow(ToolkitWindow):
    def __init__(self):
        # Set-up Interface
        super(MainWindow, self).__init__(os.path.basename(os.path.dirname(__file__)))

        self.local_rig_file_path = ""
        self.local_rig_file_name_only = ""
        self.local_rig_file_json = ""

        self.set_up_quick_data_widget()

    def set_up_quick_data_widget(self):
        self.ui.pushButton_build_and_read_current.clicked.connect(
            lambda X: QuickData.build_and_read()
        )
        self.ui.pushButton_build_current.clicked.connect(
            lambda x: QuickData.build_current()
        )
        self.ui.pushButton_remove_rig.clicked.connect(lambda x: QuickData.remove_rig())
        # self.ui.pushButton_hero_ctrl.clicked.connect(lambda x: QuickData.hero_ctrl())

        # self.ui.pushButton_hero_hi.clicked.connect(lambda x: QuickData.hero_hi())

        # Quick Data
        self.ui.pushButton_create_quick_data_folder.clicked.connect(
            self.create_quick_data_folder
        )
        self.ui.pushButton_open_quick_data_folder.clicked.connect(
            lambda x: QuickData.open_quick_data_folder()
        )
        self.ui.pushButton_reload_quick_data_folder.clicked.connect(
            self.reload_quick_data_folder
        )
        self.reload_quick_data_folder()

        self.dict_skin_cluster_export = {}
        self.dict_skin_cluster_import = {}

        # controller quick data
        self.ui.pushButton_save_shape.clicked.connect(
            lambda x: QuickData.export_shape_quick()
        )
        self.ui.pushButton_read_shape.clicked.connect(
            lambda x: QuickData.import_shape_quick()
        )

        # self.ui.pushButton_save_shape_custom.clicked.connect(
        #     lambda x: QuickData.export_shape_custom()
        # )
        # self.ui.pushButton_read_shape_custom.clicked.connect(
        #     lambda x: QuickData.import_shape_custom()
        # )

        # skin weight quick data
        self.ui.pushButton_import_skin_quick.clicked.connect(
            lambda x: QuickData.import_skin_quick(
                enable_transfer=self.ui.checkBox_transfer_skin.isChecked()
            )
        )
        self.ui.pushButton_export_skin_quick.clicked.connect(
            lambda x: QuickData.export_skin_quick()
        )

        # self.ui.pushButton_import_skin_custom.clicked.connect(
        #     lambda x: QuickData.import_skin_custom()
        # )
        # self.ui.pushButton_export_skin_custom.clicked.connect(
        #     lambda x: QuickData.export_skin_custom()
        # )

        self.ui.pushButton_backup_all.clicked.connect(
            lambda x: QuickData.backup_controller_and_skin()
        )
        self.ui.pushButton_apply_all.clicked.connect(
            lambda x: QuickData.apply_controller_and_skin()
        )

        self.ui.pushButton_import_all_reference.clicked.connect(
            Scene.import_all_references
        )
        self.ui.pushButton_remove_namespaces.clicked.connect(
            Scene.remove_all_namespaces
        )

        self.ui.pushButton_clean_up.clicked.connect(Scene.clean_up_scene)

        # Set Up Menu Clean Up
        self.menu_clean_up = QtWidgets.QMenu(self)
        # self.ui.pushButton_quick_clean_up.clicked.connect(Misc.clean_up_scene)

        separator_label = QAction("----- File -----", self)
        separator_label.setEnabled(False)
        self.menu_clean_up.addAction(separator_label)

        self.ui.toolButton_clean_up_scene_extra.setMenu(self.menu_clean_up)
        self.action_import_all_reference = QAction("Import All Reference", self)
        self.action_import_all_reference.triggered.connect(Scene.import_all_references)
        self.menu_clean_up.addAction(self.action_import_all_reference)

        self.action_remove_all_namespace = QAction("Remove All Namespace", self)
        self.action_remove_all_namespace.triggered.connect(Scene.remove_all_namespaces)
        self.menu_clean_up.addAction(self.action_remove_all_namespace)

        self.reload_all_reference = QAction("Reload All Refrence", self)
        self.reload_all_reference.triggered.connect(
            lambda x: QuickData.reload_all_references()
        )
        self.menu_clean_up.addAction(self.reload_all_reference)

        separator_label = QAction("----- mGear -----", self)
        separator_label.setEnabled(False)
        self.menu_clean_up.addAction(separator_label)

        self.action_clean_mgear_node = QAction("Convert mGear node to Maya", self)
        self.action_clean_mgear_node.triggered.connect(
            Scene.clean_mgear_matrix_constraint
        )
        self.action_clean_mgear_node.triggered.connect(Scene.clean_mgear_mult_matrix)
        self.menu_clean_up.addAction(self.action_clean_mgear_node)

        separator_label = QAction("----- Display -----", self)
        separator_label.setEnabled(False)
        self.menu_clean_up.addAction(separator_label)

        self.action_show_channel_box_history = QAction("Show Channel Box History", self)
        self.action_show_channel_box_history.triggered.connect(
            Scene.show_channel_box_history
        )
        self.menu_clean_up.addAction(self.action_show_channel_box_history)

        self.action_hide_channel_box_history = QAction("Hide Channel Box History", self)
        self.action_hide_channel_box_history.triggered.connect(
            Scene.hide_channel_box_history
        )
        self.menu_clean_up.addAction(self.action_hide_channel_box_history)

        separator_label = QAction("----- Lock Group -----", self)
        separator_label.setEnabled(False)
        self.menu_clean_up.addAction(separator_label)

        self.action_lock_anim_grp = QAction("Lock Anim Group", self)
        self.action_lock_anim_grp.triggered.connect(Scene.lock_anim_grp)
        self.menu_clean_up.addAction(self.action_lock_anim_grp)

        self.action_unlock_anim_grp = QAction("Unlock Anim Group", self)
        self.action_unlock_anim_grp.triggered.connect(Scene.unlock_anim_grp)
        self.menu_clean_up.addAction(self.action_unlock_anim_grp)

        separator_label = QAction("----- Clean Up -----", self)
        separator_label.setEnabled(False)
        self.menu_clean_up.addAction(separator_label)

        self.action_clear_anim_curve = QAction("Clear Anim Curve", self)
        self.action_clear_anim_curve.triggered.connect(Scene.clear_controller_animation)
        self.menu_clean_up.addAction(self.action_clear_anim_curve)

        # self.action_clear_ngskin_node = QAction("Clear ngSkinning Node", self)
        # self.action_clear_ngskin_node.triggered.connect(Misc.clear_controller_animation)
        # self.menu_clean_up.addAction(self.action_clear_ngskin_node)

        # Script function
        self.ui.pushButton_edit_script.clicked.connect(
            lambda x: QuickData.create_script()
        )
        # self.ui.pushButton_open_script_folder.clicked.connect(lambda x:QuickData.open_script_folder())
        self.ui.pushButton_run_script.clicked.connect(
            lambda x: QuickData.run_script_file()
        )

    # Quick Data
    def reload_quick_data_folder(self):
        quick_data_path = QuickData.get_quick_data_dir()

        if quick_data_path:
            self.ui.lineEdit_quick_data_dir.setText(quick_data_path)

        else:
            self.ui.lineEdit_quick_data_dir.setText("")

        return quick_data_path

    def create_quick_data_folder(self):
        current_file_path = mc.file(query=True, sceneName=True)

        if not current_file_path:
            mc.confirmDialog(message="Please save this file before create quick data.")
            return

        dir_path = os.path.dirname(current_file_path)

        # Define the subfolder structure
        subfolders = [
            "QuickData/Python",
            "QuickData/Skin",
            "QuickData/Controller",
            "QuickData/SkinTransfer",
        ]

        # Create folders
        for folder in subfolders:
            full_path = os.path.join(dir_path, folder)
            os.makedirs(full_path, exist_ok=True)

        self.reload_quick_data_folder()

    def transfer_to_combine(self):
        combine_mesh = self.list_combine_weight_target[0]
        combine_shape = mc.listRelatives(combine_mesh, children=True, shapes=True)[0]

        # get all vertex data
        dict_match_vertex = SkinWeight.get_closest_vertex(
            sources=self.list_combine_weight_source,
            target=combine_mesh,
            absolute_match=True,
        )

        if not dict_match_vertex:
            return

        # prepare skincluster node and add influence
        list_add_influences = []
        for source in self.list_combine_weight_source:
            list_add_influences += SkinWeight.get_skin_cluster_influence(source)

        if SkinWeight.get_skin_cluster_node(combine_mesh):
            node_combine_skin_cluster = SkinWeight.get_skin_cluster_node(combine_mesh)

            for joint in list_add_influences:
                try:
                    mc.skinCluster(
                        node_combine_skin_cluster,
                        edit=True,
                        addInfluence=joint,
                        weight=0.0,
                    )
                except:
                    pass

        else:
            node_combine_skin_cluster = mc.skinCluster(
                list_add_influences + [combine_mesh], toSelectedBones=True
            )[0]

        # transfer weight
        for ref_mesh in self.list_combine_weight_source:
            dict_pair_vertex = dict_match_vertex[str(ref_mesh)]
            target_skinCluster = SkinWeight.get_skin_cluster_node(ref_mesh)

            print("target skin cluster : ", ref_mesh, target_skinCluster)

            for ref_vtx, combine_vtx in dict_pair_vertex.items():

                print("combine vertex : ")
                influences = mc.skinPercent(
                    target_skinCluster, ref_vtx, query=True, transform=None
                )
                values = mc.skinPercent(
                    target_skinCluster, ref_vtx, query=True, value=True
                )

                print("vtx infs,values : ", influences, values)

                dict_weight = dict(zip(influences, values))

                for influence, value in dict_weight.items():
                    mc.skinPercent(
                        node_combine_skin_cluster,
                        combine_vtx,
                        transformValue=[(influence, value)],
                    )

    def load_source_combine_weight(self):
        selection = mc.ls(selection=True)
        self.list_combine_weight_source = selection
        self.ui.lineEdit_source_to_combine.setText(str([str(sel) for sel in selection]))

    def load_target_combine_weight(self):
        selection = mc.ls(selection=True)
        self.list_combine_weight_target = selection
        self.ui.lineEdit_target_to_combine.setText(str([str(sel) for sel in selection]))

    def import_local_rig(self):

        dict_data = File.load_json_file_to_dict(self.local_rig_file_json)
        File.add_local_rig_from_file(
            file_path=self.local_rig_file_path, parent_config=dict_data
        )

    def edit_local_rig_json(self):
        # File.open_file(file_path=)
        os.startfile(self.local_rig_file_json)

    def create_json_rig_data(self):
        # get current quick data
        quick_data_current = QuickData.get_quick_data_dir()

        if not quick_data_current:
            return

        # try to create local rig data dir if not exist
        local_rig_data_path = os.path.join(quick_data_current, "LocalRigConfig")
        path_json = os.path.join(
            local_rig_data_path, "{}.json".format(self.local_rig_file_name_only)
        )
        os.makedirs(local_rig_data_path, exist_ok=True)

        # Create Json file if not exist
        data = {
            "main_mesh_group": "Geo_Grp",
            "rig_parent": ["rig", "neck_C0_head_ctl"],
            "mesh_parent": ["FclGeo_Grp", "LocalGeo_Grp"],
            "joint_parent": ["jnt_org", "jnt_org"],
            "geo_key_name": ["Body", "EyeBrows", "Cornea_L_Geo", "Cornea_R_Geo"],
        }

        if not os.path.exists(path_json):
            with open(path_json, "w") as json_file:
                json.dump(data, json_file, indent=4)

        # Update Variables
        self.local_rig_file_json = path_json

    def browse_current(self):
        self.local_rig_file_path = mc.file(query=True, sceneName=True)
        self.local_rig_file_name_only = os.path.splitext(
            os.path.basename(self.local_rig_file_path)
        )[0]

        # update widget
        self.ui.lineEdit_local_rig_browse.setText(self.local_rig_file_name_only)

        self.create_json_rig_data()

    def browse_local_rig(self):
        scene_path = mc.file(query=True, sceneName=True)
        default_dir = (
            os.path.dirname(scene_path)
            if scene_path
            else mc.workspace(query=True, rootDirectory=True)
        )

        file_path = mc.fileDialog2(
            fileMode=1,
            dialogStyle=1,
            startingDirectory=default_dir,
            fileFilter="Maya Files (*.ma *.mb)",
        )

        if not file_path:
            return
        else:
            file_path = file_path[0]

        print("file path : ", file_path)
        self.local_rig_file_path = file_path
        self.local_rig_file_name_only = os.path.splitext(
            os.path.basename(self.local_rig_file_path)
        )[0]

        # update widget
        self.ui.lineEdit_local_rig_browse.setText(self.local_rig_file_name_only)

        self.create_json_rig_data()
