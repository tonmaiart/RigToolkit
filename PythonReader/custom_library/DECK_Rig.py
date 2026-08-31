import tmlib
from tmlib.core import QuickData, Scene, Utility, Validate, SkinWeight

import maya.cmds as cmds
import maya.mel as mel
import os
import fnmatch

import UkoreMaya

from UkoreMaya.core import Pipeline, utils
from UkoreMaya.menu import General, Skin

def import_all_reference_and_clean_namespaces():
    Scene.import_all_references()
    Scene.remove_all_namespaces()
    
def toggle_joints_via_set():
    def toggle_viewport_joints():
        # This is the "Fail-safe" - it hides joints only in the current view
        panel = cmds.getPanel(withFocus=True)
        if cmds.modelEditor(panel, q=True, exists=True):
            curr_state = cmds.modelEditor(panel, q=True, joints=True)
            cmds.modelEditor(panel, e=True, joints=not curr_state)

    joints = cmds.ls(type="joint")

    if not joints:
        cmds.warning("No joints found.")
        return

    # Check the visibility of the first joint to decide whether to hide or show
    # Note: If locked, we'll fall back to the Viewport Filter method
    try:
        current_state = cmds.getAttr(joints[0] + ".visibility")

        cmds.select(joints)
        if current_state:
            mel.eval("HideSelectedObjects;")
        else:
            mel.eval("ShowLastHidden;")

        cmds.select(clear=True)

    except RuntimeError:
        # This triggers if 'visibility' is locked/connected
        cmds.warning("Visibility is locked. Switching to Viewport Filter toggle.")
        toggle_viewport_joints()

    toggle_joints_via_set()


def clean_up_rig_file():
    Scene.clean_up_scene()


def update_model_for_rig():
    """This Used for Update model for rig in one click"""

    # remove old geo grp if exists

    if cmds.objExists("old_geo"):
        cmds.delete("old_geo")

    # store data
    cmds.select(Pipeline.list_meshes_with_suffix_geo())
    QuickData.export_skin_quick()

    # reference current version
    cmds.select(
        "*:geo",
    )
    sel = cmds.ls(sl=1)

    if not sel:
        raise Exception("Not found geo group")

    namespace = sel[0].split(":")[0]

    ref_node = cmds.referenceQuery(sel[0], referenceNode=True)
    ref_path = cmds.referenceQuery(ref_node, filename=True)

    # import all reference and namspaces
    Scene.import_all_references()
    Scene.remove_all_namespaces()

    if not cmds.objExists("Delete_Grp"):
        cmds.group(em=1, n="Delete_Grp")

    # rename old geo grp and parent to delete grp
    cmds.parent("geo", "Delete_Grp")
    cmds.rename("geo", f"old_geo")

    # remove all materials in the scene
    Validate.cleanup_materials()

    # get lastest version of path
    lastest_version_path = utils.get_latest_version_in_folder_based(ref_path=ref_path)
    print("recent version : ", ref_path)
    print("lastest version : ", lastest_version_path)

    # reference new file
    cmds.file(lastest_version_path, reference=True, namespace=namespace)
    cmds.parent("{}:geo".format(namespace), "Geometry")

    # transfer skin weight
    cmds.select("old_geo", "{}:geo".format(namespace))
    Skin.fast_copy_weight()

    # rename all transform in old geo back
    cmds.select("old_geo")
    General.sort_by_type(typ="transform")
    list_children = cmds.ls(sl=1)
    list_children = list_children[::-1]
    list_children.remove("old_geo")

    for node in list_children:
        name = Utility.cut(node, hierarchy=True)
        cmds.rename(node, "old_{}".format(name))

    # polish hide
    cmds.setAttr("old_geo.v", False)


def export_selected_skin():
    "Write Selected Maya and ng Skin .json file to quickdata directory"
    QuickData.export_skin_quick()


def import_selected_skin():
    "Read Selected Maya and ng Skin .json file to selected mesh"
    QuickData.import_skin_quick()


def open_quick_data_folder():
    QuickData.open_quick_data_folder()


