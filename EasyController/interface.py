from tmlib.core import (
    Controller,
    Utility
)
from tmlib.module.PySide import QtCore, QtGui, QtWidgets, QAction

import os, importlib, webbrowser, inspect, configparser, re, json
from tmlib.ui.interface_template import ToolkitWindow
import maya.cmds as cmds
from tmlib.ui import uitools

class MainWindow(ToolkitWindow):
    def __init__(self):
        # Set-up Interface
        super(MainWindow, self).__init__(os.path.basename(os.path.dirname(__file__)))

        self.set_up_controller_widget()

    def set_up_controller_widget(self):

        def set_button_icon(button, index):
            path = os.path.join(icon_path, "icon_{}.jpg".format(str(index).zfill(2)))
            button.setIcon(QtGui.QIcon(path))
            button.setIconSize(QtCore.QSize(30,30))

        def swap_keyword():
            source = self.ui.lineEdit_source.text()
            target = self.ui.lineEdit_target.text()

            self.ui.lineEdit_source.setText(target)
            self.ui.lineEdit_target.setText(source)

        def update_keyword_presets():
            dict_data = {
                0: ["L_", "R_"],
                1: ["*L", "*R"],
                2: ["L0", "R0"],
            }

            current_index = self.ui.comboBox_keyword.currentIndex()

            self.ui.lineEdit_source.setText(dict_data[current_index][0])
            self.ui.lineEdit_target.setText(dict_data[current_index][1])

        icon_path = os.path.join(os.path.dirname(__file__), "icons")
        selection = cmds.ls(selection=True)

        # ============================================
        # set-up control icon and connect to command
        # ============================================

        for i,button_control in enumerate([self.ui.pushButton_icon_1,
                       self.ui.pushButton_icon_2,
                       self.ui.pushButton_icon_3,
                       self.ui.pushButton_icon_4,
                       self.ui.pushButton_icon_5,
                       self.ui.pushButton_icon_6,
                       self.ui.pushButton_icon_7,
                       self.ui.pushButton_icon_8,
                       self.ui.pushButton_icon_9,
                       self.ui.pushButton_icon_10,
                       self.ui.pushButton_icon_11,
                       self.ui.pushButton_icon_12,
                       self.ui.pushButton_icon_13,
                       self.ui.pushButton_icon_14,
                       self.ui.pushButton_icon_15,
                       self.ui.pushButton_icon_16,
                       self.ui.pushButton_icon_17,
                       self.ui.pushButton_icon_18,
                       self.ui.pushButton_icon_19,
                       self.ui.pushButton_icon_20,
                       self.ui.pushButton_icon_21,
                       self.ui.pushButton_icon_22,
                       self.ui.pushButton_icon_23,
                       self.ui.pushButton_icon_24,
                       self.ui.pushButton_icon_25,
                       self.ui.pushButton_icon_26,
                       self.ui.pushButton_icon_27,
                       self.ui.pushButton_icon_28]):
            
            set_button_icon(button=button_control,index=i+1)
            button_control.clicked.connect(lambda x: Controller.create_control(i))

        # ============================================
        # set-up color button
        # ============================================

        self.ui.pushButton_color_1.clicked.connect(lambda x :self.on_click_set_color(i=1))
        self.ui.pushButton_color_2.clicked.connect(lambda x :self.on_click_set_color(i=2))
        self.ui.pushButton_color_3.clicked.connect(lambda x :self.on_click_set_color(i=3))
        self.ui.pushButton_color_4.clicked.connect(lambda x :self.on_click_set_color(i=4))
        self.ui.pushButton_color_5.clicked.connect(lambda x :self.on_click_set_color(i=5))
        self.ui.pushButton_color_6.clicked.connect(lambda x :self.on_click_set_color(i=6))
        self.ui.pushButton_color_7.clicked.connect(lambda x :self.on_click_set_color(i=7))
        self.ui.pushButton_color_8.clicked.connect(lambda x :self.on_click_set_color(i=8))
        self.ui.pushButton_color_9.clicked.connect(lambda x :self.on_click_set_color(i=9))
        self.ui.pushButton_color_10.clicked.connect(lambda x :self.on_click_set_color(i=10))
        self.ui.pushButton_color_11.clicked.connect(lambda x :self.on_click_set_color(i=11))
        self.ui.pushButton_color_12.clicked.connect(lambda x :self.on_click_set_color(i=12))
        self.ui.pushButton_color_13.clicked.connect(lambda x :self.on_click_set_color(i=13))
        self.ui.pushButton_color_14.clicked.connect(lambda x :self.on_click_set_color(i=14))
        self.ui.pushButton_color_15.clicked.connect(lambda x :self.on_click_set_color(i=15))
        self.ui.pushButton_color_16.clicked.connect(lambda x :self.on_click_set_color(i=16))
        self.ui.pushButton_color_17.clicked.connect(lambda x :self.on_click_set_color(i=17))
        self.ui.pushButton_color_18.clicked.connect(lambda x :self.on_click_set_color(i=18))
        self.ui.pushButton_color_19.clicked.connect(lambda x :self.on_click_set_color(i=19))
        self.ui.pushButton_color_20.clicked.connect(lambda x :self.on_click_set_color(i=20))
        self.ui.pushButton_color_21.clicked.connect(lambda x :self.on_click_set_color(i=21))
        self.ui.pushButton_color_22.clicked.connect(lambda x :self.on_click_set_color(i=22))
        self.ui.pushButton_color_23.clicked.connect(lambda x :self.on_click_set_color(i=23))
        self.ui.pushButton_color_24.clicked.connect(lambda x :self.on_click_set_color(i=24))
        self.ui.pushButton_color_25.clicked.connect(lambda x :self.on_click_set_color(i=25))
        self.ui.pushButton_color_26.clicked.connect(lambda x :self.on_click_set_color(i=26))
        self.ui.pushButton_color_27.clicked.connect(lambda x :self.on_click_set_color(i=27))
        self.ui.pushButton_color_28.clicked.connect(lambda x :self.on_click_set_color(i=28))
        self.ui.pushButton_color_29.clicked.connect(lambda x :self.on_click_set_color(i=29))
        self.ui.pushButton_color_30.clicked.connect(lambda x :self.on_click_set_color(i=30))


        self.ui.pushButton_color_rgb.clicked.connect(
            lambda x: Controller.open_color_dialog()
        )
        
        # =================
        # mirror function
        # =================

        self.ui.pushButton_mirror_left_to_right.clicked.connect(self.on_mirror_left_to_right_clicked)
        self.ui.pushButton_mirror_right_to_left.clicked.connect(self.on_mirror_right_to_left_clicked)
        self.ui.horizontalSlider_line_width.valueChanged.connect(self.on_slider_curve_thick_changed)

        # self.ui.pushButton_swap_keyword.clicked.connect(swap_keyword)
        # self.ui.lineEdit_source.setText("L_")
        # self.ui.lineEdit_target.setText("R_")

        # self.ui.pushButton_mirror_shape.clicked.connect(
        #     lambda x: Controller.mirror_shape(
        #         source_side=self.ui.lineEdit_source.text(),
        #         target_side=self.ui.lineEdit_target.text(),
        #     )
        # )

        # update_keyword_presets()
        # self.ui.comboBox_keyword.currentTextChanged.connect(update_keyword_presets)

        # isolate edit
        self.ui.pushButton_isolateEdit.clicked.connect(
            lambda x: Controller.isolate_edit(False, False)
        )
        self.ui.pushButton_isolateClear.clicked.connect(
            lambda x: Controller.isolate_clear()
        )

        # multiple replace function
        # self.ui.pushButton_replace.clicked.connect(lambda x: Controller.clone_shape())
        self.ui.pushButton_clone_style.clicked.connect(lambda x : self.on_clone_style_clicked())

        # ===============
        # flip function
        # ===============

        self.ui.pushButton_flip_x.clicked.connect(lambda x: Controller.flip_shape("x"))
        self.ui.pushButton_flip_x.clicked.connect(lambda x: Controller.flip_shape("y"))
        self.ui.pushButton_flip_x.clicked.connect(lambda x: Controller.flip_shape("z"))

        self.ui.pushButton_match_cv.clicked.connect(self.on_auto_match_clicked)

        cmds.select(selection)

    @uitools.undoable
    def on_click_set_color(self,i):
        print("color set : {}".format(i))
        Controller.set_color([True, i])

    @uitools.undoable
    def on_clone_style_clicked(self):
        Controller.clone_style()

    @uitools.undoable
    def on_mirror_left_to_right_clicked(self):
        Controller.as_mirror_control_curves(left_to_right=True)

    @uitools.undoable
    def on_mirror_right_to_left_clicked(self):
        Controller.as_mirror_control_curves(left_to_right=False)

    @uitools.undoable
    def on_slider_curve_thick_changed(self):
        Controller.set_line_width(cmds.ls(sl=1),self.ui.horizontalSlider_line_width.value())

    @uitools.undoable
    def on_auto_match_clicked(self):
        
        # check selection filter
        sel = cmds.ls(sl=1)
        
        targets = sel[0:len(sel)-1]
        ref = sel[-1]

        # get ref controller cvs
        ref_shapes = cmds.listRelatives(ref,c=1,s=1,typ="nurbsCurve",f=1)

        if len(ref_shapes) != 1:
            raise Exception("This tools not support multiple shapes in controller.")


        ref_cvs,ref_spans,ref_degrees = Utility.get_cvs(ref_shapes[0])


        # check target controller cvs and update shape

        for s in targets:
            shapes = cmds.listRelatives(s,c=1,s=1,typ="nurbsCurve",f=1)

            if len(shapes) != 1:
                raise Exception("This tools not support multiple shapes in controller.")

            # get vertex position
            target_cvs,target_spans,target_degrees = Utility.get_cvs(shapes[0])

            if target_cvs == ref_cvs and ref_spans == target_spans and ref_degrees == target_degrees:
                Controller.match_controller_cv()
            else:
                Controller.as_swap_curve()

        cmds.inViewMessage(amg="Copy Shape Success!")