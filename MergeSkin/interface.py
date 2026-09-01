import os
import importlib

import maya.cmds as mc

from tmlib.ui import uitools
from tmlib.ui.interface_template import ToolkitWindow

from MergeSkin import function

# launch()/launch_toolkit() only reload this interface module, not its
# sibling function.py -- reload it explicitly so scene-logic edits take
# effect without restarting Maya.
importlib.reload(function)


class MainWindow(ToolkitWindow):
    def __init__(self):
        super(MainWindow, self).__init__(os.path.basename(os.path.dirname(__file__)))

        self.ui.pushButton_add_base.clicked.connect(self.add_base_objects)
        self.ui.pushButton_remove_base.clicked.connect(self.remove_base_objects)
        self.ui.pushButton_set_target.clicked.connect(self.set_target)
        self.ui.pushButton_merge_skin.clicked.connect(self.merge_skin)

    def add_base_objects(self):
        selection = mc.ls(selection=True) or []
        if not selection:
            mc.warning("Select mesh(es) to add as base objects.")
            return

        existing = {
            self.ui.listWidget_base_objects.item(i).text()
            for i in range(self.ui.listWidget_base_objects.count())
        }
        for name in selection:
            if name not in existing:
                self.ui.listWidget_base_objects.addItem(name)

    def remove_base_objects(self):
        for item in self.ui.listWidget_base_objects.selectedItems():
            self.ui.listWidget_base_objects.takeItem(
                self.ui.listWidget_base_objects.row(item)
            )

    def set_target(self):
        selection = mc.ls(selection=True) or []
        if not selection:
            mc.warning("Select a mesh to set as target.")
            return
        self.ui.lineEdit_target.setText(selection[-1])

    def get_base_objects(self):
        return [
            self.ui.listWidget_base_objects.item(i).text()
            for i in range(self.ui.listWidget_base_objects.count())
        ]

    @uitools.undoable
    def merge_skin(self):
        base_objects = self.get_base_objects()
        target = self.ui.lineEdit_target.text().strip()

        if not base_objects:
            mc.warning("Add at least one base object.")
            return
        if not target:
            mc.warning("Set a target object.")
            return

        function.merge_skin(
            base_objects, target, debug_log=self.ui.checkBox_debug_log.isChecked()
        )
