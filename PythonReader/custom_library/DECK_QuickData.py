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

from tmlib.ui.interface_template import ToolkitWindow

from tmlib.ui import uitools
import maya.cmds as cmds


def export_all_shape():
    try_create_quick_data_folder()
    
    QuickData.export_shape_quick()

def import_all_shape():
    try_create_quick_data_folder()
    
    QuickData.import_shape_quick()

def import_selected_skin(enable_transfer=False):
    try_create_quick_data_folder()
    
    QuickData.import_skin_quick(enable_transfer=enable_transfer)

def export_selected_skin():
    try_create_quick_data_folder()
    
    QuickData.export_skin_quick()

def export_all_skin_shape():
    try_create_quick_data_folder()
    
    QuickData.backup_controller_and_skin()

def import_all_skin_shape():
    try_create_quick_data_folder()

    QuickData.apply_controller_and_skin()

def try_create_quick_data_folder():
    if QuickData.get_quick_data_dir() is False:
        result = cmds.confirmDialog( title='Confirm', message='Quick Data Path not found , create a new one?', button=['Yes','No'], defaultButton='Yes', cancelButton='No', dismissString='No' )
        if result == "Yes":
            QuickData.create_quick_data_folder_template()
