import tmlib
from tmlib.core import QuickData, Scene, Utility, Validate, SkinWeight,Visualized,Create,Controller

import maya.cmds as cmds
import maya.mel as mel
import os

import UkoreMaya

from UkoreMaya.core import Pipeline, utils
from UkoreMaya.menu import General, Skin

def create_line():
    """
    Create Temp Display to Selected two locators
    
    """
    selection = cmds.ls(sl=1)

    create_tmp_grp()


    loc1 = cmds.spaceLocator()[0]
    loc2 = cmds.spaceLocator()[0]

    cmds.setAttr(cmds.listRelatives(loc1,c=1,s=1)[0]+".v",False)
    cmds.setAttr(cmds.listRelatives(loc2,c=1,s=1)[0]+".v",False)

    cmds.pointConstraint(selection[0],loc1)
    cmds.pointConstraint(selection[1],loc2)

    cmds.addAttr(loc1,ln="lineWidth",dv=3,k=1)

    Create.create_line_annotate(
        list_object=[loc1,loc2]
    )
    cmds.connectAttr(loc1+".lineWidth",cmds.listRelatives(loc1,c=1,s=1,typ="nurbsCurve")[0]+".lineWidth",f=1)

    cmds.parent(loc1,loc2,"TMP")
    cmds.select(loc1)

def visualized_cross_node():
    """
    Select Cross Node and start object , When run this will visualized cross vector line
    """
    selection = cmds.ls(sl=1)

    create_tmp_grp()


    node_cross = selection[0]
    start_point = selection[1]

    loc1 = cmds.spaceLocator()[0]
    loc2 = cmds.spaceLocator()[0]

    cmds.parent(loc1,"TMP")
    cmds.parent(loc2,loc1)
    cmds.pointConstraint(start_point,loc1)
    cmds.connectAttr(node_cross+".output",loc2+".translate",f=1)

    cmds.select(loc1,loc2)
    create_line()

    pass

def jaco():
    pass

def create_tmp_grp():
    if not cmds.objExists("TMP"):
        cmds.group(em=1,n="TMP")
