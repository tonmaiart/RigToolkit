import tmlib
from tmlib.core import QuickData, Validate,Visualized,Geometry
import maya.cmds as cmds
import maya.api.OpenMaya as om
import os
import maya.cmds as cmds
import glob
def clean_up_char_model_file():
    selection = cmds.ls(sl=1)
    Validate.validate_material_face_set(selection=selection)

    # validate uv sets

    pass

def match_shape_with_wrap():
    """
    Blend Shape with wrap deformer , ignore vertex id

    To use
    1.select prefer shape mesh > select before mesh (vertex order should match) > select target mesh that wanna match

    """

    pass

def auto_match_bounding_box():
    """Select ref and target mesh , the ref will try to scale the mesh size to reach fill the bounding box of target mesh"""

    # get from selection
    sel = cmds.ls(sl=1)

    if not sel:
        return

    if (cmds.selectPref(tso=True, q=True)==0):
        cmds.selectPref(tso=True)
        
    sel = cmds.ls(orderedSelection =1,fl=1)

    # first one is target , second one is ref
    vertices_ref = []
    vertices_target = []

    first_name = None
    second_name = None

    for s in sel:
        mesh_name = s.split(".")[0]

        if first_name is None:
            first_name = mesh_name
        
        if first_name and second_name is None and first_name != mesh_name:
            second_name = mesh_name
        
        if mesh_name == first_name:
            vertices_target.append(s)
        elif mesh_name == second_name:
            vertices_ref.append(s)

    Geometry.auto_match_bounding_box_by_vertices(vertices_ref=vertices_ref,vertices_target=vertices_target)



def clean_model():
    sel = cmds.ls(sl=1, l=1)
    list_child = cmds.listRelatives(sel, ad=1, typ="transform", f=1)
    list_target = sel + list_child if list_child is not None else sel

    # unlock attributes
    for target in list_target:
        list_attr = ["tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz", "v"]
        [cmds.setAttr("{}.{}".format(target, attr), k=1, l=0) for attr in list_attr]

    # delete history
    [cmds.delete(list_target, ch=1) for target in list_target]

    # delete orig shape
    for target in list_target:
        list_shapes = cmds.listRelatives(target, c=1, s=1, typ="mesh", f=1)

        if list_shapes:
            # delete orig
            for shape in list_shapes:
                if "Orig" in shape:
                    cmds.delete(shape)

            # rename all shape
            for shape in list_shapes:
                parent_name = cmds.listRelatives(shape, p=1, typ="transform")[0]
                parent_name = (
                    parent_name.split("|")[-1]
                    if "|" in parent_name
                    else parent_name
                )

                cmds.rename(shape, parent_name + "Shape")

    cmds.select(cl=1)
