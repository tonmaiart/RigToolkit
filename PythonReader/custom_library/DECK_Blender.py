import tmlib
from tmlib.core import QuickData, Scene, Utility, Validate, SkinWeight

import maya.cmds as cmds
import maya.mel as mel
import os

import UkoreMaya

from UkoreMaya.core import Pipeline, utils
from UkoreMaya.menu import General, Skin

def import_weight():
    if not QuickData.get_quick_data_dir():
        cmds.warning("Quick data directory not found. Please save your file first.")
        return
    else:
        quick_data_path = QuickData.get_quick_data_dir()

    list_files = os.listdir(os.path.join(quick_data_path,"FbxFromBlender"))

    print("# List Files")
    for file in list_files:
        print(file)

    for file in list_files:
        if file.endswith(".fbx"):
            path_import = os.path.join(quick_data_path,"FbxFromBlender" ,file)
            print("Importing Fbx : {}".format(path_import))

            # cmds.importFBX(path_import)
            cmds.file(path_import, i=True, type="FBX", ignoreVersion=True, ra=True, mergeNamespacesOnClash=True, namespace=":", options="fbx",  pr=True)

    # path_import = os.path.join(quick_data_path,"FbxFromBlender" ,"{}.json".format())

def export_weight():
    cmds.select(cmds.ls(typ="transform"))
    QuickData.export_skin_quick()

