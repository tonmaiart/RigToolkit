from BeamSmear import (
    Misc,
    BlendShape,
)

from BeamSmear.PySide import QtCore, QtGui, QtWidgets, QAction

import os, importlib, webbrowser, inspect, configparser, re, json
from BeamSmear.interface_template import ToolkitWindow
from BeamSmear.PySide import QtWidgets, QtCore, QtGui, QUiLoader, QtWidgets

import pymel.core as pm
import maya.cmds as mc


class MainWindow(ToolkitWindow):
    def __init__(self):
        # Set-up Interface
        super(MainWindow, self).__init__("BeamSmear")

        self.local_rig_file_path = ""
        self.local_rig_file_name_only = ""
        self.local_rig_file_json = ""

        self.set_up_anim_sculpt_widget()

    def set_up_anim_sculpt_widget(self):
        def duplicate_orig_shape(obj, n):
            obj = pm.duplicate(obj, n=n)

            child = pm.listRelatives(obj, c=1, typ="transform")

            if child:
                pm.delete(child)

            shapes = pm.listRelatives(obj, c=1, s=1)
            has_orig = any("Orig" in item.shortName() for item in shapes)

            if has_orig:
                exist_orig = None

                for shape in shapes:
                    shape_name = shape.shortName()

                    if "Orig" in shape_name and exist_orig is None:
                        exist_orig = shape_name
                        pm.setAttr("{}.intermediateObject".format(shape_name), False)

                    else:
                        pm.delete(shape)

            return obj

        @Misc.undoable
        def add_active_mesh():
            selection = pm.ls(sl=1)

            ## -------------------------
            ## add blendshape target
            ## -------------------------

            smear_name = get_current_smear_name()
            current_blend_shape = get_current_blend_shape_node()
            # active_meshes = get_current_active_meshes()

            for mesh in selection:
                #############################
                ## Create Main Blend Shape ##
                #############################

                # is already have main blendshape
                target_node = get_beam_smear_node(mesh=mesh)

                # create new main blend shape if not exist
                if target_node is None:
                    target_node = mc.blendShape(
                        mesh, n="BeamSmear_bs".format(smear_name)
                    )[0]

                    pm.setAttr("{}.envelope".format(target_node), l=1)

                #######################################
                ## Add New Smear Target if not exist ##
                #######################################

                all_smear_name = mc.aliasAttr(target_node, query=True)

                if all_smear_name is None or smear_name not in all_smear_name:
                    # target_mesh = pm.duplicate(mesh, n=smear_name)[0]
                    target_mesh = duplicate_orig_shape(mesh, n=smear_name)[0]

                    target_mesh = str(target_mesh)

                    targets = mc.getAttr(f"{target_node}.w", size=True) + 1
                    target_index = targets

                    pm.blendShape(
                        target_node,
                        e=True,
                        tc=True,
                        t=(mesh, target_index, target_mesh, 1.0),
                        w=(target_index, 1.0),
                    )

                    pm.delete(target_mesh)

            blend_shape_nodes = get_current_blend_shape_node()

            update_active_mesh_widget(
                smear_name=smear_name,
                active_meshes=None,
                blend_shape_nodes=blend_shape_nodes,
            )
            update_slider_real_time(
                smear_name=smear_name, blend_shape_nodes=blend_shape_nodes
            )

        def remove_active_mesh():
            pass

        def update_active_mesh_widget(
            smear_name=None,
            active_meshes=None,
            blend_shape_nodes=None,
            snap_key_frame=None,
        ):

            # clear list widget
            self.ui.listWidget_active_meshes.clear()

            # Optimized
            if smear_name is None:
                smear_name = get_current_smear_name()

            if active_meshes is None:
                active_meshes = get_all_active_meshes()

            if blend_shape_nodes is None:
                blend_shape_nodes = get_current_blend_shape_node()

            # return if something empty
            if not smear_name:
                return
            elif not active_meshes:
                return
            elif not blend_shape_nodes:
                return

            # add items to list widget
            self.ui.listWidget_active_meshes.addItems(active_meshes)

            # lock others attribute
            for node in blend_shape_nodes:
                all_smear_name = mc.aliasAttr(node, query=True)

                if not all_smear_name:
                    continue
                else:
                    all_smear_name = all_smear_name[::2]

                for name in all_smear_name:
                    if name == smear_name:
                        pm.setAttr("{}.{}".format(node, name), k=True, l=False)
                    else:
                        pm.setAttr("{}.{}".format(node, name), k=False, l=True)

            # --------------------------------------------------------------
            # Update Slider, Select blend Shape node and turn on edit mode
            # --------------------------------------------------------------
            update_slider_real_time(
                smear_name=smear_name, blend_shape_nodes=blend_shape_nodes
            )
            select_blend_shape_node_only(
                smear_name=smear_name, blend_shape_nodes=blend_shape_nodes
            )
            enter_edit_mode(
                smear_name=smear_name,
                blend_shape_nodes=blend_shape_nodes,
                active_meshes=active_meshes,
            )

            # ===========================
            # Fix Keyframe Viewport bugs
            # ===========================

            if not snap_key_frame:
                attr = "{}.{}".format(blend_shape_nodes[0], smear_name)
                pm.currentTime(get_max_keyframe(attr=attr))

            else:
                pm.currentTime(snap_key_frame)

        def get_max_keyframe(attr):
            times = mc.keyframe(attr, q=True, timeChange=True) or []
            values = mc.keyframe(attr, q=True, valueChange=True) or []

            key_data = list(zip(times, values))

            # set current time to most influence if have keyed
            if key_data:
                max_value = None
                target_frame = None

                for frame, value in key_data:
                    if max_value == None:
                        max_value = value
                        target_frame = frame
                    elif value > max_value:
                        max_value = value
                        target_frame = frame

                return target_frame

            # set current time
            else:
                current_frame = pm.currentTime(q=True)
                return current_frame

        def update_smear_list_widget(
            smear_name=None, active_meshes=None, blend_shape_nodes=None
        ):

            # reset smear list widget first
            self.ui.listWidget_smear_name.clear()

            # get current blend shape nodes
            if not blend_shape_nodes:
                blend_shape_nodes = get_all_blend_shape_nodes()

            # return if not blend shape nodes
            if not blend_shape_nodes:
                return

            # Update list widget

            list_smear_name = get_all_smear_name()

            self.ui.listWidget_smear_name.addItems(list_smear_name)

            select_last_item()
            # update_active_mesh_widget(
            #     smear_name=smear_name,
            #     active_meshes=active_meshes,
            #     blend_shape_nodes=blend_shape_nodes,
            # )

            # enter_edit_mode()

        def select_last_item():
            list_widget = self.ui.listWidget_smear_name

            last_index = list_widget.count() - 1
            if last_index >= 0:
                list_widget.setCurrentRow(last_index)

        def set_key():
            select_blend_shape_node_only()

            smear_name = get_current_smear_name()
            list_blend_shape_node = get_current_blend_shape_node()

            for node in list_blend_shape_node:
                pm.setKeyframe("{}.{}".format(node, smear_name))

            pm.inViewMessage(
                amg="<hl>Set Keyframe : {}</hl>".format(smear_name),
                pos="botCenter",
                fade=True,
            )

        def get_current_blend_shape_node():
            list_current_blend_shape = []
            active_meshes = get_all_active_meshes()
            smear_name = get_current_smear_name()

            if not active_meshes:
                return None

            for mesh in active_meshes:
                exists_blendshape = BlendShape.get_blendshape_nodes(mesh)
                main_blend_shape_node = None

                for node in exists_blendshape:
                    node_name = node.shortName()
                    if "BeamSmear_bs".format(smear_name) in node_name:
                        main_blend_shape_node = node_name
                        list_current_blend_shape.append(main_blend_shape_node)
                        break

            return list_current_blend_shape

        def update_opacity():
            value = self.ui.horizontalSlider_key_opacity.value()
            norm_value = value * 0.01

            smear_name = get_current_smear_name()
            nodes = get_current_blend_shape_node()

            if nodes:
                for node in nodes:
                    pm.setAttr("{}.{}".format(node, smear_name), norm_value)

        def select_blend_shape_node_only(smear_name=None, blend_shape_nodes=None):
            # optimized
            if smear_name is None:
                smear_name = get_current_smear_name()
            if blend_shape_nodes is None:
                blend_shape_nodes = get_current_blend_shape_node()

            pm.select(blend_shape_nodes)

            pm.inViewMessage(
                amg="<hl>Select Blend Shape Node : {}</hl>".format(smear_name),
                pos="botCenter",
                fade=True,
            )

        def get_beam_smear_node(mesh):
            exists_blendshape = BlendShape.get_blendshape_nodes(mesh)
            target_node = None

            if exists_blendshape:
                for node in exists_blendshape:
                    node_name = node.shortName()
                    if "BeamSmear_bs" in node_name:
                        target_node = node_name
                        break

            return target_node

        @Misc.undoable
        def create_smear():
            def get_default_smear_name():
                # Get New Name auto
                count = 1
                all_smear_name = get_all_smear_name()

                while True:
                    # Format the name with a two-digit number
                    smear_name_default = f"smear{count:02d}"

                    # Check if an object with this name already exists in the scene
                    if not all_smear_name:
                        break
                    elif smear_name_default not in all_smear_name:
                        break

                    # If it exists, increment the count and check again
                    count += 1

                return smear_name_default

            ## ----------------------
            ## Check Selection
            ## ----------------------

            selection = pm.ls(sl=1)

            for sel in selection:
                if not pm.listRelatives(sel, c=1, typ="mesh"):
                    pm.confirmDialog(message="Selection must be mesh.")
                    return

            if not selection:
                pm.confirmDialog(message="Please Select Mesh before add new smear")
                return

            ## ----------------------
            ## Confirm Input
            ## ----------------------

            result = mc.promptDialog(
                title="Rename Object",
                text=get_default_smear_name(),
                message="Enter Name:",
                button=["OK", "Cancel"],
                defaultButton="OK",
                cancelButton="Cancel",
                dismissString="Cancel",
            )

            if not result == "OK":
                return

            smear_name = mc.promptDialog(query=True, text=True)

            ## -------------------------
            ## add blendshape to target
            ## -------------------------

            for mesh in selection:

                #######################################
                ## Find Exist /Create Blend Shape
                #######################################

                target_node = get_beam_smear_node(mesh=mesh)

                if target_node is None:
                    target_node = pm.blendShape(
                        mesh, n="BeamSmear_bs".format(smear_name)
                    )[0]

                    pm.setAttr("{}.envelope".format(target_node), l=1)

                #######################################
                ## Add New Smear Target if not exist ##
                #######################################

                all_smear_name = pm.aliasAttr(target_node, query=True)

                if all_smear_name is None or smear_name not in all_smear_name:
                    # target_mesh = pm.duplicate(mesh, n=smear_name)[0]
                    target_mesh = duplicate_orig_shape(mesh, n=smear_name)[0]

                    target_mesh = str(target_mesh)

                    targets = mc.getAttr(f"{target_node}.w", size=True) + 1
                    target_index = targets

                    pm.blendShape(
                        target_node,
                        e=True,
                        tc=True,
                        t=(mesh, target_index, target_mesh, 1.0),
                        w=(target_index, 1.0),
                    )

                    pm.delete(target_mesh)

                ## =========================
                ## Connect Cache Attribute
                ## =========================
                attr_name = "{}Meshes".format(smear_name)
                attr_path = "{}.{}".format(target_node, attr_name)

                if not pm.attributeQuery(attr_name, node=target_node, exists=True):
                    pm.addAttr(target_node, k=1, at="message", multi=True, ln=attr_name)

                existing = mc.listConnections(attr_path, plugs=True) or []
                next_index = len(existing)
                dst_attr = "{}[{}]".format(attr_path, next_index)
                pm.connectAttr(
                    "{}.message".format(mesh),
                    dst_attr,
                )

            # blend_shape_nodes = get_current_blend_shape_node()

            ## -------------------------
            # Update widget
            ## -------------------------

            # update_smear_list_widget()

            # update_active_mesh_widget(
            #     smear_name=smear_name,
            #     active_meshes=None,
            #     blend_shape_nodes=blend_shape_nodes,
            # )
            # update_slider_real_time(
            #     smear_name=smear_name, blend_shape_nodes=blend_shape_nodes
            # )

            ## -------------------------
            # Select Last Items of Smear
            ## -------------------------
            self.ui.listWidget_smear_name.addItem(smear_name)
            select_last_item()

            ## -------------------------
            ## Popup Message
            ## -------------------------

            pm.inViewMessage(
                amg="<hl>Created New Smear : {}</hl>".format(smear_name),
                pos="botCenter",
                fade=True,
            )

        @Misc.undoable
        def delete_smear():
            smear_name = get_current_smear_name()

            # do nothing if no smear left
            if not smear_name:
                return

            # get current smear name
            blend_shape_nodes = get_current_blend_shape_node()

            try:
                mc.deleteAttr(self.cache_node, attribute=smear_name)
            except:
                pass

            pm.delete(blend_shape_nodes)

            # RELOAD
            update_smear_list_widget(
                smear_name=smear_name, blend_shape_nodes=blend_shape_nodes
            )
            update_active_mesh_widget(
                smear_name=smear_name, blend_shape_nodes=blend_shape_nodes
            )

            pm.inViewMessage(
                amg="<hl>Delete Smear : {}</hl>".format(smear_name),
                pos="botCenter",
                fade=True,
            )

        def get_current_smear_name(optimized=False):
            if optimized:
                selected_items = self.ui.listWidget_smear_name.selectedItems()

                if selected_items:
                    return selected_items[0].text()
                else:
                    return
            else:
                selected_items = self.ui.listWidget_smear_name.selectedItems()

                if selected_items:
                    text = selected_items[0].text()
                    print("Current Smear Name : ", text)

                    return text
                else:
                    return

        def get_all_smear_name(optimized=False):
            if optimized:
                items = []
                for i in range(self.ui.listWidget_smear_name.count()):
                    items.append(self.ui.listWidget_smear_name.item(i).text())
                return items
            else:
                # filter for optimized
                all_smear_name = []

                for node in get_all_blend_shape_nodes():
                    all_weight = mc.aliasAttr(node, query=True)

                    if all_weight is None:
                        continue

                    # normalize name
                    all_weight = all_weight[::2]
                    all_smear_name += all_weight

                all_smear_name = list(set(all_smear_name))

                print("all smear_name : ", all_smear_name)
                return all_smear_name

        def get_all_active_meshes(optimized=False):

            if optimized:
                items = []
                for i in range(self.ui.listWidget_active_meshes.count()):
                    items.append(self.ui.listWidget_active_meshes.item(i).text())
                return items
            else:

                smear_name = get_current_smear_name()

                if not smear_name:
                    return

                blend_shape_nodes = get_current_blend_shape_node()

                if not blend_shape_nodes:
                    return

                node = blend_shape_nodes[0]
                items = mc.listConnections(
                    "{}.{}Meshes".format(node, smear_name), s=True, d=False
                )

                return items

        def update_slider_real_time(smear_name=None, blend_shape_nodes=None):
            if not smear_name:
                smear_name = get_current_smear_name()
            if not blend_shape_nodes:
                blend_shape_nodes = get_current_blend_shape_node()

            # return if smear name of blend shape is empty
            if not smear_name:
                return
            elif not blend_shape_nodes:
                return

            node = blend_shape_nodes[0]

            if node:
                value = pm.getAttr("{}.{}".format(node, smear_name))
                self.ui.horizontalSlider_key_opacity.setValue(value * 100)

        def enter_edit_mode(
            smear_name=None,
            active_meshes=None,
            blend_shape_nodes=None,
        ):

            if blend_shape_nodes is None:
                blend_shape_nodes = get_current_blend_shape_node()
            if smear_name is None:
                smear_name = get_current_smear_name()
            if active_meshes is None:
                active_meshes = get_all_active_meshes()

            if not blend_shape_nodes:
                pm.warning("Can't Enter Edit Mode ,Not found current BeamSmear node.")
                return

            for node in blend_shape_nodes:
                if node is None:
                    return

                # Equivalent of: sculptTarget -e -target -1 blendShape1;
                # 1. Deactivate any current sculpt target
                mc.sculptTarget(node, e=True, target=-1)

                # 2. Get target index
                aliases = mc.aliasAttr(node, q=True) or []
                alias_dict = {
                    aliases[i]: aliases[i + 1] for i in range(0, len(aliases), 2)
                }

                if smear_name in alias_dict:
                    index = int(alias_dict[smear_name].split("[")[1].split("]")[0])

                    # 3. Activate target for editing by index
                    mc.sculptTarget(node, e=True, target=index)

                else:
                    print(f"Target '{smear_name}' not found in '{node}'")

        def select_blend_shape_node():
            # Switch selection to object mode
            mc.selectMode(object=True)
            mc.selectType(allObjects=True)

            # Get current selection
            sel = mc.ls(sl=True, long=True) or []

            # Convert any component selection to the transform object
            obj_sel = mc.ls(sel, objectsOnly=True, long=True)
            if obj_sel:
                mc.select(obj_sel, replace=True)
            else:
                mc.select(clear=True)

            mc.select(clear=True)

            select_blend_shape_node_only()

            selection = pm.ls(sl=1)

            if selection:
                pm.inViewMessage(
                    amg="<hl>Selected Blend Shape Node</hl>",
                    pos="botCenter",
                    fade=True,
                )
            else:
                pm.inViewMessage(
                    amg="<hl>Not found any selected smear.</hl>",
                    pos="botCenter",
                    fade=True,
                )

        def get_all_blend_shape_nodes():
            all_blend_shape_node = pm.ls(typ="blendShape")
            list_return = []

            for node in all_blend_shape_node:
                if "BeamSmear_bs" in node.shortName():
                    list_return.append(node.shortName())

            return list_return

        def auto_highlight_smear():
            all_blend_shape_node = get_all_smear_name()

            # # ---------------------
            # # search closest time
            # # ---------------------
            # current_time = pm.currentTime(q=True)
            # target_node = None
            # target_attr = None
            # diffrent_value = None

            # for node in all_blend_shape_node:
            #     aliases = mc.aliasAttr(node, q=True) or []

            #     # aliases = [name0, weight[0], name1, weight[1], ...]
            #     for i in range(0, len(aliases), 2):
            #         target_name = aliases[i]
            #         weight_attr = "{}.{}".format(node, aliases[i + 1])

            #         keyframe_data = sorted(set(mc.keyframe(weight_attr, q=True) or []))
            #         if not keyframe_data:
            #             continue

            #         closest_value = min(
            #             keyframe_data, key=lambda x: abs(x - current_time)
            #         )

            #         # set first target case
            #         if target_node is None:
            #             target_node = node
            #             target_attr = target_name
            #             diffrent_value = abs(current_time - closest_value)

            #         else:
            #             current_diffrent_value = abs(current_time - closest_value)
            #             if current_diffrent_value < diffrent_value:
            #                 target_node = node
            #                 target_attr = target_name
            #                 diffrent_value = current_diffrent_value

            # # -------------------
            # # Select Blend Shape
            # # -------------------
            # if target_node and target_attr:
            #     # reset all style sheet first
            #     for i in range(self.ui.listWidget_smear_name.count()):
            #         item = self.ui.listWidget_smear_name.item(i)
            #         item.setBackground(QtGui.QBrush())

            #     smear_name = target_attr  # now use the alias target name directly

            #     # set target style sheet
            #     item = self.ui.listWidget_smear_name.findItems(
            #         smear_name, QtCore.Qt.MatchExactly | QtCore.Qt.MatchCaseSensitive
            #     )[0]
            #     item.setBackground(QtGui.QBrush(QtGui.QColor(147, 202, 247)))

            #     print("## Auto Select : {} ##".format(item.text()))
            #     print("Target Node", target_node)

        @Misc.undoable
        def edit_smear_name():
            smear_name = get_current_smear_name()
            blend_shape_all = get_all_blend_shape_nodes()

            result = mc.promptDialog(
                title="Rename Object",
                text=smear_name,
                message="Rename {} to:".format(smear_name),
                button=["OK", "Cancel"],
                defaultButton="OK",
                cancelButton="Cancel",
                dismissString="Cancel",
            )

            if result == "OK":
                new_name = mc.promptDialog(query=True, text=True)

                val = pm.getAttr(f"{self.cache_node}.{smear_name}")
                typ = pm.getAttr(f"{self.cache_node}.{smear_name}", type=True)
                pm.deleteAttr(f"{self.cache_node}.{smear_name}")
                pm.addAttr(self.cache_node, ln=new_name, k=True, dt="stringArray")

                try:
                    pm.setAttr(f"{self.cache_node}.{new_name}", val)
                except:
                    pass

                for node in blend_shape_all:
                    try:
                        BlendShape.rename_blendshape_target(node, smear_name, new_name)
                    except:
                        pass

                # update smear widget and select
                update_smear_list_widget()

                item = self.ui.listWidget_smear_name.findItems(
                    new_name, QtCore.Qt.MatchExactly | QtCore.Qt.MatchCaseSensitive
                )[0]

                self.ui.listWidget_smear_name.setCurrentItem(item)

            else:
                pm.displayInfo("Creatre new smear is cancelled.")
                return

        def select_active_mesh():
            selected_items = self.ui.listWidget_active_meshes.selectedItems()

            # pm.select(cl=True)

            pm.select([item.text()] for item in selected_items)

        # ===========================
        # Signal connection
        # ===========================

        self.ui.pushButton_create_smear.clicked.connect(create_smear)
        # self.ui.pushButton_delete_smear.clicked.connect(delete_smear)
        # self.ui.pushButton_edit_smear_name.clicked.connect(edit_smear_name)

        # self.ui.pushButton_set_key.clicked.connect(set_key)

        # self.ui.listWidget_smear_name.itemClicked.connect(update_active_mesh_widget)

        # self.ui.listWidget_active_meshes.itemClicked.connect(select_active_mesh)
        # self.ui.listWidget_active_meshes.currentItemChanged.connect(select_active_mesh)

        # self.ui.horizontalSlider_key_opacity.sliderPressed.connect(update_opacity)
        # self.ui.horizontalSlider_key_opacity.sliderMoved.connect(update_opacity)
        # self.ui.horizontalSlider_key_opacity.sliderReleased.connect(update_opacity)

        # self.ui.pushButton_select_blend_shape_node.clicked.connect(
        #     select_blend_shape_node
        # )

        # self.ui.pushButton_add_active_mesh.clicked.connect(add_active_mesh)
        # self.ui.pushButton_remove_active_mesh.clicked.connect(remove_active_mesh)

        # ===========================
        # Update widget once when start
        # ===========================

        # update_smear_list_widget()
        # update_active_mesh_widget()

        # ===========================
        # Set script job
        # ===========================

        # mc.scriptJob(
        #     event=["timeChanged", update_slider_real_time],
        #     parent=self.objectName(),
        # )
        # mc.scriptJob(
        #     event=["timeChanged", auto_highlight_smear],
        #     parent=self.objectName(),
        # )
        # mc.scriptJob(
        #     event=["Undo", update_smear_list_widget],
        #     parent=self.objectName(),
        # )
        # mc.scriptJob(
        #     event=["Redo", update_smear_list_widget],
        #     parent=self.objectName(),
        # )

        # ===============================
        # Turn off GPU Override Warning
        # ===============================

        if mc.optionVar(q="gpuOverride"):
            self.ui.label_warning.setText(
                "⚠ Turn off Gpu Override for Stable Soft Selection."
            )

    def load_ui(self, ui_path):
        """Use to load .ui file by given path"""
        loader = QUiLoader()
        ui = QtCore.QFile(ui_path)
        ui.open(QtCore.QFile.ReadOnly)
        ui_return = loader.load(ui)
        ui.close()

        return ui_return