class AbSymMeshPython:
    def __init__(self):
        self.window_name = "abSymMeshPyWin"
        self.sym_table = []
        self.base_obj = ""
        self.slider_dragging = False

    def ui(self):
        if cmds.window(self.window_name, exists=True):
            cmds.deleteUI(self.window_name)

        cmds.window(self.window_name, title="abSymMesh Python", widthHeight=(250, 520), menuBar=True)
        
        # --- Menus ---
        cmds.menu(label="Operations")
        cmds.menuItem(label="Copy A to B", command=lambda x: self.service_op(2))
        cmds.menuItem(label="Add A to B", command=lambda x: self.service_op(1))
        cmds.menuItem(label="Subtract A from B", command=lambda x: self.service_op(0))
        
        # --- Layout ---
        form = cmds.formLayout(numberOfDivisions=100)
        
        self.axis_grp = cmds.radioButtonGrp(labelArray3=['YZ', 'XZ', 'XY'], numberOfRadioButtons=3, select=1, columnWidth3=[50, 50, 50])
        sep1 = cmds.separator(height=10, style='shelf')
        
        tol_txt = cmds.text(label="Global Tolerance")
        self.tol_fld = cmds.floatField(value=0.001, precision=4)
        
        sbg_btn = cmds.button(label="Select Base Geometry", command=self.set_base_geometry)
        self.sbg_fld = cmds.textField(editable=False, text="")
        
        sep2 = cmds.separator(height=10, style='shelf')
        
        cs_btn = cmds.button(label="Check Symmetry", command=self.check_symmetry_ui)
        self.sm_btn = cmds.button(label="Selection Mirror", enable=False, command=self.mirror_selection)
        self.smv_btn = cmds.button(label="Select Moved Verts", enable=False, command=self.select_moved_verts_ui)
        
        sep3 = cmds.separator(height=10, style='shelf')
        
        self.ms_btn = cmds.button(label="Mirror Selected", enable=False, command=lambda x: self.mirror_logic(flip=False))
        self.fs_btn = cmds.button(label="Flip Selected", enable=False, command=lambda x: self.mirror_logic(flip=True))
        
        # --- Revert Section ---
        self.rs_btn = cmds.button(label="Revert Selected to Base", enable=False, command=self.revert_logic)
        
        # Axis Toggles for Revert
        self.rev_x = cmds.checkBox(label="X", value=True)
        self.rev_y = cmds.checkBox(label="Y", value=True)
        self.rev_z = cmds.checkBox(label="Z", value=True)
        
        self.rev_slider = cmds.floatSlider(min=0, max=1, value=1, step=0.01, 
                                          dragCommand=self.interactive_revert,
                                          changeCommand=self.end_slider_drag)
        
        self.piv_chk = cmds.checkBox(label="Use Pivot as Origin", value=True)
        close_btn = cmds.button(label="Close", command=lambda x: cmds.deleteUI(self.window_name))

        cmds.formLayout(form, edit=True,
            attachForm=[(self.axis_grp, 'top', 10), (self.axis_grp, 'left', 10),
                        (sep1, 'left', 5), (sep1, 'right', 5),
                        (tol_txt, 'left', 10), (self.tol_fld, 'right', 10),
                        (sbg_btn, 'left', 5), (sbg_btn, 'right', 5),
                        (self.sbg_fld, 'left', 5), (self.sbg_fld, 'right', 5),
                        (cs_btn, 'left', 5), (cs_btn, 'right', 5),
                        (self.sm_btn, 'left', 5), (self.sm_btn, 'right', 5),
                        (self.smv_btn, 'left', 5), (self.smv_btn, 'right', 5),
                        (self.ms_btn, 'left', 5), (self.ms_btn, 'right', 5),
                        (self.fs_btn, 'left', 5), (self.fs_btn, 'right', 5),
                        (self.rs_btn, 'left', 5), (self.rs_btn, 'right', 5),
                        (self.rev_x, 'left', 60),
                        (self.rev_slider, 'left', 10), (self.rev_slider, 'right', 10),
                        (self.piv_chk, 'left', 10),
                        (close_btn, 'bottom', 10), (close_btn, 'left', 5), (close_btn, 'right', 5)],
            attachControl=[(sep1, 'top', 5, self.axis_grp),
                           (tol_txt, 'top', 5, sep1),
                           (self.tol_fld, 'top', 5, sep1), (self.tol_fld, 'left', 5, tol_txt),
                           (sbg_btn, 'top', 10, self.tol_fld),
                           (self.sbg_fld, 'top', 2, sbg_btn),
                           (cs_btn, 'top', 10, self.sbg_fld),
                           (self.sm_btn, 'top', 2, cs_btn),
                           (self.smv_btn, 'top', 2, self.sm_btn),
                           (self.ms_btn, 'top', 10, self.smv_btn),
                           (self.fs_btn, 'top', 2, self.ms_btn),
                           (self.rs_btn, 'top', 10, self.fs_btn),
                           (self.rev_x, 'top', 5, self.rs_btn),
                           (self.rev_y, 'top', 5, self.rs_btn), (self.rev_y, 'left', 10, self.rev_x),
                           (self.rev_z, 'top', 5, self.rs_btn), (self.rev_z, 'left', 10, self.rev_y),
                           (self.rev_slider, 'top', 5, self.rev_x),
                           (self.piv_chk, 'top', 10, self.rev_slider)]
        )
        
        cmds.showWindow(self.window_name)

    # --- Geometry Logic ---

    def set_base_geometry(self, *args):
        sel = cmds.ls(sl=True, type='transform')
        if not sel:
            cmds.warning("Select a base polygon mesh.")
            return
        self.base_obj = sel[0]
        self.build_sym_table()
        cmds.textField(self.sbg_fld, e=True, text=self.base_obj)
        for btn in [self.sm_btn, self.smv_btn, self.ms_btn, self.fs_btn, self.rs_btn]:
            cmds.button(btn, e=True, enable=True)

    def build_sym_table(self):
        axis = cmds.radioButtonGrp(self.axis_grp, q=True, select=True) - 1
        tol = cmds.floatField(self.tol_fld, q=True, v=True)
        use_piv = cmds.checkBox(self.piv_chk, q=True, v=True)
        
        self.sym_table = []
        vtx_count = cmds.polyEvaluate(self.base_obj, vertex=True)
        mid = cmds.xform(self.base_obj, q=True, ws=True, t=True)[axis] if use_piv else 0
        
        pos_side, neg_side = [], []
        for i in range(vtx_count):
            p = cmds.xform(f"{self.base_obj}.vtx[{i}]", q=True, ws=True, t=True)
            if (p[axis] - mid) >= -0.000001: pos_side.append((i, p))
            else: neg_side.append((i, p))
        
        a2, a3 = (axis + 1) % 3, (axis + 2) % 3
        matched_neg = set()
        for p_idx, p_pos in pos_side:
            p_off = p_pos[axis] - mid
            if p_off < tol: continue
            for n_idx, n_pos in neg_side:
                if n_idx in matched_neg: continue
                n_off = mid - n_pos[axis]
                if abs(p_off - n_off) <= tol:
                    if abs(p_pos[a2] - n_pos[a2]) < tol and abs(p_pos[a3] - n_pos[a3]) < tol:
                        self.sym_table.extend([p_idx, n_idx])
                        matched_neg.add(n_idx)
                        break
        print(f"Symmetry table built: {len(self.sym_table)//2} pairs.")

    def apply_revert(self, bias):
        sel = cmds.ls(sl=True, fl=True)
        verts = cmds.filterExpand(sel, sm=31)
        if not verts or not self.base_obj: return
        
        ux, uy, uz = [cmds.checkBox(c, q=True, v=True) for c in [self.rev_x, self.rev_y, self.rev_z]]
        
        for v in verts:
            idx = v.split('[')[-1].split(']')[0]
            base_vtx = f"{self.base_obj}.vtx[{idx}]"
            cur_p = cmds.xform(v, q=True, os=True, t=True)
            bs_p = cmds.xform(base_vtx, q=True, os=True, t=True)
            
            new_p = list(cur_p)
            if ux: new_p[0] = bs_p[0] + (cur_p[0] - bs_p[0]) * bias
            if uy: new_p[1] = bs_p[1] + (cur_p[1] - bs_p[1]) * bias
            if uz: new_p[2] = bs_p[2] + (cur_p[2] - bs_p[2]) * bias
            cmds.xform(v, os=True, t=new_p)

    def interactive_revert(self, val):
        if not self.slider_dragging:
            cmds.undoInfo(openChunk=True)
            self.slider_dragging = True
        self.apply_revert(val)

    def end_slider_drag(self, *args):
        self.slider_dragging = False
        cmds.undoInfo(closeChunk=True)

    def mirror_logic(self, flip=False):
        sel = cmds.ls(sl=True, fl=True)
        verts = cmds.filterExpand(sel, sm=31)
        if not verts: return
        
        axis = cmds.radioButtonGrp(self.axis_grp, q=True, select=True) - 1
        use_piv = cmds.checkBox(self.piv_chk, q=True, v=True)
        mid = cmds.xform(self.base_obj, q=True, ws=True, t=True)[axis] if use_piv else 0

        for v in verts:
            idx = int(v.split('[')[-1].split(']')[0])
            m_idx = -1
            if idx in self.sym_table:
                p = self.sym_table.index(idx)
                m_idx = self.sym_table[p+1] if p % 2 == 0 else self.sym_table[p-1]
            
            if m_idx != -1:
                obj = v.split('.')[0]
                m_vtx = f"{obj}.vtx[{m_idx}]"
                pos = cmds.xform(v, q=True, ws=True, t=True)
                new_pos = list(pos)
                new_pos[axis] = 2 * mid - pos[axis]
                
                if flip:
                    m_pos = cmds.xform(m_vtx, q=True, ws=True, t=True)
                    f_pos = list(m_pos)
                    f_pos[axis] = 2 * mid - m_pos[axis]
                    cmds.xform(v, ws=True, t=f_pos)
                
                cmds.xform(m_vtx, ws=True, t=new_pos)

    def select_moved_verts_ui(self, *args):
        sel = cmds.ls(sl=True, type='transform')
        if not sel or not self.base_obj: return
        obj = sel[0]
        tol = cmds.floatField(self.tol_fld, q=True, v=True)
        moved = []
        v_count = cmds.polyEvaluate(obj, v=True)
        for i in range(v_count):
            p1 = cmds.xform(f"{obj}.vtx[{i}]", q=True, os=True, t=True)
            p2 = cmds.xform(f"{self.base_obj}.vtx[{i}]", q=True, os=True, t=True)
            if any(abs(p1[j] - p2[j]) > tol for j in range(3)):
                moved.append(f"{obj}.vtx[{i}]")
        if moved: cmds.select(moved)

    def mirror_selection(self, *args):
        sel = cmds.ls(sl=True, fl=True)
        m_list = []
        for s in sel:
            if '.vtx' in s:
                idx = int(s.split('[')[-1].split(']')[0])
                if idx in self.sym_table:
                    p = self.sym_table.index(idx)
                    m_idx = self.sym_table[p+1] if p % 2 == 0 else self.sym_table[p-1]
                    m_list.append(f"{s.split('.')[0]}.vtx[{m_idx}]")
        if m_list: cmds.select(m_list)

    def check_symmetry_ui(self, *args):
        self.build_sym_table()
        print("Symmetry check complete.")

    def revert_logic(self, *args):
        self.apply_revert(0.0)

    def service_op(self, op):
        pass

