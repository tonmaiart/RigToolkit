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

from tmlib.ui import uitools
from tmlib.ui.interface_template import ToolkitWindow
import maya.cmds as cmds


class MainWindow(ToolkitWindow):
    def __init__(self):
        super(MainWindow, self).__init__("WeightPuller")

        self.ui.pushButton_move_weight.clicked.connect(self.move_weight)
        self.ui.pushButton_swap_weight.clicked.connect(self.swap_weight)

    def swap_weight(self):
        source_text = self.ui.lineEdit_source_keyword.text()
        target_text = self.ui.lineEdit_target_keyword.text()

        self.ui.lineEdit_source_keyword.setText(target_text)
        self.ui.lineEdit_target_keyword.setText(source_text)

    @uitools.undoable
    def move_weight(self):
        selection = cmds.ls(selection=True, flatten=True)
        selected_meshes = Utility.cut(selection[0])

        weight_percent = self.ui.doubleSpinBox_move_weight.value()
        source_text = self.ui.lineEdit_source_keyword.text()
        target_text = self.ui.lineEdit_target_keyword.text()

        try:
            from ngSkinTools2.api import get_layers_enabled

            get_layers_enabled(selected_meshes)
            SkinWeight.move_weight_ngskintools(weight_percent, source_text, target_text)
            print("ngSkinTools2 weight moved")
        except Exception:
            SkinWeight.move_weight(weight_percent, source_text, target_text)
            print("Maya weight moved")

    

