from tmlib import config
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
import pymel.core as pm
import maya.cmds as mc



class MainWindow(ToolkitWindow):
    def __init__(self):

        super(MainWindow, self).__init__(os.path.basename(os.path.dirname(__file__)))
        