def launch_absym():
    ab_sym = AbSymMeshPython()
    ab_sym.ui()


def dnshader():
    def DNshader1(*args):
        sel = cmds.ls(sl=True)
        if cmds.objExists('DNshader1'):
            print('Already Exists')
            if cmds.ls(sl=True):
                print('Assign Texture')
                print(sel)
                cmds.sets(sel, e=True, fe='DNshader1SG')
            else:
                print('')
        else:
            print('DNshader1 does not Exist')
            if cmds.ls(sl=True):
                print('Assign Texture')
                DNshader1 = cmds.shadingNode('blinn', asShader=True, n='DNshader1')
                DNshader1SG = cmds.sets(r=True, nss=True, em=True, n='DNshader1SG')
                cmds.connectAttr(DNshader1 + '.outColor', 'DNshader1SG' + '.surfaceShader')
                cmds.setAttr(DNshader1 + '.color', 1, 0.4, 0.4)
                cmds.setAttr(DNshader1 + '.eccentricity', 0.6)
                cmds.setAttr(DNshader1 + '.specularRollOff', 0.3)
                cmds.setAttr(DNshader1 + '.specularColor', 0.15, 0.15, 0.15)
                cmds.sets(sel, e=True, fe=DNshader1SG)
                cmds.select(sel)
            else:
                print('Make DNshader1')
                DNshader1 = cmds.shadingNode('blinn', asShader=True, n='DNshader1')
                DNshader1SG = cmds.sets(r=True, nss=True, em=True, n='DNshader1SG')
                cmds.connectAttr(DNshader1 + '.outColor', 'DNshader1SG' + '.surfaceShader')
                cmds.setAttr(DNshader1 + '.color', 1, 0.4, 0.4)
                cmds.setAttr(DNshader1 + '.eccentricity', 0.6)
                cmds.setAttr(DNshader1 + '.specularRollOff', 0.3)
                cmds.setAttr(DNshader1 + '.specularColor', 0.15, 0.15, 0.15)
                cmds.select(cl=True)


    def DNshader2(*args):
        sel = cmds.ls(sl=True)
        if cmds.objExists('DNshader2'):
            print('Already Exists')
            if cmds.ls(sl=True):
                print('Assign Texture')
                print(sel)
                cmds.sets(sel, e=True, fe='DNshader2SG')
            else:
                print('')
        else:
            print('DNshader2 does not Exist')
            if cmds.ls(sl=True):
                print('Assign Texture')
                DNshader2 = cmds.shadingNode('blinn', asShader=True, n='DNshader2')
                DNshader2SG = cmds.sets(r=True, nss=True, em=True, n='DNshader2SG')
                cmds.connectAttr(DNshader2 + '.outColor', 'DNshader2SG' + '.surfaceShader')
                cmds.setAttr(DNshader2 + '.color', 1, 0.4, 0.8)
                cmds.setAttr(DNshader2 + '.eccentricity', 0.6)
                cmds.setAttr(DNshader2 + '.specularRollOff', 0.3)
                cmds.setAttr(DNshader2 + '.specularColor', 0.15, 0.15, 0.15)
                cmds.sets(sel, e=True, fe=DNshader2SG)
                cmds.select(sel)
            else:
                print('Make DNshader2')
                DNshader2 = cmds.shadingNode('blinn', asShader=True, n='DNshader2')
                DNshader2SG = cmds.sets(r=True, nss=True, em=True, n='DNshader2SG')
                cmds.connectAttr(DNshader2 + '.outColor', 'DNshader2SG' + '.surfaceShader')
                cmds.setAttr(DNshader2 + '.color', 1, 0.4, 0.8)
                cmds.setAttr(DNshader2 + '.eccentricity', 0.6)
                cmds.setAttr(DNshader2 + '.specularRollOff', 0.3)
                cmds.setAttr(DNshader2 + '.specularColor', 0.15, 0.15, 0.15)
                cmds.select(cl=True)


    def DNshader3(*args):
        sel = cmds.ls(sl=True)
        if cmds.objExists('DNshader3'):
            print('Already Exists')
            if cmds.ls(sl=True):
                print('Assign Texture')
                print(sel)
                cmds.sets(sel, e=True, fe='DNshader3SG')
            else:
                print('')
        else:
            print('DNshader3 does not Exist')
            if cmds.ls(sl=True):
                print('Assign Texture')
                DNshader3 = cmds.shadingNode('blinn', asShader=True, n='DNshader3')
                DNshader3SG = cmds.sets(r=True, nss=True, em=True, n='DNshader3SG')
                cmds.connectAttr(DNshader3 + '.outColor', 'DNshader3SG' + '.surfaceShader')
                cmds.setAttr(DNshader3 + '.color', 0.8, 0.4, 1)
                cmds.setAttr(DNshader3 + '.eccentricity', 0.6)
                cmds.setAttr(DNshader3 + '.specularRollOff', 0.3)
                cmds.setAttr(DNshader3 + '.specularColor', 0.15, 0.15, 0.15)
                cmds.sets(sel, e=True, fe=DNshader3SG)
                cmds.select(sel)
            else:
                print('Make DNshader3')
                DNshader3 = cmds.shadingNode('blinn', asShader=True, n='DNshader3')
                DNshader3SG = cmds.sets(r=True, nss=True, em=True, n='DNshader3SG')
                cmds.connectAttr(DNshader3 + '.outColor', 'DNshader3SG' + '.surfaceShader')
                cmds.setAttr(DNshader3 + '.color', 0.8, 0.4, 1)
                cmds.setAttr(DNshader3 + '.eccentricity', 0.6)
                cmds.setAttr(DNshader3 + '.specularRollOff', 0.3)
                cmds.setAttr(DNshader3 + '.specularColor', 0.15, 0.15, 0.15)
                cmds.select(cl=True)


    def DNshader4(*args):
        sel = cmds.ls(sl=True)
        if cmds.objExists('DNshader4'):
            print('Already Exists')
            if cmds.ls(sl=True):
                print('Assign Texture')
                print(sel)
                cmds.sets(sel, e=True, fe='DNshader4SG')
            else:
                print('')
        else:
            print('DNshader4 does not Exist')
            if cmds.ls(sl=True):
                print('Assign Texture')
                DNshader4 = cmds.shadingNode('blinn', asShader=True, n='DNshader4')
                DNshader4SG = cmds.sets(r=True, nss=True, em=True, n='DNshader4SG')
                cmds.connectAttr(DNshader4 + '.outColor', 'DNshader4SG' + '.surfaceShader')
                cmds.setAttr(DNshader4 + '.color', 0.5, 0.4, 1)
                cmds.setAttr(DNshader4 + '.eccentricity', 0.6)
                cmds.setAttr(DNshader4 + '.specularRollOff', 0.3)
                cmds.setAttr(DNshader4 + '.specularColor', 0.15, 0.15, 0.15)
                cmds.sets(sel, e=True, fe=DNshader4SG)
                cmds.select(sel)
            else:
                print('Make DNshader4')
                DNshader4 = cmds.shadingNode('blinn', asShader=True, n='DNshader4')
                DNshader4SG = cmds.sets(r=True, nss=True, em=True, n='DNshader4SG')
                cmds.connectAttr(DNshader4 + '.outColor', 'DNshader4SG' + '.surfaceShader')
                cmds.setAttr(DNshader4 + '.color', 0.5, 0.4, 1)
                cmds.setAttr(DNshader4 + '.eccentricity', 0.6)
                cmds.setAttr(DNshader4 + '.specularRollOff', 0.3)
                cmds.setAttr(DNshader4 + '.specularColor', 0.15, 0.15, 0.15)
                cmds.select(cl=True)


    def DNshader5(*args):
        sel = cmds.ls(sl=True)
        if cmds.objExists('DNshader5'):
            print('Already Exists')
            if cmds.ls(sl=True):
                print('Assign Texture')
                print(sel)
                cmds.sets(sel, e=True, fe='DNshader5SG')
            else:
                print('')
        else:
            print('DNshader5 does not Exist')
            if cmds.ls(sl=True):
                print('Assign Texture')
                DNshader5 = cmds.shadingNode('blinn', asShader=True, n='DNshader5')
                DNshader5SG = cmds.sets(r=True, nss=True, em=True, n='DNshader5SG')
                cmds.connectAttr(DNshader5 + '.outColor', 'DNshader5SG' + '.surfaceShader')
                cmds.setAttr(DNshader5 + '.color', 0.4, 0.6, 1)
                cmds.setAttr(DNshader5 + '.eccentricity', 0.6)
                cmds.setAttr(DNshader5 + '.specularRollOff', 0.3)
                cmds.setAttr(DNshader5 + '.specularColor', 0.15, 0.15, 0.15)
                cmds.sets(sel, e=True, fe=DNshader5SG)
                cmds.select(sel)
            else:
                print('Make DNshader5')
                DNshader5 = cmds.shadingNode('blinn', asShader=True, n='DNshader5')
                DNshader5SG = cmds.sets(r=True, nss=True, em=True, n='DNshader5SG')
                cmds.connectAttr(DNshader5 + '.outColor', 'DNshader5SG' + '.surfaceShader')
                cmds.setAttr(DNshader5 + '.color', 0.4, 0.6, 1)
                cmds.setAttr(DNshader5 + '.eccentricity', 0.6)
                cmds.setAttr(DNshader5 + '.specularRollOff', 0.3)
                cmds.setAttr(DNshader5 + '.specularColor', 0.15, 0.15, 0.15)
                cmds.select(cl=True)


    def DNshader6(*args):
        sel = cmds.ls(sl=True)
        if cmds.objExists('DNshader6'):
            print('Already Exists')
            if cmds.ls(sl=True):
                print('Assign Texture')
                print(sel)
                cmds.sets(sel, e=True, fe='DNshader6SG')
            else:
                print('')
        else:
            print('DNshader6 does not Exist')
            if cmds.ls(sl=True):
                print('Assign Texture')
                DNshader6 = cmds.shadingNode('blinn', asShader=True, n='DNshader6')
                DNshader6SG = cmds.sets(r=True, nss=True, em=True, n='DNshader6SG')
                cmds.connectAttr(DNshader6 + '.outColor', 'DNshader6SG' + '.surfaceShader')
                cmds.setAttr(DNshader6 + '.color', 0.4, 0.9, 1)
                cmds.setAttr(DNshader6 + '.eccentricity', 0.6)
                cmds.setAttr(DNshader6 + '.specularRollOff', 0.3)
                cmds.setAttr(DNshader6 + '.specularColor', 0.15, 0.15, 0.15)
                cmds.sets(sel, e=True, fe=DNshader6SG)
                cmds.select(sel)
            else:
                print('Make DNshader6')
                DNshader6 = cmds.shadingNode('blinn', asShader=True, n='DNshader6')
                DNshader6SG = cmds.sets(r=True, nss=True, em=True, n='DNshader6SG')
                cmds.connectAttr(DNshader6 + '.outColor', 'DNshader6SG' + '.surfaceShader')
                cmds.setAttr(DNshader6 + '.color', 0.4, 0.9, 1)
                cmds.setAttr(DNshader6 + '.eccentricity', 0.6)
                cmds.setAttr(DNshader6 + '.specularRollOff', 0.3)
                cmds.setAttr(DNshader6 + '.specularColor', 0.15, 0.15, 0.15)
                cmds.select(cl=True)


    def DNshader7(*args):
        sel = cmds.ls(sl=True)
        if cmds.objExists('DNshader7'):
            print('Already Exists')
            if cmds.ls(sl=True):
                print('Assign Texture')
                print(sel)
                cmds.sets(sel, e=True, fe='DNshader7SG')
            else:
                print('')
        else:
            print('DNshader7 does not Exist')
            if cmds.ls(sl=True):
                print('Assign Texture')
                DNshader7 = cmds.shadingNode('blinn', asShader=True, n='DNshader7')
                DNshader7SG = cmds.sets(r=True, nss=True, em=True, n='DNshader7SG')
                cmds.connectAttr(DNshader7 + '.outColor', 'DNshader7SG' + '.surfaceShader')
                cmds.setAttr(DNshader7 + '.color', 0.4, 1, 0.7)
                cmds.setAttr(DNshader7 + '.eccentricity', 0.6)
                cmds.setAttr(DNshader7 + '.specularRollOff', 0.3)
                cmds.setAttr(DNshader7 + '.specularColor', 0.15, 0.15, 0.15)
                cmds.sets(sel, e=True, fe=DNshader7SG)
                cmds.select(sel)
            else:
                print('Make DNshader7')
                DNshader7 = cmds.shadingNode('blinn', asShader=True, n='DNshader7')
                DNshader7SG = cmds.sets(r=True, nss=True, em=True, n='DNshader7SG')
                cmds.connectAttr(DNshader7 + '.outColor', 'DNshader7SG' + '.surfaceShader')
                cmds.setAttr(DNshader7 + '.color', 0.4, 1, 0.7)
                cmds.setAttr(DNshader7 + '.eccentricity', 0.6)
                cmds.setAttr(DNshader7 + '.specularRollOff', 0.3)
                cmds.setAttr(DNshader7 + '.specularColor', 0.15, 0.15, 0.15)
                cmds.select(cl=True)


    def DNshader8(*args):
        sel = cmds.ls(sl=True)
        if cmds.objExists('DNshader8'):
            print('Already Exists')
            if cmds.ls(sl=True):
                print('Assign Texture')
                print(sel)
                cmds.sets(sel, e=True, fe='DNshader8SG')
            else:
                print('')
        else:
            print('DNshader8 does not Exist')
            if cmds.ls(sl=True):
                print('Assign Texture')
                DNshader8 = cmds.shadingNode('blinn', asShader=True, n='DNshader8')
                DNshader8SG = cmds.sets(r=True, nss=True, em=True, n='DNshader8SG')
                cmds.connectAttr(DNshader8 + '.outColor', 'DNshader8SG' + '.surfaceShader')
                cmds.setAttr(DNshader8 + '.color', 0.6, 1, 0.4)
                cmds.setAttr(DNshader8 + '.eccentricity', 0.6)
                cmds.setAttr(DNshader8 + '.specularRollOff', 0.3)
                cmds.setAttr(DNshader8 + '.specularColor', 0.15, 0.15, 0.15)
                cmds.sets(sel, e=True, fe=DNshader8SG)
                cmds.select(sel)
            else:
                print('Make DNshader8')
                DNshader8 = cmds.shadingNode('blinn', asShader=True, n='DNshader8')
                DNshader8SG = cmds.sets(r=True, nss=True, em=True, n='DNshader8SG')
                cmds.connectAttr(DNshader8 + '.outColor', 'DNshader8SG' + '.surfaceShader')
                cmds.setAttr(DNshader8 + '.color', 0.6, 1, 0.4)
                cmds.setAttr(DNshader8 + '.eccentricity', 0.6)
                cmds.setAttr(DNshader8 + '.specularRollOff', 0.3)
                cmds.setAttr(DNshader8 + '.specularColor', 0.15, 0.15, 0.15)
                cmds.select(cl=True)


    def DNshader9(*args):
        sel = cmds.ls(sl=True)
        if cmds.objExists('DNshader9'):
            print('Already Exists')
            if cmds.ls(sl=True):
                print('Assign Texture')
                print(sel)
                cmds.sets(sel, e=True, fe='DNshader9SG')
            else:
                print('')
        else:
            print('DNshader9 does not Exist')
            if cmds.ls(sl=True):
                print('Assign Texture')
                DNshader9 = cmds.shadingNode('blinn', asShader=True, n='DNshader9')
                DNshader9SG = cmds.sets(r=True, nss=True, em=True, n='DNshader9SG')
                cmds.connectAttr(DNshader9 + '.outColor', 'DNshader9SG' + '.surfaceShader')
                cmds.setAttr(DNshader9 + '.color', 1, 0.9, 0.4)
                cmds.setAttr(DNshader9 + '.eccentricity', 0.6)
                cmds.setAttr(DNshader9 + '.specularRollOff', 0.3)
                cmds.setAttr(DNshader9 + '.specularColor', 0.15, 0.15, 0.15)
                cmds.sets(sel, e=True, fe=DNshader9SG)
                cmds.select(sel)
            else:
                print('Make DNshader9')
                DNshader9 = cmds.shadingNode('blinn', asShader=True, n='DNshader9')
                DNshader9SG = cmds.sets(r=True, nss=True, em=True, n='DNshader9SG')
                cmds.connectAttr(DNshader9 + '.outColor', 'DNshader9SG' + '.surfaceShader')
                cmds.setAttr(DNshader9 + '.color', 1, 0.9, 0.4)
                cmds.setAttr(DNshader9 + '.eccentricity', 0.6)
                cmds.setAttr(DNshader9 + '.specularRollOff', 0.3)
                cmds.setAttr(DNshader9 + '.specularColor', 0.15, 0.15, 0.15)
                cmds.select(cl=True)


    def DNshader10(*args):
        sel = cmds.ls(sl=True)
        if cmds.objExists('DNshader10'):
            print('Already Exists')
            if cmds.ls(sl=True):
                print('Assign Texture')
                print(sel)
                cmds.sets(sel, e=True, fe='DNshader10SG')
            else:
                print('')
        else:
            print('DNshader10 does not Exist')
            if cmds.ls(sl=True):
                print('Assign Texture')
                DNshader10 = cmds.shadingNode('blinn', asShader=True, n='DNshader10')
                DNshader10SG = cmds.sets(r=True, nss=True, em=True, n='DNshader10SG')
                cmds.connectAttr(DNshader10 + '.outColor', 'DNshader10SG' + '.surfaceShader')
                cmds.setAttr(DNshader10 + '.color', 1, 0.6, 0.4)
                cmds.setAttr(DNshader10 + '.eccentricity', 0.6)
                cmds.setAttr(DNshader10 + '.specularRollOff', 0.3)
                cmds.setAttr(DNshader10 + '.specularColor', 0.15, 0.15, 0.15)
                cmds.sets(sel, e=True, fe=DNshader10SG)
                cmds.select(sel)
            else:
                print('Make DNshader10')
                DNshader10 = cmds.shadingNode('blinn', asShader=True, n='DNshader10')
                DNshader10SG = cmds.sets(r=True, nss=True, em=True, n='DNshader10SG')
                cmds.connectAttr(DNshader10 + '.outColor', 'DNshader10SG' + '.surfaceShader')
                cmds.setAttr(DNshader10 + '.color', 1, 0.6, 0.4)
                cmds.setAttr(DNshader10 + '.eccentricity', 0.6)
                cmds.setAttr(DNshader10 + '.specularRollOff', 0.3)
                cmds.setAttr(DNshader10 + '.specularColor', 0.15, 0.15, 0.15)
                cmds.select(cl=True)


    def AssignShadeLoop(*args):
        sel = cmds.ls(sl=True)
        if cmds.objExists('DNshader1'):
            print('DNshader1 Already Exists')
        else:
            DNshader1()

        if cmds.objExists('DNshader2'):
            print('DNshader2 Already Exists')
        else:
            DNshader2()

        if cmds.objExists('DNshader3'):
            print('DNshader3 Already Exists')
        else:
            DNshader3()

        if cmds.objExists('DNshader4'):
            print('DNshader4 Already Exists')
        else:
            DNshader4()

        if cmds.objExists('DNshader5'):
            print('DNshader5 Already Exists')
        else:
            DNshader5()

        if cmds.objExists('DNshader6'):
            print('DNshader6 Already Exists')
        else:
            DNshader6()

        if cmds.objExists('DNshader7'):
            print('DNshader7 Already Exists')
        else:
            DNshader7()

        if cmds.objExists('DNshader8'):
            print('DNshader8 Already Exists')
        else:
            DNshader8()

        if cmds.objExists('DNshader9'):
            print('DNshader9 Already Exists')
        else:
            DNshader9()

        if cmds.objExists('DNshader10'):
            print('DNshader10 Already Exists')
        else:
            DNshader10()

        if cmds.ls(sl=True):
            for i in range(len(sel)):
                cmds.sets(sel[i], e=True, fe='DNshader' + str((i) % 10 + 1) + 'SG')
        else:
            print('Make All DNshader')
        cmds.select(cl=True)


    def DNshaderSkin(*args):
        sel = cmds.ls(sl=True)
        if cmds.objExists('DNshaderSkin'):
            print('Already Exists')
            if cmds.ls(sl=True):
                print('Assign Texture')
                print(sel)
                cmds.sets(sel, e=True, fe='DNshaderSkinSG')
            else:
                print('')
        else:
            print('DNshaderSkin does not Exist')
            if cmds.ls(sl=True):
                print('Assign Texture')
                DNshaderSkin = cmds.shadingNode('blinn', asShader=True, n='DNshaderSkin')
                DNshaderSkinSG = cmds.sets(r=True, nss=True, em=True, n='DNshaderSkinSG')
                cmds.connectAttr(DNshaderSkin + '.outColor', 'DNshaderSkinSG' + '.surfaceShader')
                cmds.setAttr(DNshaderSkin + '.color', 1, 0.685, 0.55)
                cmds.setAttr(DNshaderSkin + '.diffuse', 1)
                cmds.setAttr(DNshaderSkin + '.translucence', 0.05)
                cmds.setAttr(DNshaderSkin + '.eccentricity', 0.3)
                cmds.setAttr(DNshaderSkin + '.specularRollOff', 0.7)
                cmds.setAttr(DNshaderSkin + '.specularColor', 0.15, 0.15, 0.15)
                cmds.sets(sel, e=True, fe=DNshaderSkinSG)
                cmds.select(sel)
            else:
                print('Make DNshaderSkin')
                DNshaderSkin = cmds.shadingNode('blinn', asShader=True, n='DNshaderSkin')
                DNshaderSkinSG = cmds.sets(r=True, nss=True, em=True, n='DNshaderSkinSG')
                cmds.connectAttr(DNshaderSkin + '.outColor', 'DNshaderSkinSG' + '.surfaceShader')
                cmds.setAttr(DNshaderSkin + '.color', 1, 0.685, 0.55)
                cmds.setAttr(DNshaderSkin + '.diffuse', 1)
                cmds.setAttr(DNshaderSkin + '.translucence', 0.05)
                cmds.setAttr(DNshaderSkin + '.eccentricity', 0.3)
                cmds.setAttr(DNshaderSkin + '.specularRollOff', 0.7)
                cmds.setAttr(DNshaderSkin + '.specularColor', 0.15, 0.15, 0.15)


    def GrayShader1(*args):
        sel = cmds.ls(sl=True)
        if cmds.objExists('GrayShader1'):
            print('Already Exists')
            if sel:
                print('Assign Texture')
                print(sel)
                cmds.sets(sel, e=True, fe='GrayShader1SG')
            else:
                print('')
        else:
            print('GrayShader1 does not Exist')
            if sel:
                print('Assign Texture')
                GrayShader1 = cmds.shadingNode('blinn', asShader=True, n='GrayShader1')
                GrayShader1SG = cmds.sets(r=True, nss=True, em=True, n='GrayShader1SG')
                cmds.connectAttr(GrayShader1 + '.outColor', 'GrayShader1SG' + '.surfaceShader')
                cmds.setAttr(GrayShader1 + '.color', 0, 0, 0)
                cmds.setAttr(GrayShader1 + '.specularColor', 0.15, 0.15, 0.15)
                cmds.setAttr(GrayShader1 + '.eccentricity', 1.0)
                cmds.setAttr(GrayShader1 + '.specularRollOff', 0.3)
                cmds.sets(sel, e=True, fe=GrayShader1SG)
                cmds.select(sel)
            else:
                print('Make GrayShader1')
                GrayShader1 = cmds.shadingNode('blinn', asShader=True, n='GrayShader1')
                GrayShader1SG = cmds.sets(r=True, nss=True, em=True, n='GrayShader1SG')
                cmds.connectAttr(GrayShader1 + '.outColor', 'GrayShader1SG' + '.surfaceShader')
                cmds.setAttr(GrayShader1 + '.color', 0, 0, 0)
                cmds.setAttr(GrayShader1 + '.specularColor', 0.15, 0.15, 0.15)
                cmds.setAttr(GrayShader1 + '.eccentricity', 1.0)
                cmds.setAttr(GrayShader1 + '.specularRollOff', 0.3)


    def GrayShader2(*args):
        sel = cmds.ls(sl=True)
        if cmds.objExists('GrayShader2'):
            print('Already Exists')
            if sel:
                print('Assign Texture')
                print(sel)
                cmds.sets(sel, e=True, fe='GrayShader2SG')
            else:
                print('')
        else:
            print('GrayShader2 does not Exist')
            if sel:
                print('Assign Texture')
                GrayShader2 = cmds.shadingNode('blinn', asShader=True, n='GrayShader2')
                GrayShader2SG = cmds.sets(r=True, nss=True, em=True, n='GrayShader2SG')
                cmds.connectAttr(GrayShader2 + '.outColor', 'GrayShader2SG' + '.surfaceShader')
                cmds.setAttr(GrayShader2 + '.color', 0.25, 0.25, 0.25)
                cmds.setAttr(GrayShader2 + '.specularColor', 0.15, 0.15, 0.15)
                cmds.setAttr(GrayShader2 + '.eccentricity', 1.0)
                cmds.setAttr(GrayShader2 + '.specularRollOff', 0.3)
                cmds.sets(sel, e=True, fe=GrayShader2SG)
                cmds.select(sel)
            else:
                print('Make GrayShader2')
                GrayShader2 = cmds.shadingNode('blinn', asShader=True, n='GrayShader2')
                GrayShader2SG = cmds.sets(r=True, nss=True, em=True, n='GrayShader2SG')
                cmds.connectAttr(GrayShader2 + '.outColor', 'GrayShader2SG' + '.surfaceShader')
                cmds.setAttr(GrayShader2 + '.color', 0.25, 0.25, 0.25)
                cmds.setAttr(GrayShader2 + '.specularColor', 0.15, 0.15, 0.15)
                cmds.setAttr(GrayShader2 + '.eccentricity', 1.0)
                cmds.setAttr(GrayShader2 + '.specularRollOff', 0.3)


    def GrayShader3(*args):
        sel = cmds.ls(sl=True)
        if cmds.objExists('GrayShader3'):
            print('Already Exists')
            if sel:
                print('Assign Texture')
                print(sel)
                cmds.sets(sel, e=True, fe='GrayShader3SG')
            else:
                print('')
        else:
            print('GrayShader3 does not Exist')
            if sel:
                print('Assign Texture')
                GrayShader3 = cmds.shadingNode('blinn', asShader=True, n='GrayShader3')
                GrayShader3SG = cmds.sets(r=True, nss=True, em=True, n='GrayShader3SG')
                cmds.connectAttr(GrayShader3 + '.outColor', 'GrayShader3SG' + '.surfaceShader')
                cmds.setAttr(GrayShader3 + '.color', 0.5, 0.5, 0.5)
                cmds.setAttr(GrayShader3 + '.specularColor', 0.15, 0.15, 0.15)
                cmds.setAttr(GrayShader3 + '.eccentricity', 1.0)
                cmds.setAttr(GrayShader3 + '.specularRollOff', 0.3)
                cmds.sets(sel, e=True, fe=GrayShader3SG)
                cmds.select(sel)
            else:
                print('Make GrayShader3')
                GrayShader3 = cmds.shadingNode('blinn', asShader=True, n='GrayShader3')
                GrayShader3SG = cmds.sets(r=True, nss=True, em=True, n='GrayShader3SG')
                cmds.connectAttr(GrayShader3 + '.outColor', 'GrayShader3SG' + '.surfaceShader')
                cmds.setAttr(GrayShader3 + '.color', 0.5, 0.5, 0.5)
                cmds.setAttr(GrayShader3 + '.specularColor', 0.15, 0.15, 0.15)
                cmds.setAttr(GrayShader3 + '.eccentricity', 1.0)
                cmds.setAttr(GrayShader3 + '.specularRollOff', 0.3)


    def GrayShader4(*args):
        sel = cmds.ls(sl=True)
        if cmds.objExists('GrayShader4'):
            print('Already Exists')
            if sel:
                print('Assign Texture')
                print(sel)
                cmds.sets(sel, e=True, fe='GrayShader4SG')
            else:
                print('')
        else:
            print('GrayShader4 does not Exist')
            if sel:
                print('Assign Texture')
                GrayShader4 = cmds.shadingNode('blinn', asShader=True, n='GrayShader4')
                GrayShader4SG = cmds.sets(r=True, nss=True, em=True, n='GrayShader4SG')
                cmds.connectAttr(GrayShader4 + '.outColor', 'GrayShader4SG' + '.surfaceShader')
                cmds.setAttr(GrayShader4 + '.color', 0.75, 0.75, 0.75)
                cmds.setAttr(GrayShader4 + '.specularColor', 0.15, 0.15, 0.15)
                cmds.setAttr(GrayShader4 + '.eccentricity', 1.0)
                cmds.setAttr(GrayShader4 + '.specularRollOff', 0.3)
                cmds.sets(sel, e=True, fe=GrayShader4SG)
                cmds.select(sel)
            else:
                print('Make GrayShader4')
                GrayShader4 = cmds.shadingNode('blinn', asShader=True, n='GrayShader4')
                GrayShader4SG = cmds.sets(r=True, nss=True, em=True, n='GrayShader4SG')
                cmds.connectAttr(GrayShader4 + '.outColor', 'GrayShader4SG' + '.surfaceShader')
                cmds.setAttr(GrayShader4 + '.color', 0.75, 0.75, 0.75)
                cmds.setAttr(GrayShader4 + '.specularColor', 0.15, 0.15, 0.15)
                cmds.setAttr(GrayShader4 + '.eccentricity', 1.0)
                cmds.setAttr(GrayShader4 + '.specularRollOff', 0.3)


    def GrayShader5(*args):
        sel = cmds.ls(sl=True)
        if cmds.objExists('GrayShader5'):
            print('Already Exists')
            if sel:
                print('Assign Texture')
                print(sel)
                cmds.sets(sel, e=True, fe='GrayShader5SG')
            else:
                print('')
        else:
            print('GrayShader5 does not Exist')
            if sel:
                print('Assign Texture')
                GrayShader5 = cmds.shadingNode('blinn', asShader=True, n='GrayShader5')
                GrayShader5SG = cmds.sets(r=True, nss=True, em=True, n='GrayShader5SG')
                cmds.connectAttr(GrayShader5 + '.outColor', GrayShader5SG + '.surfaceShader')
                cmds.setAttr(GrayShader5 + '.color', 1, 1, 1)
                cmds.setAttr(GrayShader5 + '.specularColor', 0.15, 0.15, 0.15)
                cmds.setAttr(GrayShader5 + '.eccentricity', 1.0)
                cmds.setAttr(GrayShader5 + '.specularRollOff', 0.3)
                cmds.sets(sel, e=True, fe=GrayShader5SG)
                cmds.select(sel)
            else:
                print('Make GrayShader5')
                GrayShader5 = cmds.shadingNode('blinn', asShader=True, n='GrayShader5')
                GrayShader5SG = cmds.sets(r=True, nss=True, em=True, n='GrayShader5SG')
                cmds.connectAttr(GrayShader5 + '.outColor', GrayShader5SG + '.surfaceShader')
                cmds.setAttr(GrayShader5 + '.color', 1, 1, 1)
                cmds.setAttr(GrayShader5 + '.specularColor', 0.75, 0.75, 0.75)
                cmds.setAttr(GrayShader5 + '.eccentricity', 1.0)
                cmds.setAttr(GrayShader5 + '.specularRollOff', 0.3)


    def TransparencyFUN(*args):
        sel = cmds.ls(sl=True)
        if cmds.objExists('Transparency'):
            print('Already Exists')
            if sel:
                print('Assign Texture')
                print(sel)
                cmds.sets(sel, e=True, fe='TransparencySG')
            else:
                print('')
        else:
            print('Transparency does not Exist')
            if sel:
                print('Assign Texture')
                Transparency = cmds.shadingNode('blinn', asShader=True, n='Transparency')
                TransparencySG = cmds.sets(r=True, nss=True, em=True, n='TransparencySG')
                cmds.connectAttr(Transparency + '.outColor', TransparencySG + '.surfaceShader')
                cmds.setAttr(Transparency + '.color', 1, 1, 1)
                cmds.setAttr(Transparency + '.transparency', 1, 1, 1)
                cmds.setAttr(Transparency + '.specularColor', 0.15, 0.15, 0.15)
                cmds.setAttr(Transparency + '.eccentricity', 1.0)
                cmds.setAttr(Transparency + '.specularRollOff', 0.3)
                cmds.sets(sel, e=True, fe=TransparencySG)
                cmds.select(sel)
            else:
                print('Make Transparency')
                Transparency = cmds.shadingNode('blinn', asShader=True, n='Transparency')
                TransparencySG = cmds.sets(r=True, nss=True, em=True, n='TransparencySG')
                cmds.connectAttr(Transparency + '.outColor', TransparencySG + '.surfaceShader')
                cmds.setAttr(Transparency + '.color', 1, 1, 1)
                cmds.setAttr(Transparency + '.specularColor', 0.15, 0.15, 0.15)
                cmds.setAttr(Transparency + '.eccentricity', 1.0)
                cmds.setAttr(Transparency + '.specularRollOff', 0.3)


    def DeleteUnusedNodes(*args):
        mel.eval('MLdeleteUnused;')

    def SwitchToViewport2(*args):
        # Check DNshader 1-10
        DNshader = []
        addColor = 0.2
        for i in range(1, 11):
            if cmds.objExists('DNshader' + str(i)):
                DNshader.append('DNshader' + str(i))
            else:
                print('DNshader' + str(i) + ' is not Exists')

        if cmds.objExists('DNshaderSkin'):
            DNshader.append('DNshaderSkin')
        else:
            print('DNshaderSkin is not Exists')

        print(DNshader)

        for i in range(len(DNshader)):
            Color = cmds.getAttr(DNshader[i] + '.color')
            cmds.setAttr(DNshader[i] + '.color', Color[0][0], Color[0][1] - addColor, Color[0][2] - addColor)
            cmds.setAttr(DNshader[i] + '.diffuse', 1)


    def SwitchToLegacy(*args):
        # Check DNshader 1-10
        DNshader = []
        addColor = 0.2
        for i in range(1, 11):
            if cmds.objExists('DNshader' + str(i)):
                DNshader.append('DNshader' + str(i))
            else:
                print('DNshader' + str(i) + ' is not Exists')

        if cmds.objExists('DNshaderSkin'):
            DNshader.append('DNshaderSkin')
        else:
            print('DNshaderSkin is not Exists')

        print(DNshader)

        for i in range(len(DNshader)):
            Color = cmds.getAttr(DNshader[i] + '.color')
            cmds.setAttr(DNshader[i] + '.color', Color[0][0], Color[0][1] + addColor, Color[0][2] + addColor)
            cmds.setAttr(DNshader[i] + '.diffuse', 0.8)


    if cmds.window('AssignDNshader', q=True, ex=True):
        cmds.deleteUI('AssignDNshader')

    window = cmds.window('AssignDNshader', title="Assign DNshader (Blinn)", widthHeight=(100, 150))
    cmds.columnLayout(adj=True)

    cmds.button(label='Red', bgc=(1.0, 0.0, 0.0), c=DNshader1)
    cmds.button(label='Pink', bgc=(1.0, 0.2, 1.0), c=DNshader2)
    cmds.button(label='Purple', bgc=(0.5, 0.0, 0.9), c=DNshader3)
    cmds.button(label='DarkPurple', bgc=(0.25, 0.0, 0.5), c=DNshader4)
    cmds.button(label='Blue', bgc=(0.0, 0.5, 1.0), c=DNshader5)
    cmds.button(label='LightBlue', bgc=(0.5, 1.0, 1.0), c=DNshader6)
    cmds.button(label='LightGreen', bgc=(0.1, 1.0, 0.8), c=DNshader7)
    cmds.button(label='Green', bgc=(0.0, 1.0, 0.0), c=DNshader8)
    cmds.button(label='Yellow', bgc=(1.0, 1.0, 0.0), c=DNshader9)
    cmds.button(label='Orange', bgc=(1.0, 0.5, 0.0), c=DNshader10)
    cmds.button(label='Skin', bgc=(1.0, 0.5, 0.5), c=DNshaderSkin)
    cmds.button(label='Black', bgc=(0.1, 0.1, 0.1), c=GrayShader1)
    cmds.button(label='Dark', bgc=(0.25, 0.25, 0.25), c=GrayShader2)
    cmds.button(label='Gray', bgc=(0.4, 0.4, 0.4), c=GrayShader3)
    cmds.button(label='LightGray', bgc=(0.6, 0.6, 0.6), c=GrayShader4)
    cmds.button(label='White', bgc=(0.8, 0.8, 0.8), c=GrayShader5)
    cmds.button(label='Transparency', bgc=(1.0, 1.0, 1.0), c=TransparencyFUN)
    cmds.separator(width=50, height=10, style='out')
    cmds.button(label='Assign Shade Loop', c=AssignShadeLoop)
    cmds.separator(width=50, height=10, style='out')
    cmds.button(label='Delete Unused Nodes', c=DeleteUnusedNodes)
    # cmds.button( label='Switch to Viewport 2.0' , c = SwitchToViewport2 )
    # cmds.button( label='Switch to Legacy Viewport' , c = SwitchToLegacy )

    cmds.showWindow('AssignDNshader')
    cmds.window('AssignDNshader', e=True, w=250, h=520, tlc=[400, 1100])



