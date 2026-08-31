import os
import importlib

import pymeltm.core as pm
import maya.cmds as mc

from tmlib.module.PySide import QtCore
from tmlib.ui import uitools
from tmlib.ui.interface_template import ToolkitWindow

from BeamSmear import function

# launch()/launch_toolkit() only reload this interface module, not its
# sibling function.py -- reload it explicitly so scene-logic edits take
# effect without restarting Maya.
importlib.reload(function)


class MainWindow(ToolkitWindow):
    def __init__(self):
        super(MainWindow, self).__init__(os.path.basename(os.path.dirname(__file__)))

        self.ui.pushButton_create_smear.clicked.connect(self.create_smear)
        self.ui.pushButton_delete_smear.clicked.connect(self.delete_smear)
        self.ui.pushButton_edit_smear_name.clicked.connect(self.edit_smear_name)

        self.ui.pushButton_set_key.clicked.connect(self.set_key)
        self.ui.pushButton_select_blend_shape_node.clicked.connect(
            self.select_blend_shape_node
        )

        self.ui.pushButton_add_active_mesh.clicked.connect(self.add_active_mesh)
        self.ui.pushButton_remove_active_mesh.clicked.connect(self.remove_active_mesh)

        # refresh_current_smear takes an optional snap_key_frame -- connecting
        # it directly would let Qt's arg-count matching feed itemClicked's
        # QListWidgetItem into that param, so wrap it to drop the item.
        self.ui.listWidget_smear_name.itemClicked.connect(
            lambda item: self.refresh_current_smear()
        )
        self.ui.listWidget_active_meshes.itemClicked.connect(self.select_active_mesh)

        self.ui.horizontalSlider_key_opacity.sliderMoved.connect(self.update_opacity)
        self.ui.horizontalSlider_key_opacity.sliderReleased.connect(self.update_opacity)

        mc.scriptJob(event=["timeChanged", self.update_slider], parent=self.objectName())
        mc.scriptJob(
            event=["Undo", self.refresh_smear_list], parent=self.objectName()
        )
        mc.scriptJob(
            event=["Redo", self.refresh_smear_list], parent=self.objectName()
        )

        self.refresh_smear_list()

        if mc.optionVar(q="gpuOverride"):
            self.ui.label_warning.setText(
                "⚠ Turn off Gpu Override for Stable Soft Selection."
            )

    # ------------------------------------------------------------------
    # Smear list
    # ------------------------------------------------------------------

    def get_current_smear_name(self):
        selected = self.ui.listWidget_smear_name.selectedItems()
        return selected[0].text() if selected else None

    def refresh_smear_list(self):
        self.ui.listWidget_smear_name.clear()
        self.ui.listWidget_smear_name.addItems(function.get_all_smear_names())
        self._select_last_smear()
        self.refresh_current_smear()

    def _select_last_smear(self):
        list_widget = self.ui.listWidget_smear_name
        last_index = list_widget.count() - 1
        if last_index >= 0:
            list_widget.setCurrentRow(last_index)

    # ------------------------------------------------------------------
    # Active mesh list + edit mode
    # ------------------------------------------------------------------

    def refresh_current_smear(self, snap_key_frame=None):
        smear_name = self.get_current_smear_name()

        self.ui.listWidget_active_meshes.clear()

        if not smear_name:
            return

        blend_shape_nodes = function.get_blend_shape_nodes_for_smear(smear_name)
        if not blend_shape_nodes:
            return

        active_meshes = function.get_active_meshes(smear_name, blend_shape_nodes)
        if not active_meshes:
            return

        self.ui.listWidget_active_meshes.addItems(active_meshes)

        function.lock_other_smears(smear_name, blend_shape_nodes)
        self.update_slider(smear_name, blend_shape_nodes)
        function.select_nodes(blend_shape_nodes)
        function.enter_edit_mode(smear_name, blend_shape_nodes)

        # Fix Keyframe Viewport bugs: jump the timeline to where this smear
        # actually has influence so the sculpted shape is visible right away.
        if snap_key_frame is None:
            attr = "{}.{}".format(blend_shape_nodes[0], smear_name)
            pm.currentTime(function.get_max_keyframe_time(attr))
        else:
            pm.currentTime(snap_key_frame)

    def update_slider(self, smear_name=None, blend_shape_nodes=None):
        if smear_name is None:
            smear_name = self.get_current_smear_name()
        if blend_shape_nodes is None:
            blend_shape_nodes = function.get_blend_shape_nodes_for_smear(smear_name)

        value = function.get_smear_weight(smear_name, blend_shape_nodes)
        if value is not None:
            self.ui.horizontalSlider_key_opacity.setValue(value * 100)

    def update_opacity(self):
        smear_name = self.get_current_smear_name()
        blend_shape_nodes = function.get_blend_shape_nodes_for_smear(smear_name)

        if not blend_shape_nodes:
            return

        value = self.ui.horizontalSlider_key_opacity.value() * 0.01
        function.set_smear_weight(smear_name, blend_shape_nodes, value)

    def select_active_mesh(self):
        selected_items = self.ui.listWidget_active_meshes.selectedItems()
        pm.select([item.text() for item in selected_items])

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    @uitools.undoable
    def create_smear(self):
        selection = pm.ls(sl=True)
        smear_name = function.create_smear(selection)

        if not smear_name:
            return

        self.ui.listWidget_smear_name.addItem(smear_name)
        self._select_last_smear()
        self.refresh_current_smear()

    @uitools.undoable
    def delete_smear(self):
        smear_name = self.get_current_smear_name()
        if not smear_name:
            return

        blend_shape_nodes = function.get_blend_shape_nodes_for_smear(smear_name)
        function.delete_smear(smear_name, blend_shape_nodes)

        item = self.ui.listWidget_smear_name.currentItem()
        if item:
            self.ui.listWidget_smear_name.takeItem(
                self.ui.listWidget_smear_name.row(item)
            )

        self.refresh_current_smear()

    @uitools.undoable
    def edit_smear_name(self):
        smear_name = self.get_current_smear_name()
        if not smear_name:
            return

        new_name = function.prompt_rename_smear(smear_name)
        if not new_name:
            return

        blend_shape_nodes = function.get_blend_shape_nodes_for_smear(smear_name)
        function.rename_smear(smear_name, new_name, blend_shape_nodes)

        self.refresh_smear_list()

        items = self.ui.listWidget_smear_name.findItems(
            new_name, QtCore.Qt.MatchExactly | QtCore.Qt.MatchCaseSensitive
        )
        if items:
            self.ui.listWidget_smear_name.setCurrentItem(items[0])
            self.refresh_current_smear()

    def set_key(self):
        smear_name = self.get_current_smear_name()
        blend_shape_nodes = function.get_blend_shape_nodes_for_smear(smear_name)

        if not smear_name or not blend_shape_nodes:
            return

        function.set_key(smear_name, blend_shape_nodes)

    def select_blend_shape_node(self):
        smear_name = self.get_current_smear_name()
        blend_shape_nodes = function.get_blend_shape_nodes_for_smear(smear_name)

        if blend_shape_nodes:
            function.select_nodes(blend_shape_nodes)
            pm.inViewMessage(
                amg="<hl>Select Blend Shape Node : {}</hl>".format(smear_name),
                pos="botCenter",
                fade=True,
            )
        else:
            pm.inViewMessage(
                amg="<hl>Not found any selected smear.</hl>", pos="botCenter", fade=True
            )

    @uitools.undoable
    def add_active_mesh(self):
        smear_name = self.get_current_smear_name()
        if not smear_name:
            pm.confirmDialog(message="Please select or create a smear first.")
            return

        selection = pm.ls(sl=True)
        if not selection:
            pm.confirmDialog(message="Please select mesh to add as active mesh.")
            return

        function.add_active_mesh(selection, smear_name)
        self.refresh_current_smear()

    @uitools.undoable
    def remove_active_mesh(self):
        smear_name = self.get_current_smear_name()
        selected_items = self.ui.listWidget_active_meshes.selectedItems()

        if not smear_name or not selected_items:
            return

        meshes = [item.text() for item in selected_items]
        blend_shape_nodes = function.get_blend_shape_nodes_for_smear(smear_name)

        function.remove_active_mesh(meshes, smear_name, blend_shape_nodes)
        self.refresh_current_smear()
