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
)
from tmlib.module.PySide import QtCore, QtGui, QtWidgets, QAction

import os, importlib, webbrowser, inspect, configparser, re, json
from tmlib.ui.interface_template import ToolkitWindow
import maya.cmds as cmds
import ast
import time

from tmlib.ui import uitools


class MainWindow(ToolkitWindow):
    def __init__(self):
        # Set-up Interface
        super(MainWindow, self).__init__(os.path.basename(os.path.dirname(__file__)))

        self.local_rig_file_path = ""
        self.local_rig_file_name_only = ""
        self.local_rig_file_json = ""
        self.grp_data_keyword = "Data_Grp"
        self.grp_data = ""
        self.base_mesh = ""
        self.blend_shape_node = ""
        self.weight_mesh = "weight_split_mesh"

        # rename widget tab
        self.dict_rename_target = {}
        self.dict_rename_output = {}

        self.ui.lineEdit_search.textChanged.connect(self.update_rename_list_widget)
        self.ui.lineEdit_replace.textChanged.connect(self.update_rename_list_widget)
        self.ui.lineEdit_prefix.textChanged.connect(self.update_rename_list_widget)
        self.ui.lineEdit_suffix.textChanged.connect(self.update_rename_list_widget)
        self.ui.lineEdit_rename.textChanged.connect(self.update_rename_list_widget)
        self.ui.checkBox_auto_underscore.clicked.connect(self.update_rename_list_widget)

        self.ui.pushButton_quick_fill_rename.clicked.connect(self.quick_load)
        self.ui.pushButton_clear_all_text_box.clicked.connect(
            self.clear_all_rename_text_box
        )
        self.ui.pushButton_apply_name.clicked.connect(self.apply_rename)

        cmds.scriptJob(
            event=["SelectionChanged", self.update_rename_list_widget],
            parent=self.objectName(),
        )

        self.update_rename_list_widget()

    # rename function -----------------------------------------
    def quick_load(self):
        if self.dict_rename_output:
            first_key = list(self.dict_rename_output.keys())[0]
            self.ui.lineEdit_rename.setText(Utility.cut(str(first_key)))

    def clear_all_rename_text_box(self):
        self.ui.lineEdit_rename.setText("")
        self.ui.lineEdit_search.setText("")
        self.ui.lineEdit_replace.setText("")
        self.ui.lineEdit_prefix.setText("")
        self.ui.lineEdit_suffix.setText("")

    def update_rename_list_widget(self):
        def add_prefix(input_text):
            prefix = self.ui.lineEdit_prefix.text()
            if prefix and self.ui.checkBox_auto_underscore.isChecked():
                return "{}_".format(prefix) + input_text
            return prefix + input_text

        def add_suffix(input_text):
            suffix = self.ui.lineEdit_suffix.text()
            if suffix and self.ui.checkBox_auto_underscore.isChecked():
                return input_text + "_{}".format(suffix)
            return input_text + suffix

        def get_rename_result(input_text, i):
            list_alphabet = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
            rename = self.ui.lineEdit_rename.text()
            base_name = rename if rename else input_text

            if "$" in base_name:
                base_name = base_name.replace("$", list_alphabet[i % 26])

            if "####" in base_name:
                base_name = base_name.replace("####", str(i + 1).zfill(4))
            if "###" in base_name:
                base_name = base_name.replace("###", str(i + 1).zfill(3))
            if "##" in base_name:
                base_name = base_name.replace("##", str(i + 1).zfill(2))
            if "#" in base_name:
                base_name = base_name.replace("#", str(i + 1))

            return base_name

        selection = cmds.ls(sl=1)
        if not selection:
            self.dict_rename_target = {}
            self.ui.listView_rename_output.setModel(QtGui.QStandardItemModel())
            return

        self.dict_rename_target = {Utility.cut(sel): sel for sel in selection}
        model = QtGui.QStandardItemModel()
        self.ui.listView_rename_output.setModel(model)

        dict_output = {}
        for i, target_node in enumerate(self.dict_rename_target.values()):
            base_name = Utility.cut(target_node)
            name = get_rename_result(base_name, i)

            search = self.ui.lineEdit_search.text()
            replace = self.ui.lineEdit_replace.text()
            if search:
                name = name.replace(search, replace)

            name = add_prefix(name)
            name = add_suffix(name)
            dict_output[target_node] = name

        self.dict_rename_output = dict_output

        for before_node, after_name in dict_output.items():
            short_before = before_node.split("|")[-1]
            if short_before == after_name:
                item_text = short_before
            else:
                item_text = "{} > {}".format(short_before, after_name)
            model.appendRow(QtGui.QStandardItem(item_text))

    @uitools.undoable
    def apply_rename(self):
        # Sort by length to rename children before parents to avoid losing paths
        sorted_nodes = sorted(self.dict_rename_output.keys(), key=len, reverse=True)
        for node in sorted_nodes:
            new_name = self.dict_rename_output[node]
            if cmds.objExists(node):
                cmds.rename(node, new_name)
        cmds.inViewMessage(amg="<hl>Rename Apply</hl>", pos="botCenter", fade=True)

    # set attribute function -------------------------------------
    def update_attribute_target(self):
        list_set_attribute_target = cmds.ls(sl=1)
        self.ui.listWidget_node.clear()
        self.ui.listWidget_node.addItems(
            [Utility.cut(node) for node in list_set_attribute_target]
        )

        selected_attrs = self.ui.listWidget_attribute.selectedItems()
        if not selected_attrs:
            return
        attr = selected_attrs[0].text()

        attr_path = "{}.{}".format(list_set_attribute_target[0], attr)
        attr_type = cmds.getAttr(attr_path, type=True)

        if attr_type == "bool":
            self.ui.tabWidget_set_attribute_by_type.setCurrentIndex(0)
        elif attr_type in ["float", "double", "doubleLinear", "doubleAngle"]:
            self.ui.doubleSpinBox_float.setValue(cmds.getAttr(attr_path))
            self.ui.tabWidget_set_attribute_by_type.setCurrentIndex(1)
        elif attr_type in ["int", "long", "short"]:
            self.ui.spinBox_int.setValue(cmds.getAttr(attr_path))
            self.ui.tabWidget_set_attribute_by_type.setCurrentIndex(2)
        elif attr_type == "matrix":
            self.ui.tabWidget_set_attribute_by_type.setCurrentIndex(3)
            matrix = cmds.getAttr(attr_path)
            self.ui.plainTextEdit_matrix_set.setPlainText(str(matrix))
        elif attr_type == "enum":
            self.ui.tabWidget_set_attribute_by_type.setCurrentIndex(4)
            enum_str = cmds.attributeQuery(
                attr, n=list_set_attribute_target[0], listEnum=True
            )[0]
            self.ui.comboBox_set_attribute_enum.clear()
            self.ui.comboBox_set_attribute_enum.addItems(enum_str.split(":"))
            self.ui.comboBox_set_attribute_enum.setCurrentIndex(cmds.getAttr(attr_path))
        else:
            self.ui.tabWidget_set_attribute_by_type.setCurrentIndex(5)

        self.ui.listWidget_attribute.clear()
        all_attrs = cmds.listAttr(list_set_attribute_target[0]) or []
        search_term = self.ui.lineEdit_search_attribute.text().lower()
        filtered = (
            [a for a in all_attrs if search_term in a.lower()]
            if search_term
            else all_attrs
        )
        self.ui.listWidget_attribute.addItems(sorted(filtered))

    @uitools.undoable
    def set_attribute(self, value, typ="float"):
        attr = self.get_current_selected_module_name_single()
        selection = cmds.ls(sl=1)
        for node in selection:
            try:
                attr_path = "{}.{}".format(node, attr)
                if typ in ["float", "enum", "int"]:
                    cmds.setAttr(attr_path, value)
                elif typ == "matrix":
                    val = ast.literal_eval(value)
                    flat_matrix = [e for row in val for e in row]
                    cmds.setAttr(attr_path, flat_matrix, type="matrix")
            except Exception as e:
                cmds.displayWarning(
                    "Cannot Set Attribute for {}.{} : {}".format(node, attr, e)
                )

    def get_current_selected_module_name_single(self):
        res = [item.text() for item in self.ui.listWidget_attribute.selectedItems()]
        return res[0] if res else None

    # Snap to vertex funcion
    def remove_all(self):
        self.ui.listWidget_target.clear()
        self.DICT_TARGET = {}

    @uitools.undoable
    def snap_joint_position(self):
        for target_name, data in self.DICT_TARGET.items():
            target_node = data["Node"]
            vertex_target = data["Data"]
            if not vertex_target:
                continue
            Transform.transform_to_vertex(
                target_object=target_node, list_vertex=vertex_target
            )
        cmds.inViewMessage(
            amg="Snap All to selected vertex", pos="midCenter", fade=True
        )

    def add_object_snap_target(self):
        selection = cmds.ls(sl=1, type="transform")
        for sel in selection:
            sel_name = Utility.cut(sel)
            if sel_name not in self.DICT_TARGET:
                self.DICT_TARGET[sel_name] = {"Node": sel, "Data": []}
        self.update_list_widget()

    def update_vertex_data(self):
        list_vertex = cmds.ls(sl=1, fl=1)
        if not any(".vtx" in str(v) for v in list_vertex):
            return

        keys = [item.text() for item in self.ui.listWidget_target.selectedItems()]
        if not keys:
            return

        self.DICT_TARGET[keys[0]]["Data"] = list_vertex
        idx = self.ui.listWidget_target.currentRow()
        self.update_list_widget()
        self.ui.listWidget_target.setCurrentRow(idx + 1)

    def update_list_widget(self):
        self.ui.listWidget_target.clear()
        self.ui.listWidget_target.addItems(self.DICT_TARGET.keys())
        for i in range(self.ui.listWidget_target.count()):
            item = self.ui.listWidget_target.item(i)
            if self.DICT_TARGET[item.text()]["Data"]:
                item.setBackground(QtGui.QBrush(QtGui.QColor("green")))

    # Quick Data
    def reload_quick_data_folder(self):
        quick_data_path = QuickData.get_quick_data_dir()
        if quick_data_path:
            self.ui.lineEdit_quick_data_dir.setText(quick_data_path)
            self.ui.groupBox_import_local_rig.setEnabled(True)
        else:
            self.ui.lineEdit_quick_data_dir.setText("")
            self.ui.groupBox_import_local_rig.setEnabled(False)
        return quick_data_path

    def create_quick_data_folder(self):
        current_file_path = cmds.file(q=True, sn=True)
        if not current_file_path:
            cmds.confirmDialog(m="Please save this file before create quick data.")
            return
        dir_path = os.path.dirname(current_file_path)
        for folder in ["QuickData/Python", "QuickData/Skin", "QuickData/Controller"]:
            full_path = os.path.join(dir_path, folder)
            if not os.path.exists(full_path):
                os.makedirs(full_path)
        self.reload_quick_data_folder()

    def load_source_combine_weight(self):
        selection = cmds.ls(sl=1)
        self.list_combine_weight_source = selection
        self.ui.lineEdit_source_to_combine.setText(str(selection))

    def load_target_combine_weight(self):
        selection = cmds.ls(sl=1)
        self.list_combine_weight_target = selection
        self.ui.lineEdit_target_to_combine.setText(str(selection))

    def browse_current(self):
        self.local_rig_file_path = cmds.file(q=True, sn=True)
        self.local_rig_file_name_only = os.path.splitext(
            os.path.basename(self.local_rig_file_path)
        )[0]
        self.ui.lineEdit_local_rig_browse.setText(self.local_rig_file_name_only)
        self.create_json_rig_data()

    def get_vertex_positions(self, obj_name):
        shapes = cmds.listRelatives(obj_name, s=True, f=True)
        target = shapes[0] if shapes else obj_name
        vtx_count = cmds.polyEvaluate(target, v=True)
        positions = []
        for i in range(vtx_count):
            p = cmds.xform("{}.vtx[{}]".format(target, i), q=True, os=True, t=True)
            positions.append((p[0], p[1], p[2]))
        return positions

    @uitools.undoable
    def apply_corrective_shape(self, selected=False):
        list_target_key = (
            [
                item.text()
                for item in self.ui.listWidget_target_corrective.selectedItems()
            ]
            if selected
            else self.dict_target_corrective.keys()
        )
        base_shape = self.get_shape_orig()
        vtxs_base = self.get_vertex_positions(base_shape)

        for sel in list_target_key:
            full_shape = "{}_FullShape".format(sel)
            pose_shape = "{}_PoseShape".format(sel)
            if not cmds.objExists(full_shape):
                continue

            vtxs_weight = self.get_vertex_positions(pose_shape)
            vtxs_target = self.get_vertex_positions(full_shape)

            for i in range(len(vtxs_target)):
                # target - weight + base
                rx = vtxs_target[i][0] - vtxs_weight[i][0] + vtxs_base[i][0]
                ry = vtxs_target[i][1] - vtxs_weight[i][1] + vtxs_base[i][1]
                rz = vtxs_target[i][2] - vtxs_weight[i][2] + vtxs_base[i][2]
                cmds.xform("{}.vtx[{}]".format(sel, i), os=True, t=(rx, ry, rz))

        cmds.delete(base_shape)
        self.show_base_mesh()

    def show_base_mesh(self):
        grp = self.get_corrective_grp()
        if cmds.objExists(grp):
            for child in cmds.listRelatives(grp, c=True, f=True) or []:
                cmds.setAttr(child + ".v", False)
        self.ui.listWidget_target_corrective.clearSelection()
        if cmds.objExists(self.base_mesh):
            cmds.setAttr(self.base_mesh + ".v", True)

    def get_corrective_grp(self):
        return "{}_Corrective_Grp".format(self.blend_shape_node)

    def get_shape_orig(self, name="base_shape"):
        obj = cmds.duplicate(self.base_mesh, n=name)[0]
        if cmds.listRelatives(obj, p=True):
            cmds.parent(obj, w=True)
        shapes = cmds.listRelatives(obj, s=True, f=True)
        for s in shapes:
            if "Orig" not in s:
                cmds.delete(s)
            else:
                cmds.setAttr(s + ".intermediateObject", False)
        return obj

    @uitools.undoable
    def apply_rename(self):
        # Sort nodes by string length (descending)
        # This ensures we rename children (|group|child) before parents (|group)
        # to avoid breaking the path to the children.
        sorted_nodes = sorted(self.dict_rename_output.keys(), key=len, reverse=True)

        for node in sorted_nodes:
            new_name = self.dict_rename_output[node]

            # Check if the node exists before renaming
            if cmds.objExists(node):
                try:
                    cmds.rename(node, new_name)
                except Exception as e:
                    cmds.warning("Failed to rename {}: {}".format(node, e))

        # Feedback to user
        cmds.inViewMessage(amg="<hl>Rename Apply</hl>", pos="botCenter", fade=True)

    # set attribute function -------------------------------------
    def update_attribute_target(self):
        ######################################
        # update target node in list widget ##
        ######################################

        list_set_attribute_target = cmds.ls(sl=1)

        # update target node list
        self.ui.listWidget_node.clear()
        self.ui.listWidget_node.addItems(
            [str(Utility.cut(node)) for node in list_set_attribute_target]
        )

        #######################################
        # update search attribute name list ###
        #######################################

        attr = [item.text() for item in self.ui.listWidget_attribute.selectedItems()]

        print("attrs : ", attr)
        if not attr:
            return
        else:
            attr = attr[0]

        attr_type = None
        for node in list_set_attribute_target:
            attr_path = "{}.{}".format(node, attr)
            attr_obj = cmds.Attribute(attr_path)

            # Query the type of the attribute
            attr_type = attr_obj.type()

            print("attr_type : ", attr_type)

        if not attr_type or attr_type == "None":
            return

        if attr_type == "bool":
            self.ui.tabWidget_set_attribute_by_type.setCurrentIndex(0)

        elif (
            attr_type == "float"
            or attr_type == "double"
            or attr_type == "doubleLinear"
            or attr_type == "doubleAngle"
        ):
            self.ui.doubleSpinBox_float.setValue(cmds.getAttr(attr_path))
            self.ui.tabWidget_set_attribute_by_type.setCurrentIndex(1)

        elif attr_type == "int":
            self.ui.spinBox_int.setValue(cmds.getAttr(attr_path))
            self.ui.tabWidget_set_attribute_by_type.setCurrentIndex(2)

        elif attr_type == "matrix":
            self.ui.tabWidget_set_attribute_by_type.setCurrentIndex(3)

            matrix = cmds.getAttr(attr_path)
            self.ui.plainTextEdit_matrix_set.setPlainText(str(matrix))

        elif attr_type == "enum":
            self.ui.tabWidget_set_attribute_by_type.setCurrentIndex(4)

            enumStr = cmds.attributeQuery(
                attr, node=list_set_attribute_target[0], listEnum=True
            )[0]
            enumValues = enumStr.split(":")

            self.ui.comboBox_set_attribute_enum.clear()
            self.ui.comboBox_set_attribute_enum.addItems(enumValues)

            self.ui.comboBox_set_attribute_enum.setCurrentIndex(cmds.getAttr(attr_path))
        else:
            self.ui.tabWidget_set_attribute_by_type.setCurrentIndex(5)

        ##########################################
        # update_search_attribute_list_widget ####
        ##########################################

        def get_search_output(objs):
            if not objs:
                return []

            # Get all attribute long names of the first object
            list_attrs = []

            for i, obj in enumerate(objs):
                obj_attrs = cmds.listAttr(obj)
                list_attrs.append(obj_attrs)

            mutual_attrs = set.intersection(*map(set, list_attrs))
            mutual_attrs = sorted(mutual_attrs)

            # get search result
            search_term = self.ui.lineEdit_search_attribute.text()

            if search_term:
                list_regular_search = []
                list_quick_search = []

                for attr in mutual_attrs:
                    if search_term.lower() == Utility.to_abbreviation_case(attr):
                        list_quick_search.append(attr)
                    elif search_term.lower() in attr.lower():
                        list_regular_search.append(attr)

                mutual_attrs = list_quick_search + list_regular_search

            return mutual_attrs

        """Updates the textScrollList with attributes that contain the search term."""
        self.ui.listWidget_attribute.clear()

        list_search_attr = get_search_output(list_set_attribute_target)

        self.ui.listWidget_attribute.addItems(list_search_attr)
        self.ui.listWidget_attribute.setCurrentRow(0)

    @uitools.undoable
    def set_attribute(self, value, typ="float"):
        """Retrieves the selected attribute and value from the UI and applies it."""
        attr = self.get_current_selected_module_name_single()

        for node in list_set_attribute_target:
            try:
                attr_path = "{}.{}".format(node, attr)

                if typ == "float" or typ == "enum" or typ == "int":
                    cmds.setAttr(attr_path, value)

                elif typ == "matrix":
                    value = ast.literal_eval(value)

                    matrix = [elem for row in value for elem in row]

                    if attr == "matrix" or attr == "worldMatrix":
                        cmds.xform(node, ws=1, m=matrix)
                    else:
                        cmds.setAttr(attr_path, matrix, typ="matrix")

            except Exception as e:
                cmds.displayWarning(
                    "Cannot Set Attribute for {}.{} : {}".format(node, attr, e)
                )

    def get_current_selected_module_name_single(self):
        list_item_name = self.get_current_selected_module_name()

        if list_item_name:
            return list_item_name[0]
        else:
            return

    def get_current_selected_module_name(self):
        return [item.text() for item in self.ui.listWidget_attribute.selectedItems()]

    # Snap to vertex funcion
    def remove_all(self):
        self.ui.listWidget_target.clear()
        self.DICT_TARGET = {}

    @uitools.undoable
    def snap_joint_position(self):
        for target_name in self.DICT_TARGET.keys():
            target_node = self.DICT_TARGET[target_name]["Node"]
            vertex_target = self.DICT_TARGET[target_name]["Data"]

            if not vertex_target:
                continue

            Transform.transform_to_vertex(
                target_object=target_node, list_vertex=vertex_target
            )

        cmds.inViewMessage(
            amg="Snap All to selected vertex", pos="midCenter", fade=True
        )

    def update_snap_object_list_widget(self):
        selection = cmds.ls(sl=1)

        if selection:
            single = selection[0]
        else:
            return

        try:
            for i in range(self.ui.listWidget_target.count()):
                item = self.ui.listWidget_target.item(i)
                item_text = item.text()

                if item_text == single:
                    self.ui.listWidget_target.setItemSelected(item, True)
                else:
                    pass
        except:
            pass

    def add_object_snap_target(self):
        selection = cmds.ls(sl=1, typ="transform")

        for sel in selection:
            sel_name = Utility.cut(str(sel))

            if sel_name not in self.DICT_TARGET.keys():
                self.DICT_TARGET[sel_name] = {"Node": sel, "Data": []}

        self.update_list_widget()

        # select new one
        list_widget = self.ui.listWidget_target
        (
            list_widget.setCurrentRow(list_widget.count() - 1)
            if list_widget.count()
            else None
        )

    def update_vertex_data(self):
        list_vertex = cmds.ls(sl=1, fl=1)

        for vertex in list_vertex:
            if ".vtx" not in str(vertex):
                return

        keys = [item.text() for item in self.ui.listWidget_target.selectedItems()]

        if keys:
            key = keys[0]
        else:
            return

        self.DICT_TARGET[key]["Data"] = list_vertex

        current_index = self.ui.listWidget_target.currentRow()

        self.update_list_widget()

        self.ui.listWidget_target.setCurrentRow(current_index + 1)

    def update_list_widget(self):
        self.ui.listWidget_target.clear()
        self.ui.listWidget_target.addItems(self.DICT_TARGET)

        # update color
        for i in range(self.ui.listWidget_target.count()):
            item = self.ui.listWidget_target.item(i)
            item_text = item.text()

            if self.DICT_TARGET[item_text]["Data"]:
                item.setBackground(QtGui.QBrush(QtGui.QColor("green")))

    # Quick Data
    def reload_quick_data_folder(self):
        quick_data_path = QuickData.get_quick_data_dir()

        if quick_data_path:
            self.ui.lineEdit_quick_data_dir.setText(quick_data_path)
            self.ui.groupBox_import_local_rig.setEnabled(True)

        else:
            self.ui.lineEdit_quick_data_dir.setText("")
            self.ui.groupBox_import_local_rig.setEnabled(False)

        return quick_data_path

    def create_quick_data_folder(self):
        current_file_path = cmds.sceneName()

        if not current_file_path:
            cmds.confirmDialog(m="Please save this file before create quick data.")
            return

        dir_path = os.path.dirname(current_file_path)

        # Define the subfolder structure
        subfolders = ["QuickData/Python", "QuickData/Skin", "QuickData/Controller"]

        # Create folders
        for folder in subfolders:
            full_path = os.path.join(dir_path, folder)
            os.makedirs(full_path, exist_ok=True)

        self.reload_quick_data_folder()

    def transfer_to_combine(self):
        combine_mesh = self.list_combine_weight_target[0]
        combine_shape = cmds.listRelatives(combine_mesh, c=1, s=1)[0]

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
                    cmds.skinCluster(
                        node_combine_skin_cluster,
                        edit=True,
                        addInfluence=joint,
                        weight=0.0,
                    )
                except:
                    pass

        else:
            node_combine_skin_cluster = cmds.skinCluster(
                list_add_influences, combine_mesh, tsb=True
            )

        # transfer weight
        for ref_mesh in self.list_combine_weight_source:
            dict_pair_vertex = dict_match_vertex[str(ref_mesh)]
            target_skinCluster = SkinWeight.get_skin_cluster_node(ref_mesh)

            print("target skin cluster : ", ref_mesh, target_skinCluster)

            for ref_vtx, combine_vtx in dict_pair_vertex.items():

                print("combine vertex : ")
                influences = cmds.skinPercent(target_skinCluster, ref_vtx, q=1, t=None)
                values = cmds.skinPercent(
                    target_skinCluster, ref_vtx, query=True, value=True
                )

                print("vtx infs,values : ", influences, values)

                dict_weight = dict(zip(influences, values))

                for influence, value in dict_weight.items():
                    cmds.skinPercent(
                        node_combine_skin_cluster,
                        combine_vtx,
                        transformValue=[(influence, value)],
                    )

    def load_source_combine_weight(self):
        selection = cmds.ls(sl=1)
        self.list_combine_weight_source = selection
        self.ui.lineEdit_source_to_combine.setText(str([str(sel) for sel in selection]))

    def load_target_combine_weight(self):
        selection = cmds.ls(sl=1)
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
        self.local_rig_file_path = cmds.sceneName()
        self.local_rig_file_name_only = os.path.splitext(
            os.path.basename(self.local_rig_file_path)
        )[0]

        # update widget
        self.ui.lineEdit_local_rig_browse.setText(self.local_rig_file_name_only)

        self.create_json_rig_data()

    def browse_local_rig(self):
        scene_path = cmds.sceneName()
        default_dir = (
            os.path.dirname(scene_path)
            if scene_path
            else cmds.workspace(q=True, rootDirectory=True)
        )

        file_path = cmds.fileDialog2(
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

    def add_blend_shape_chain(self):
        dict_data = File.load_json_file_to_dict(self.local_rig_file_json)

        list_geo_group = [dict_data["mesh_parent"][0]]
        geo_key_name = dict_data["geo_key_name"]

        BlendShape.add_multi_local_blendshape(
            list_geo_group=list_geo_group, geo_key_name=geo_key_name
        )

    def create_operated_corrective_shape(
        object_base="base",
        object_weight="weight",
        object_target="target",
        object_result="max_model_v008_body1",
    ):

        def get_vertex_positions_from_duplicate(obj_name):
            """Duplicate an object, get its vertex positions, then delete the duplicate."""
            dup = cmds.duplicate(obj_name, name="tmp_vtx_extract")[0]
            positions = {}
            vtx_count = cmds.polyEvaluate(dup, vertex=True)

            for i in range(vtx_count):
                pos = cmds.xform(f"{dup}.vtx[{i}]", q=1, os=1, t=True)
                positions[i] = tuple(pos)

            cmds.delete(dup)  # delete the temporary duplicate
            return positions

        def vector_list_operation(list1, list2, operation="add"):
            """
            Perform element-wise addition or subtraction between
            two lists of 3D vectors.

            Args:
                list1 (list of tuple): List of (x, y, z) vectors.
                list2 (list of tuple): List of (x, y, z) vectors.
                operation (str): 'add' or 'sub'.

            Returns:
                list of tuple: Resulting list of (x, y, z) vectors.
            """
            if len(list1) != len(list2):
                raise ValueError(
                    f"List lengths must match. Got {len(list1)} vs {len(list2)}."
                )

            results = []
            for v1, v2 in zip(list1, list2):
                if len(v1) != 3 or len(v2) != 3:
                    raise ValueError("All vectors must be 3D tuples/lists.")
                if operation == "add":
                    results.append((v1[0] + v2[0], v1[1] + v2[1], v1[2] + v2[2]))
                elif operation == "sub":
                    results.append((v1[0] - v2[0], v1[1] - v2[1], v1[2] - v2[2]))
                else:
                    raise ValueError("Operation must be 'add' or 'sub'.")
            return results

        vtxs_base = get_vertex_positions_from_duplicate("base").values()
        vtxs_weight = get_vertex_positions_from_duplicate("weight").values()
        vtxs_target = get_vertex_positions_from_duplicate("target").values()

        # get list result
        vtxs_result = vector_list_operation(vtxs_target, vtxs_weight, "sub")
        vtxs_result = vector_list_operation(vtxs_result, vtxs_base, "add")

        for i, pos in enumerate(vtxs_result):
            cmds.xform("{}.vtx[{}]".format(object_result, i), os=1, t=pos)

    def convert_full_to_corrective_shape(
        object_base="base",
        object_weight="weight",
        object_target="target",
        object_result="max_model_v008_body1",
    ):
        """
        Convert Full Shape (regular blend shape mesh) to Corrective Shape (Shape that append to pose shape )

        """

        vtxs_base = get_vertex_positions_from_duplicate(object_base).values()
        vtxs_weight = get_vertex_positions_from_duplicate(object_weight).values()
        vtxs_target = get_vertex_positions_from_duplicate(object_target).values()

        # get list result
        vtxs_result = vector_list_operation(vtxs_target, vtxs_weight, "sub")
        vtxs_result = vector_list_operation(vtxs_result, vtxs_base, "add")

        for i, pos in enumerate(vtxs_result):
            cmds.xform("{}.vtx[{}]".format(object_result, i), os=1, t=pos)

    def get_vertex_positions_from_duplicate(obj_name):
        print("object name : ", obj_name)

        # get shape from given name
        shape = cmds.listRelatives(obj_name, c=1, s=1)[0]

        # get vertex count
        vtx_count = cmds.polyEvaluate(shape, vertex=True)

        # query postion
        positions = {}
        for i in range(vtx_count):
            pos = cmds.xform("{}.vtx[{}]".format(shape, i), q=1, os=1, t=True)
            positions[i] = tuple(pos)

        return positions

    def vector_list_operation(list1, list2, operation="add"):
        """
        Perform element-wise addition or subtraction between
        two lists of 3D vectors.

        Args:
            list1 (list of tuple): List of (x, y, z) vectors.
            list2 (list of tuple): List of (x, y, z) vectors.
            operation (str): 'add' or 'sub'.

        Returns:
            list of tuple: Resulting list of (x, y, z) vectors.
        """
        if len(list1) != len(list2):
            raise ValueError(
                f"List lengths must match. Got {len(list1)} vs {len(list2)}."
            )

        results = []
        for v1, v2 in zip(list1, list2):
            if len(v1) != 3 or len(v2) != 3:
                raise ValueError("All vectors must be 3D tuples/lists.")
            if operation == "add":
                results.append((v1[0] + v2[0], v1[1] + v2[1], v1[2] + v2[2]))
            elif operation == "sub":
                results.append((v1[0] - v2[0], v1[1] - v2[1], v1[2] - v2[2]))
            else:
                raise ValueError("Operation must be 'add' or 'sub'.")
        return results

    def exit_isolate(self):
        cmds.isolateSelect("modelPanel4", state=False)

        self.grp_data.visibility.set(False)

        cmds.select(cl=True)

    def isolate_object(self, obj):
        self.grp_data.visibility.set(True)

        cmds.select(obj)
        cmds.setAttr("{}.v".format(obj), True)

        # # Get the panel that currently has focus
        # current_panel = cmds.getPanel(wf=True)
        # panel_type = cmds.getPanel(to=current_panel)

        # # Only run if it's a viewport (modelPanel)
        # if panel_type == "modelPanel":
        #     is_on = cmds.isolateSelect(current_panel, q=True, s=True)
        #     cmds.enableIsolateSelect(current_panel, not is_on)

        return

    def load_shape(self, shape):

        selection = cmds.ls(sl=1)

        if selection:

            mesh = selection[0]

            # # raise error if mesh
            # if "|" in str(mesh):
            #     cmds.error("{} is too many object with duplicate name".format(mesh))
            #     return

        else:
            mesh = ""

        if shape == "LeftCtrl":
            if mesh == "":
                self.leftCtrl = mesh
            else:
                self.leftCtrl = mesh.shortName()

            self.ui.pushButton_select_left_ctrl.setText(self.leftCtrl)
            cmds.setAttr("{}.leftCtrl".format(self.grp_data), self.leftCtrl)

        elif shape == "RightCtrl":
            if mesh == "":
                self.rightCtrl = mesh
            else:
                self.rightCtrl = mesh.shortName()

            self.ui.pushButton_select_right_ctrl.setText(self.rightCtrl)
            cmds.setAttr("{}.rightCtrl".format(self.grp_data), self.rightCtrl)

        elif shape == "Up":
            if mesh == "":
                self.shape_Up = mesh
            else:
                self.shape_Up = mesh.shortName()

            self.ui.pushButton_select_shape_up.setText(self.shape_Up)
            cmds.setAttr("{}.up".format(self.grp_data), self.shape_Up)

        elif shape == "Down":
            if mesh == "":
                self.shape_Down = mesh
            else:
                self.shape_Down = mesh.shortName()

            self.ui.pushButton_select_shape_down.setText(self.shape_Down)
            cmds.setAttr("{}.down".format(self.grp_data), self.shape_Down)

        elif shape == "In":
            if mesh == "":
                self.shape_In = mesh
            else:
                self.shape_In = mesh.shortName()

            self.ui.pushButton_select_shape_in.setText(self.shape_In)
            cmds.setAttr("{}.in".format(self.grp_data), self.shape_In)

        elif shape == "Out":
            if mesh == "":
                self.shape_Out = mesh
            else:
                self.shape_Out = mesh.shortName()

            self.ui.pushButton_select_shape_out.setText(self.shape_Out)
            cmds.setAttr("{}.out".format(self.grp_data), self.shape_Out)

        elif shape == "OutUp":
            if mesh == "":
                self.shape_OutUp = mesh
            else:
                self.shape_OutUp = mesh.shortName()

            self.ui.pushButton_select_shape_outUp.setText(self.shape_OutUp)
            cmds.setAttr("{}.outUp".format(self.grp_data), self.shape_OutUp)

        elif shape == "OutDown":
            if mesh == "":
                self.shape_OutDown = mesh
            else:
                self.shape_OutDown = mesh.shortName()

            self.ui.pushButton_select_shape_outDown.setText(self.shape_OutDown)
            cmds.setAttr("{}.outDown".format(self.grp_data), self.shape_OutDown)

        elif shape == "InUp":
            if mesh == "":
                self.shape_InUp = mesh
            else:
                self.shape_InUp = mesh.shortName()

            self.ui.pushButton_select_shape_inUp.setText(self.shape_InUp)
            cmds.setAttr("{}.inUp".format(self.grp_data), self.shape_InUp)

        elif shape == "InDown":
            if mesh == "":
                self.shape_InDown = mesh
            else:
                self.shape_InDown = mesh.shortName()

            self.ui.pushButton_select_shape_inDown.setText(self.shape_InDown)
            cmds.setAttr("{}.inDown".format(self.grp_data), self.shape_InDown)

    @uitools.undoable
    def create_or_select_weight_split(self):
        if not self.base_mesh:
            cmds.warning("require base shape mesh to create weight split")
            return

        if cmds.objExists(self.weight_mesh):
            cmds.select(self.weight_mesh)

            cmds.inViewMessage(
                amg="<hl> Select Weight Split Mesh</hl>",
                pos="botCenter",
                fit=20,
                fts=16,
                fade=True,
            )

        else:
            # create object
            print(self.base_mesh)
            cmds.duplicate(self.base_mesh, n=self.weight_mesh)[0]

            jnt_left = cmds.createNode("joint", n="jnt_split_L")
            jnt_right = cmds.createNode("joint", n="jnt_split_R")

            cmds.parent(jnt_left, jnt_right, self.grp_data)

            try:
                cmds.parent(self.weight_mesh, self.grp_data)
            except:
                pass

            cmds.xform(jnt_left, t=(1, 1, 1), ws=1)
            cmds.xform(jnt_right, t=(-1, 1, 1), ws=1)

            # bind skin
            cmds.skinCluster(jnt_left, jnt_right, self.weight_mesh, bm=1)

            self.ui.lineEdit_weight_split.setText(self.weight_mesh)

            cmds.select(self.weight_mesh)

            cmds.inViewMessage(
                amg="<hl> Create New Split Mesh</hl>",
                pos="botCenter",
                fit=20,
                fts=16,
                fade=True,
            )

    @uitools.undoable
    def build_split(self):
        list_split_mesh = cmds.ls(sl=1)

        if not list_split_mesh:
            cmds.warning("Select Meshes Target for split first.")
        elif cmds.objExists(self.weight_mesh):

            # Launch loading screen
            factor = 100 / len(list_split_mesh)
            amount = 0
            cmds.progressWindow(
                title="Doing Nothing",
                progress=amount,
                status="Preparing: 0%",
                isInterruptable=True,
            )

            # update weight data to json
            cmds.select(self.weight_mesh)
            QuickData.export_skin_quick()

            # get weight data
            quick_data_path = QuickData.get_quick_data_dir()
            json_path = os.path.join(
                quick_data_path, "Skin", "{}.json".format(self.weight_mesh)
            )

            # check is path exist
            if not os.path.exists(json_path):
                cmds.error("Please Export Skin of {} First.".format(self.weight_mesh))

            # load json data
            dict_data = File.load_json_file_to_dict(json_path)

            # create splited shape
            output = []
            for i, shape in enumerate(list_split_mesh):
                # update progress
                amount += i * factor
                cmds.progressWindow(
                    edit=True,
                    progress=amount,
                    status=(
                        "Spliting {}/{} : {}".format(i + 1, len(list_split_mesh), shape)
                    ),
                )

                # split shape
                each_output = BlendShape.split_blendshape(
                    L_joint="jnt_split_L",
                    R_joint="jnt_split_R",
                    split_weight_mesh=self.weight_mesh,
                    base_mesh=self.base_mesh,
                    target_mesh=shape,
                    custom_weight_data=dict_data,
                )

                output += each_output

            # try to parent output to world
            try:
                cmds.parent(output, w=1)
            except:
                pass

            cmds.select(output)

            # close progress window
            cmds.progressWindow(endProgress=1)

            # display
            cmds.inViewMessage(
                amg="<hl> Split Complete!</hl>",
                pos="botCenter",
                fit=20,
                fts=16,
                fade=True,
            )

        else:
            cmds.warning("Required Weight Mesh Created")

    def select_node(self):
        if self.blend_shape_node and cmds.objExists(self.blend_shape_node):
            cmds.select(self.blend_shape_node)

            cmds.inViewMessage(
                amg="<hl>Select Blend Shape Node</hl>", pos="midCenter", fade=True
            )

    def select_data_grp(self):
        if self.grp_data:
            cmds.select(self.grp_data)

            cmds.inViewMessage(
                amg="<hl>Select Grp Data </hl>", pos="midCenter", fade=True
            )

    def create_grp_data_attribute(self):
        cmds.addAttr(self.grp_data, ln="baseMesh", dt="string", k=True)
        cmds.addAttr(self.grp_data, ln="shapeMeshes", dt="stringArray", k=True)

        cmds.addAttr(self.grp_data, ln="leftCtrl", dt="string", k=True)
        cmds.addAttr(self.grp_data, ln="rightCtrl", dt="string", k=True)

        cmds.addAttr(self.grp_data, ln="up", dt="string", k=True)
        cmds.addAttr(self.grp_data, ln="down", dt="string", k=True)
        cmds.addAttr(self.grp_data, ln="in", dt="string", k=True)
        cmds.addAttr(self.grp_data, ln="out", dt="string", k=True)

        cmds.addAttr(self.grp_data, ln="outUp", dt="string", k=True)
        cmds.addAttr(self.grp_data, ln="outDown", dt="string", k=True)
        cmds.addAttr(self.grp_data, ln="inUp", dt="string", k=True)
        cmds.addAttr(self.grp_data, ln="inDown", dt="string", k=True)

    def select_item_by_name(self, name):
        list_widget = self.ui.listWidget_target_corrective

        """Selects the item in a QListWidget that matches the given name."""
        matches = list_widget.findItems(name, QtCore.Qt.MatchExactly)
        if matches:
            list_widget.setCurrentItem(matches[0])
            return True
        return False

    def load_base_mesh(self, mesh_corrective=None):
        if mesh_corrective:
            selection = [mesh_corrective]
        elif not mesh_corrective:
            selection = cmds.ls(sl=1)

        if not selection or len(selection) == 0:
            cmds.inViewMessage(amg="Found", pos="midCenter", fade=True)

            return

        # assign grp data
        self.grp_data = "{}_{}".format(selection[0], self.grp_data_keyword)

        if cmds.objExists(self.grp_data):
            cmds.warning("You Already have {} in the scene".format(self.grp_data))
            return

        # recheck input
        if (
            len(selection) != 1
            or cmds.listRelatives(selection, c=1, typ="mesh") is None
        ):
            self.base_mesh = None
            self.ui.lineEdit_base_mesh.setText("")
            self.ui.lineEdit_blend_shape_node.setText("")

            return

        self.base_mesh = selection[0]

        # reset dict corrective
        self.dict_target_corrective = {}
        self.ui.listWidget_target_corrective.clear()

        self.blend_shape_node = BlendShape.get_blendshape_node(self.base_mesh)

        # update blend shape variables and widget
        if not self.blend_shape_node:
            result = cmds.confirmDialog(
                m="Blend shape node not exist. Create new one?",
                button=["Create New", "Cancel"],
                defaultButton="Create New",
                cancelButton="Cancel",
                dismissString="Cancel",
            )

            if result == "Create New":
                result = cmds.promptDialog(
                    title="Create New Corrective Blend Shape",
                    message="Enter Blend Shape Node Name:",
                    button=["OK", "Cancel"],
                    defaultButton="OK",
                    cancelButton="Cancel",
                    dismissString="Cancel",
                    tx="corrective_blendShape",
                )

                if result == "OK":
                    text = cmds.promptDialog(query=True, text=True)
                    self.blend_shape_node = cmds.blendShape(
                        self.base_mesh, n=text, at=True
                    )[0]
                    cmds.inViewMessage(
                        amg="Created new blendShape : {}".format(self.blend_shape_node),
                        pos="midCenter",
                        fade=True,
                    )

                else:
                    return

            elif result == "Cancel":
                self.ui.lineEdit_blend_shape_node.setText("")
                self.ui.lineEdit_base_mesh.setText("")

                return

        if self.blend_shape_node:
            self.ui.lineEdit_blend_shape_node.setText(str(self.blend_shape_node))
            self.ui.lineEdit_base_mesh.setText(str(self.base_mesh))

            self.load_list_target_from_exist_group()

            # display base mesh
            self.show_base_mesh()

        self.ui.lineEdit_base_mesh.setText(str(self.base_mesh))

        # create group data
        cmds.group(em=1, n=self.grp_data)
        self.create_grp_data_attribute()

        cmds.setAttr(
            "{}.{}".format(self.grp_data, "baseMesh"), str(self.base_mesh), typ="string"
        )

    def load_list_target_from_exist_group(self):
        # find exist full shape grp
        if not cmds.objExists("{}_Corrective_Grp".format(self.blend_shape_node)):
            return

        # reset dict corrective
        self.dict_target_corrective = {}
        self.ui.listWidget_target_corrective.clear()

        # update dict target corrective
        for obj in cmds.listRelatives(self.get_corrective_grp(), c=1):
            if not "_FullShape" in str(obj):
                continue

            self.dict_target_corrective[str(obj).replace("_FullShape", "")] = obj

        # debug
        self.ui.listWidget_target_corrective.addItems(
            [str(target) for target in self.dict_target_corrective.keys()]
        )

    def text_to_dict(self, text):
        return ast.literal_eval("{" + text + "}")

    def reset_pose(self):
        """Reset all controller transform"""
        for shape in self.dict_target_corrective:
            full_shape_mesh = "{}_FullShape".format(shape)

            # set pose from pose data
            list_array_text = cmds.getAttr("{}.controller_data".format(full_shape_mesh))

            if not list_array_text:
                continue

            for text_data in list_array_text:
                dict_data = self.text_to_dict(text_data)

                controller = list(dict_data.keys())[0]

                translate, rotate, scale = [(0, 0, 0), (0, 0, 0), (1, 1, 1)]

                # is controller exist
                if not cmds.objExists(controller):
                    continue

                # set transform
                for attr_name, values in [
                    ("t", translate),
                    ("r", rotate),
                    ("s", scale),
                ]:
                    for i, axis in enumerate("xyz"):
                        try:
                            cmds.setAttr(f"{controller}.{attr_name}{axis}", values[i])
                        except:
                            pass

        # turn off all blend shape
        for shape in self.dict_target_corrective.keys():
            cmds.setAttr("{}.{}".format(self.blend_shape_node, shape), 0)

        self.show_base_mesh()
        cmds.inViewMessage(amg="Pose Reset", pos="midCenter", fade=True)

    def update_pose_data(self):
        # get dict pose data
        maya_selection = cmds.ls(sl=1)

        dict_pose_data = {}
        list_write_pose_data = []

        for control in maya_selection:
            dict_pose_data[str(control)] = (
                list(control.translate.get()),
                list(control.rotate.get()),
                list(control.scale.get()),
            )

        for key in dict_pose_data.keys():
            transform = dict_pose_data[key]
            list_write_pose_data.append(
                '"{}":({},{},{})'.format(key, transform[0], transform[1], transform[2])
            )

        # update pose to selected full path attribute
        selection = [
            item.text() for item in self.ui.listWidget_target_corrective.selectedItems()
        ]

        if selection:
            full_shape_mesh = selection[0] + "_FullShape"
        else:
            return

        cmds.setAttr(
            "{}.controller_data".format(full_shape_mesh),
            list_write_pose_data,
            typ="stringArray",
        )

        cmds.inViewMessage(
            amg="Pose Data Updated to Shape : {}".format(selection[0]),
            pos="midCenter",
            fade=True,
        )

    def create_full_shape(self, shape_name, source_mesh=None):
        if not source_mesh:
            source_mesh = self.base_mesh

        full_shape_mesh_name = shape_name + "_FullShape"

        full_shape_mesh = cmds.duplicate(source_mesh, n=full_shape_mesh_name)[0]

        # parent to group
        cmds.parent(full_shape_mesh, self.get_corrective_grp())

        # hide
        full_shape_mesh.visibility.set(False)

        # add attribute
        cmds.addAttr(full_shape_mesh, ln="keyframe", at="long", k=1)
        cmds.setAttr(
            "{}.keyframe".format(full_shape_mesh), cmds.currentTime(query=True)
        )

        cmds.addAttr(full_shape_mesh, dt="stringArray", ln="controller_data", k=1)

        return full_shape_mesh

    def create_pose_shape(self, full_shape_mesh):
        # turn blendshape off
        if self.blend_shape_node.envelope.get() == True:
            self.blend_shape_node.envelope.set(False)

        # set current time to match pose
        # cmds.currentTime(cmds.getAttr("{}.keyframe".format(full_shape_mesh)))

        # create pose shape
        pose_shape = cmds.duplicate(
            self.base_mesh, n=full_shape_mesh.replace("_FullShape", "_PoseShape")
        )[0]
        cmds.parent(pose_shape, self.get_corrective_grp())
        pose_shape.visibility.set(False)

        # set blendshape envelope back
        self.blend_shape_node.envelope.set(True)

        return pose_shape

    def create_corrective_grp(self):
        # create group for store data
        if not cmds.objExists(self.get_corrective_grp()):
            cmds.group(em=1, n=self.get_corrective_grp())

    def get_shape_orig(self, name="base_shape"):
        object = cmds.duplicate(self.base_mesh, n=name)[0]

        cmds.parent(object, w=1)

        list_orig_shape = []
        list_delete_shape = []

        list_shape = cmds.listRelatives(object, c=1, s=1, typ="mesh")

        for shape in list_shape:
            if "Orig" not in str(shape):
                cmds.delete(shape)
            else:
                cmds.setAttr("{}.intermediateObject".format(shape), False)

        return object

    @uitools.undoable
    def apply_corrective_shape(self, selected=False):
        """
        Apply Full Shape to Corrective shape
        """

        # get target
        if selected:
            list_target_key = [
                item.text()
                for item in self.ui.listWidget_target_corrective.selectedItems()
            ]
        else:
            list_target_key = self.dict_target_corrective.keys()

        print("Applying All Corrective Shape")

        # create tmp dummy base shape
        base_shape = self.get_shape_orig()
        print("Crated Orig Shape : ", base_shape)

        # operation
        for sel in list_target_key:
            pose_shape_mesh = "{}_PoseShape".format(sel)
            full_shape_mesh = "{}_FullShape".format(sel)

            # skip if pose shape or full shape not found
            if not cmds.objExists(full_shape_mesh):
                continue

            # update pose shape
            if not cmds.objExists(pose_shape_mesh):
                self.create_pose_shape(full_shape_mesh=full_shape_mesh)

            # apply to corrective shape
            print("Applying : ", full_shape_mesh)
            func.convert_full_to_corrective_shape(
                object_base=base_shape,
                object_weight=pose_shape_mesh,
                object_target=full_shape_mesh,
                object_result=sel,
            )

        cmds.delete(base_shape)

        print("Apply Corrective Shape Complete!")

        self.show_base_mesh()

    def get_corrective_grp(self):
        return "{}_Corrective_Grp".format(self.blend_shape_node)

    def show_base_mesh(self):
        # hide all shape
        if cmds.objExists(self.get_corrective_grp()):
            for child in cmds.listRelatives(self.get_corrective_grp(), c=1):
                child.visibility.set(False)

        # clear list widget selection
        self.ui.listWidget_target_corrective.clearSelection()

        # show base mesh
        self.base_mesh.visibility.set(True)

        # select base mesh
        # cmds.select(self.base_mesh)

    def get_list_widget_selection(self):
        selection = [
            item.text() for item in self.ui.listWidget_target_corrective.selectedItems()
        ]

        return selection

    def remove_selected(self):
        selection = self.get_list_widget_selection()

        if not selection:
            return

        for sel in selection:
            full_shape_mesh = "{}_FullShape".format(sel)
            pose_shape_mesh = "{}_PoseShape".format(sel)

            if cmds.objExists(full_shape_mesh):
                cmds.delete(full_shape_mesh)

            if cmds.objExists(pose_shape_mesh):
                cmds.delete(pose_shape_mesh)

        self.load_list_target_from_exist_group()

        # select the last one
        list_widget = self.ui.listWidget_target_corrective
        (
            list_widget.setCurrentRow(list_widget.count() - 1)
            if list_widget.count()
            else None
        )
        self.isolate_full_shape()

        cmds.inViewMessage(amg="Removed", pos="midCenter", fade=True)

    def isolate_full_shape(self):
        print("Isolate Mode")

        selection = self.get_list_widget_selection()

        if not selection:
            return

        full_shape_mesh = selection[0] + "_FullShape"

        # return if not found full shape
        if not cmds.objExists(full_shape_mesh):
            return

        # hide all shape, include base shape
        if cmds.objExists(self.get_corrective_grp()):
            for child in cmds.listRelatives(self.get_corrective_grp(), c=1):
                child.visibility.set(False)

        self.base_mesh.visibility.set(False)

        # set visibility on for selection
        if self.ui.radioButton_edit_mode.isChecked():
            self.ui.pushButton_apply_selected_corrective_shape.setEnabled(True)
            cmds.setAttr("{}.v".format(full_shape_mesh), True)
            cmds.inViewMessage(
                amg="Edit Mode".format(self.blend_shape_node),
                pos="midCenter",
                fade=True,
            )

        else:
            self.ui.pushButton_apply_selected_corrective_shape.setEnabled(False)
            cmds.setAttr("{}.v".format(self.base_mesh), True)
            cmds.inViewMessage(
                amg="Base Shape Display".format(self.blend_shape_node),
                pos="midCenter",
                fade=True,
            )

        # set pose from pose data
        list_array_text = cmds.getAttr("{}.controller_data".format(full_shape_mesh))

        if not list_array_text:
            cmds.warning("Not found Pose Data")
        else:
            for text_data in list_array_text:
                dict_data = self.text_to_dict(text_data)

                controller = list(dict_data.keys())[0]

                translate, rotate, scale = list(dict_data.values())[0]

                # is controller exist
                if not cmds.objExists(controller):
                    continue

                # set transform
                for attr_name, values in [
                    ("t", translate),
                    ("r", rotate),
                    ("s", scale),
                ]:
                    for i, axis in enumerate("xyz"):
                        try:
                            cmds.setAttr(f"{controller}.{attr_name}{axis}", values[i])
                        except:
                            pass

        # set blendshape node
        # set all off
        all_target_name = BlendShape.query_all_blend_shape_input(
            blendshape_name=self.blend_shape_node
        )

        for shape in all_target_name:
            cmds.setAttr("{}.{}".format(self.blend_shape_node, shape), 0)

        # set current on
        cmds.setAttr("{}.{}".format(self.blend_shape_node, selection[0]), 1)

        # selection object
        # if self.ui.radioButton_edit_mode.isChecked():
        #     cmds.select(full_shape_mesh)

    def find_exists_grp_data(self):
        """This function return exist grp data name in the scene"""

        transforms = cmds.ls(typ="transform")

        for transform in transforms:
            if transform.endswith(self.grp_data_keyword):
                return transform

        if not self.grp_data:
            return None

    def refresh(self):
        # find grp exist grp data / only refresh when grp data exist
        self.grp_data = self.find_exists_grp_data()

        if not self.grp_data:
            return

        # update variable
        self.base_mesh = cmds.getAttr(self.grp_data + ".baseMesh")

        self.leftCtrl = cmds.getAttr(self.grp_data + ".leftCtrl")
        self.rightCtrl = cmds.getAttr(self.grp_data + ".rightCtrl")

        self.shape_Up = cmds.getAttr(self.grp_data + ".up")
        self.shape_Down = cmds.getAttr(self.grp_data + ".down")
        self.shape_In = cmds.getAttr(self.grp_data + ".in")
        self.shape_Out = cmds.getAttr(self.grp_data + ".out")

        self.shape_OutUp = cmds.getAttr(self.grp_data + ".outUp")
        self.shape_OutDown = cmds.getAttr(self.grp_data + ".outDown")
        self.shape_InUp = cmds.getAttr(self.grp_data + ".inUp")
        self.shape_InDown = cmds.getAttr(self.grp_data + ".inDown")

        # find blend shape
        self.blend_shape_node = BlendShape.get_blendshape_node(
            self.base_mesh
        ).shortName()
        # print(self.blend_shape_node)
        # update widget
        self.ui.lineEdit_base_mesh.setText(self.base_mesh)
        self.ui.lineEdit_weight_split.setText(self.weight_mesh)
        self.ui.lineEdit_blend_shape_node.setText(self.blend_shape_node)

        # update widget
        self.ui.pushButton_select_left_ctrl.setText(self.leftCtrl)
        self.ui.pushButton_select_right_ctrl.setText(self.rightCtrl)

        self.ui.pushButton_select_shape_up.setText(self.shape_Up)
        self.ui.pushButton_select_shape_down.setText(self.shape_Down)
        self.ui.pushButton_select_shape_in.setText(self.shape_In)
        self.ui.pushButton_select_shape_out.setText(self.shape_Out)

        self.ui.pushButton_select_shape_outUp.setText(self.shape_OutUp)
        self.ui.pushButton_select_shape_outDown.setText(self.shape_OutDown)
        self.ui.pushButton_select_shape_inUp.setText(self.shape_InDown)
        self.ui.pushButton_select_shape_inDown.setText(self.shape_InDown)

    @uitools.undoable
    def update_blend_shape_driver(self):

        if not cmds.objExists(self.weight_mesh):
            cmds.error("Require weight split mesh before update shape driver")
            return

        list_shape_name = [
            "Up",
            "Down",
            "In",
            "Out",
            "OutUp",
            "OutDown",
            "InUp",
            "InDown",
        ]
        shape = [
            self.shape_Up,
            self.shape_Down,
            self.shape_In,
            self.shape_Out,
            self.shape_OutUp,
            self.shape_OutDown,
            self.shape_InUp,
            self.shape_InDown,
        ]

        # recheck the name

        for shape_name, shape in zip(list_shape_name, shape):
            print("shape : ", shape)
            if not shape:
                # use exist if shape is exist
                if cmds.objExists(shape_name):
                    custom_shape = shape_name

                # create new one if shape not exist
                else:
                    custom_shape = cmds.duplicate(self.base_mesh, n=shape_name)

                # update shape to attribute data
                cmds.select(custom_shape)
                self.load_shape(shape=shape_name)

                # parent shape to grp data
                try:
                    cmds.parent(custom_shape, self.grp_data)
                except:
                    pass

        # create split shape
        cmds.select(self.weight_mesh)
        QuickData.export_skin_quick()

        # create splited shape
        list_split_mesh = []

        for name in list_shape_name:
            # check is split name exist
            each_output = BlendShape.split_blendshape(
                L_joint="jnt_split_L",
                R_joint="jnt_split_R",
                split_weight_mesh=self.weight_mesh,
                base_mesh=self.base_mesh,
                target_mesh=name,
                L_keyword="LeftTmp",
                R_keyword="RightTemp",
            )

            L_side_geo, R_side_geo = each_output
            L_side_geo_main, R_side_geo_main = "{}_Left".format(
                name
            ), "{}_Right".format(name)

            if cmds.objExists(L_side_geo_main):
                Utility.morph_shape(L_side_geo, [L_side_geo_main])
                cmds.delete(L_side_geo)
            else:
                cmds.rename(L_side_geo, L_side_geo_main)

            if cmds.objExists(R_side_geo_main):
                Utility.morph_shape(R_side_geo, [R_side_geo_main])
                cmds.delete(R_side_geo)
            else:
                cmds.rename(R_side_geo, R_side_geo_main)

            # add to list
            list_split_mesh.append(L_side_geo_main)
            list_split_mesh.append(R_side_geo_main)

            # set visibility off
            cmds.setAttr("{}.v".format(L_side_geo_main), False)
            cmds.setAttr("{}.v".format(R_side_geo_main), False)

        cmds.select(list_split_mesh)

        # add blend shape
        BlendShape.add_or_create_blend_shape_node_v2(
            list_target_mesh=list_split_mesh,
            input_mesh=self.base_mesh,
            node_name=self.blend_shape_node,
        )

        # parent
        cmds.parent(list_split_mesh, self.grp_data)

        # Connect diagonal
        left_diagonal_transform_name = self.base_mesh + "_LeftDiagonalNode"

        if not cmds.objExists(left_diagonal_transform_name):
            left_diagonal_transform = Connection.set_diagonal_driver(
                transform_name=self.leftCtrl, name_tag=left_diagonal_transform_name
            )

        right_diagonal_transform_name = self.base_mesh + "_RightDiagonalNode"

        if not cmds.objExists(right_diagonal_transform_name):
            right_diagonal_transform = Connection.set_diagonal_driver(
                transform_name=self.rightCtrl, name_tag=right_diagonal_transform_name
            )

        # force connect
        cmds.connectAttr(
            "{}.Up".format(left_diagonal_transform_name),
            "{}.Up_Left".format(self.blend_shape_node),
            f=True,
        )
        cmds.connectAttr(
            "{}.Down".format(left_diagonal_transform_name),
            "{}.Down_Left".format(self.blend_shape_node),
            f=True,
        )
        cmds.connectAttr(
            "{}.In".format(left_diagonal_transform_name),
            "{}.In_Left".format(self.blend_shape_node),
            f=True,
        )
        cmds.connectAttr(
            "{}.Out".format(left_diagonal_transform_name),
            "{}.Out_Left".format(self.blend_shape_node),
            f=True,
        )
        cmds.connectAttr(
            "{}.UpOut".format(left_diagonal_transform_name),
            "{}.OutUp_Left".format(self.blend_shape_node),
            f=True,
        )
        cmds.connectAttr(
            "{}.UpIn".format(left_diagonal_transform_name),
            "{}.InUp_Left".format(self.blend_shape_node),
            f=True,
        )
        cmds.connectAttr(
            "{}.DownOut".format(left_diagonal_transform_name),
            "{}.OutDown_Left".format(self.blend_shape_node),
            f=True,
        )
        cmds.connectAttr(
            "{}.DownIn".format(left_diagonal_transform_name),
            "{}.InDown_Left".format(self.blend_shape_node),
            f=True,
        )

        cmds.connectAttr(
            "{}.Up".format(right_diagonal_transform_name),
            "{}.Up_Right".format(self.blend_shape_node),
            f=True,
        )
        cmds.connectAttr(
            "{}.Down".format(right_diagonal_transform_name),
            "{}.Down_Right".format(self.blend_shape_node),
            f=True,
        )
        cmds.connectAttr(
            "{}.In".format(right_diagonal_transform_name),
            "{}.In_Right".format(self.blend_shape_node),
            f=True,
        )
        cmds.connectAttr(
            "{}.Out".format(right_diagonal_transform_name),
            "{}.Out_Right".format(self.blend_shape_node),
            f=True,
        )
        cmds.connectAttr(
            "{}.UpOut".format(right_diagonal_transform_name),
            "{}.OutUp_Right".format(self.blend_shape_node),
            f=True,
        )
        cmds.connectAttr(
            "{}.UpIn".format(right_diagonal_transform_name),
            "{}.InUp_Right".format(self.blend_shape_node),
            f=True,
        )
        cmds.connectAttr(
            "{}.DownOut".format(right_diagonal_transform_name),
            "{}.OutDown_Right".format(self.blend_shape_node),
            f=True,
        )
        cmds.connectAttr(
            "{}.DownIn".format(right_diagonal_transform_name),
            "{}.InDown_Right".format(self.blend_shape_node),
            f=True,
        )

        return

    def add_current_mesh(self):
        control_selection = cmds.ls(sl=1)

        if not control_selection:
            cmds.inViewMessage(
                amg="Please select controller to set pose", pos="midCenter", fade=True
            )
            return
        # sort mesh that influence to blend shape node
        list_target_mesh = []

        # create new blend shape
        result = cmds.promptDialog(
            title="Create New Shape",
            message="Shape Name:",
            button=["OK", "Cancel"],
            defaultButton="OK",
            cancelButton="Cancel",
            dismissString="Cancel",
            tx="",
        )

        if result == "OK":
            input_name = cmds.promptDialog(query=True, text=True)

            if input_name == "":
                return

        else:
            return

        # ensure corrective grp is created
        self.create_corrective_grp()

        current_mesh = self.get_shape_orig(name=input_name)
        current_mesh.visibility.set(False)
        BlendShape.add_or_create_blend_shape_node([current_mesh], self.blend_shape_node)

        full_shape = self.create_full_shape(
            shape_name=input_name, source_mesh=self.base_mesh
        )
        pose_mesh = self.create_pose_shape(full_shape_mesh=full_shape)

        # create full shape
        for sel in list_target_mesh:
            full_shape_mesh = "{}_FullShape".format(sel)
            pose_shape_mesh = "{}_PoseShape".format(sel)

            # skip if already have full shape
            if cmds.objExists(full_shape_mesh):
                result = cmds.confirmDialog(
                    m="{} Has already created!".format(sel),
                    button=["Overwrite", "Cancel"],
                    defaultButton="Overwrite",
                    cancelButton="Cancel",
                    dismissString="Cancel",
                )

                if result == "Overwrite":
                    cmds.delete(full_shape_mesh)

                    if cmds.objExists(pose_shape_mesh):
                        cmds.delete(full_shape_mesh)

                elif result == "Cancel":
                    continue

            # create full shape
            self.create_full_shape(shape_name=sel)

            # create pose shape
            self.create_pose_shape(full_shape_mesh=full_shape_mesh)

        # reload list widget
        self.load_list_target_from_exist_group()

        # select new one
        list_widget = self.ui.listWidget_target_corrective
        (
            list_widget.setCurrentRow(list_widget.count() - 1)
            if list_widget.count()
            else None
        )

        # update pose data
        cmds.select(control_selection)
        self.update_pose_data()

    def add_exist_mesh(self):
        selection = cmds.ls(sl=1)

        # return if no selection
        if not selection:
            return

        # sort mesh that influence to blendshape node
        list_target_mesh = []

        for sel in selection:
            if cmds.listRelatives(sel, c=1, typ="mesh") is None:
                continue
            else:
                shape_node = cmds.listRelatives(sel, c=1, typ="mesh")[0]
                list_connection = cmds.listConnections(
                    "{}.worldMesh[0]".format(shape_node), d=True
                )

                if self.blend_shape_node in list_connection:
                    list_target_mesh.append(sel)

        if not list_target_mesh:
            return

        # ensure corrective grp is created
        self.create_corrective_grp()

        # create full shape
        for sel in list_target_mesh:
            full_shape_mesh = "{}_FullShape".format(sel)
            pose_shape_mesh = "{}_PoseShape".format(sel)

            # skip if already have full shape
            if cmds.objExists(full_shape_mesh):
                result = cmds.confirmDialog(
                    m="{} Has already created!".format(sel),
                    button=["Overwrite", "Cancel"],
                    defaultButton="Overwrite",
                    cancelButton="Cancel",
                    dismissString="Cancel",
                )

                if result == "Overwrite":
                    cmds.delete(full_shape_mesh)

                    if cmds.objExists(pose_shape_mesh):
                        cmds.delete(full_shape_mesh)

                elif result == "Cancel":
                    continue

            # create full shape
            self.create_full_shape(shape_name=sel)

            # create pose shape
            self.create_pose_shape(full_shape_mesh=full_shape_mesh)

        # reload list widget
        self.load_list_target_from_exist_group()

        # select new one
        list_widget = self.ui.listWidget_target_corrective
        (
            list_widget.setCurrentRow(list_widget.count() - 1)
            if list_widget.count()
            else None
        )

    def load_node_corrective(self):
        return

    def update_mesh_name(self):
        self.mesh_name = self.ui.lineEdit_mesh.text()
