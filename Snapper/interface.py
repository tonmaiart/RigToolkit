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
    Misc,
)

from tmlib.ui import uitools
from tmlib.module.PySide import QtCore, QtGui, QtWidgets, QAction

import os, importlib, webbrowser, inspect, configparser, re, json
from tmlib.ui.interface_template import ToolkitWindow
import xml.etree.ElementTree as ET
import maya.cmds as mc


class MainWindow(ToolkitWindow):
    def __init__(self):
        def create_axis_plane():
            for target in self.DICT_TARGET:
                print(target)

                plane_result = mc.nurbsPlane()
                plane = plane_result[0]
                shape = mc.listRelatives(plane, children=True, shapes=True)[0]
                mc.rename(shape, "AxisPlaneShape")
                mc.parent(shape, "joint1", relative=True, shape=True)
                mc.delete(plane)

        def setAxisDisplay(display=False, allObj=False):
            # if no joints are selected, do it for all the joints in the scene
            # if allObj flag is True then this will toggle the axis display for all objects in the scene, not just joints.
            if not allObj:
                if len(mc.ls(sl=1, type="joint")) == 0:
                    jointList = mc.ls(type="joint")
                else:
                    jointList = mc.ls(sl=1, type="joint")
                # set the displayLocalAxis attribute to what the user specifies.
                for jnt in jointList:
                    mc.setAttr(jnt + ".displayLocalAxis", display)
            else:
                if len(mc.ls(sl=1)) == 0:
                    objList = mc.ls(transforms=1)
                else:
                    objList = mc.ls(sl=1)
                # set the displayLocalAxis attribute to what the user specifies.
                for obj in objList:
                    mc.setAttr(obj + ".displayLocalAxis", display)

        def add_or_snap():

            selection = mc.ls(selection=True)

            if not selection:
                return

            first_item = selection[0]

            # --- Branch Logic ---
            if ".vtx[" in str(first_item):
                # ✅ Vertex/component selection
                self.update_vertex_data()
            else:
                # ✅ Transform/object selection
                self.add_object_snap_target()

        @uitools.undoable
        def create_joint_to_selected():
            list_vertex = mc.ls(selection=True, flatten=True)
            joint = mc.createNode("joint")

            Transform.transform_to_vertex(target_object=joint, list_vertex=list_vertex)

            mc.select(list_vertex)

        # Set-up Interface

        super(MainWindow, self).__init__(os.path.basename(os.path.dirname(__file__)))

        self.DICT_TARGET = {}

        self.ui.pushButton_snap_joint_position.clicked.connect(self.snap_joint_position)

        self.ui.pushButton_add_target.clicked.connect(lambda x: add_or_snap())

        self.ui.pushButton_remove_all.clicked.connect(self.remove_all)

        self.ui.pushButton_axis_on.clicked.connect(
            lambda x: setAxisDisplay(display=True)
        )
        self.ui.pushButton_axis_off.clicked.connect(
            lambda x: setAxisDisplay(display=False)
        )

        self.ui.pushButton_create_axis_plane.clicked.connect(
            lambda x: create_axis_plane()
        )
        self.ui.pushButton_create_joint_to_selected.clicked.connect(
            lambda x: create_joint_to_selected()
        )

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

        mc.inViewMessage(amg="Snap All to selected vertex", pos="midCenter", fade=True)

    def update_snap_object_list_widget(self):
        selection = mc.ls(selection=True)

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
        selection = mc.ls(selection=True, type="transform")

        if not selection:
            return

        # Step 1: Store existing keys
        existing_keys = set(self.DICT_TARGET.keys())

        # Step 2: Add new selections
        for sel in selection:
            sel_name = Utility.cut(str(sel))

            if sel_name not in existing_keys:
                self.DICT_TARGET[sel_name] = {"Node": sel, "Data": []}

        self.update_list_widget()

        # Step 3: Find the newly added items
        new_keys = [key for key in self.DICT_TARGET.keys() if key not in existing_keys]

        # Step 4: Select the first newly added item in the list widget
        if new_keys:
            list_widget = self.ui.listWidget_target

            for i in range(list_widget.count()):
                if list_widget.item(i).text() == new_keys[0]:
                    list_widget.setCurrentRow(i)
                    break

    def update_vertex_data(self):
        list_vertex = mc.ls(selection=True, flatten=True)

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