def select_object_by_name():
    # 1. ดึงรายชื่อวัตถุที่กำลังเลือกอยู่
    selected_objects = cmds.ls(selection=True)

    if not selected_objects:
        cmds.warning("กรุณาเลือกวัตถุก่อนรันสคริปต์!")
    else:
        # 2. เปิดหน้าต่างป๊อปอัปให้พิมพ์ Expression เอง
        result = cmds.promptDialog(
            title='Select by Name Expression',
            message='ใส่คำค้นหา (ใช้ * ได้ เช่น *mouth, eye*):',
            button=['OK', 'Cancel'],
            defaultButton='OK',
            cancelButton='Cancel',
            dismissString='Cancel'
        )
        
        # ถ้ากด OK ถึงจะทำงานต่อ
        if result == 'OK':
            # ดึงข้อความที่ผู้ใช้พิมพ์
            search_expr = cmds.promptDialog(query=True, text=True)
            
            if search_expr:
                # 3. คัดกรองวัตถุด้วย fnmatch (รองรับการใช้ * ในการค้นหา)
                # fnmatch จะช่วยเช็ค pattern เช่น *mouth ได้แม่นยำ
                matching_objects = [obj for obj in selected_objects if fnmatch.fnmatch(obj, search_expr)]
                
                if matching_objects:
                    # 4. เลือกวัตถุที่ตรงเงื่อนไข
                    cmds.select(matching_objects, replace=True)
                    print(f"เลือกวัตถุสำเร็จ {len(matching_objects)} ชิ้น ตามเงื่อนไข '{search_expr}'")
                else:
                    cmds.select(clear=True)
                    cmds.warning(f"ไม่พบวัตถุที่ตรงกับเงื่อนไข '{search_expr}' ในกลุ่มที่เลือก")
            else:
                cmds.warning("ไม่ได้พิมพ์คำค้นหาใดๆ")