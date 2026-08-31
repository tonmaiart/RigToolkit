"""Maya-side operations for BeamSmear.

Kept independent of the Qt widgets in interface.py so the scene logic can be
read/tested without a live UI. Every smear target lives as an alias on a
"BeamSmear_bs" blendShape node created on the target mesh -- multiple smears
can share the same node, so most lookups here go by node+alias rather than
by a single "current node".
"""

import pymel.core as pm
import maya.cmds as mc

from tmlib.core import BlendShape

NODE_NAME = "BeamSmear_bs"


def duplicate_orig_shape(obj, name):
    """Duplicate obj into a static target mesh named `name`.

    If obj is already deformed (has an Orig/intermediate shape), keep only
    that Orig shape as the result -- this makes a target sculpted on a
    deformed mesh capture the true undeformed base rather than the live
    deformed result.
    """
    dup = pm.duplicate(obj, n=name)[0]

    children = pm.listRelatives(dup, c=True, typ="transform")
    if children:
        pm.delete(children)

    shapes = pm.listRelatives(dup, c=True, s=True) or []
    has_orig = any("Orig" in shape.shortName() for shape in shapes)

    if has_orig:
        kept_orig = None
        for shape in shapes:
            shape_name = shape.shortName()
            if "Orig" in shape_name and kept_orig is None:
                kept_orig = shape_name
                pm.setAttr("{}.intermediateObject".format(shape_name), False)
            else:
                pm.delete(shape)

    return dup


def get_beam_smear_node(mesh):
    """Return mesh's own BeamSmear blendShape node, or None if it doesn't have one yet."""
    for node_name in BlendShape.get_blendshape_nodes(mesh):
        if NODE_NAME in node_name:
            return node_name
    return None


def get_all_blend_shape_nodes():
    return [
        node.shortName() for node in pm.ls(typ="blendShape") if NODE_NAME in node.shortName()
    ]


def get_all_smear_names(blend_shape_nodes=None):
    if blend_shape_nodes is None:
        blend_shape_nodes = get_all_blend_shape_nodes()

    names = []
    for node in blend_shape_nodes:
        aliases = mc.aliasAttr(node, query=True) or []
        names += aliases[::2]

    return sorted(set(names))


def get_blend_shape_nodes_for_smear(smear_name):
    """All BeamSmear nodes that currently carry a target named smear_name."""
    if not smear_name:
        return []

    nodes = []
    for node in get_all_blend_shape_nodes():
        aliases = mc.aliasAttr(node, query=True) or []
        if smear_name in aliases[::2]:
            nodes.append(node)

    return nodes


def get_active_meshes(smear_name, blend_shape_nodes):
    if not smear_name or not blend_shape_nodes:
        return []

    node = blend_shape_nodes[0]
    attr_name = "{}Meshes".format(smear_name)

    if not mc.attributeQuery(attr_name, node=node, exists=True):
        return []

    return mc.listConnections("{}.{}".format(node, attr_name), s=True, d=False) or []


def connect_active_mesh(target_node, mesh, smear_name):
    """Track mesh as one of smear_name's active meshes via a message-attribute connection."""
    attr_name = "{}Meshes".format(smear_name)
    attr_path = "{}.{}".format(target_node, attr_name)

    if not mc.attributeQuery(attr_name, node=target_node, exists=True):
        mc.addAttr(target_node, k=True, at="message", multi=True, ln=attr_name)

    mesh_message = "{}.message".format(mesh)
    existing = mc.listConnections(attr_path, plugs=True) or []

    if any(mc.isConnected(mesh_message, plug) for plug in existing):
        return

    dst_attr = "{}[{}]".format(attr_path, len(existing))
    mc.connectAttr(mesh_message, dst_attr)


def disconnect_active_mesh(target_node, mesh, smear_name):
    attr_name = "{}Meshes".format(smear_name)
    attr_path = "{}.{}".format(target_node, attr_name)

    if not mc.attributeQuery(attr_name, node=target_node, exists=True):
        return

    mesh_message = "{}.message".format(mesh)
    for plug in mc.listConnections(attr_path, plugs=True) or []:
        if mc.isConnected(mesh_message, plug):
            mc.disconnectAttr(mesh_message, plug)


def ensure_smear_target(mesh, smear_name):
    """Create mesh's BeamSmear node/target for smear_name if it doesn't exist yet, and mark mesh active. Returns the blendShape node name."""
    target_node = get_beam_smear_node(mesh)

    if target_node is None:
        target_node = mc.blendShape(mesh, name=NODE_NAME)[0]
        mc.setAttr("{}.envelope".format(target_node), lock=True)

    existing_names = (mc.aliasAttr(target_node, query=True) or [])[::2]

    if smear_name not in existing_names:
        target_mesh = duplicate_orig_shape(mesh, smear_name)
        target_mesh_name = str(target_mesh)

        target_index = mc.getAttr("{}.w".format(target_node), size=True)

        mc.blendShape(
            target_node,
            edit=True,
            topologyCheck=False,
            target=(mesh, target_index, target_mesh_name, 1.0),
            weight=(target_index, 1.0),
        )

        pm.delete(target_mesh_name)

    connect_active_mesh(target_node, mesh, smear_name)

    return target_node


def validate_mesh_selection(selection):
    if not selection:
        pm.confirmDialog(message="Please select mesh before adding a new smear.")
        return False

    for sel in selection:
        if not pm.listRelatives(sel, c=True, typ="mesh"):
            pm.confirmDialog(message="Selection must be mesh.")
            return False

    return True


def get_default_smear_name():
    existing = get_all_smear_names()
    count = 1
    while True:
        name = "smear{:02d}".format(count)
        if name not in existing:
            return name
        count += 1


def prompt_smear_name(title, message, default_text):
    result = mc.promptDialog(
        title=title,
        text=default_text,
        message=message,
        button=["OK", "Cancel"],
        defaultButton="OK",
        cancelButton="Cancel",
        dismissString="Cancel",
    )

    if result != "OK":
        return None

    return mc.promptDialog(query=True, text=True)


def create_smear(selection):
    """Prompt for a name and create a new smear target on every selected mesh.

    Returns the new smear name, or None if cancelled/invalid.
    """
    if not validate_mesh_selection(selection):
        return None

    smear_name = prompt_smear_name(
        "New Smear", "Enter Name:", get_default_smear_name()
    )
    if not smear_name:
        return None

    for mesh in selection:
        ensure_smear_target(mesh, smear_name)

    pm.inViewMessage(
        amg="<hl>Created New Smear : {}</hl>".format(smear_name),
        pos="botCenter",
        fade=True,
    )

    return smear_name


def add_active_mesh(selection, smear_name):
    """Add each selected mesh as an active mesh contributing to smear_name."""
    for mesh in selection:
        ensure_smear_target(mesh, smear_name)

    pm.inViewMessage(amg="<hl>Added Active Mesh</hl>", pos="botCenter", fade=True)


def remove_active_mesh(meshes, smear_name, blend_shape_nodes):
    """Disconnect the given meshes from smear_name without deleting their sculpted target."""
    for node in blend_shape_nodes:
        for mesh in meshes:
            disconnect_active_mesh(node, mesh, smear_name)

    pm.inViewMessage(amg="<hl>Removed Active Mesh</hl>", pos="botCenter", fade=True)


def delete_smear(smear_name, blend_shape_nodes):
    """Remove smear_name's target from every node that has it (not the node itself, which may hold other smears too)."""
    for node in blend_shape_nodes:
        BlendShape.delete_blendshape_target(node, smear_name)

    pm.inViewMessage(
        amg="<hl>Deleted Smear : {}</hl>".format(smear_name), pos="botCenter", fade=True
    )


def rename_smear(old_name, new_name, blend_shape_nodes):
    for node in blend_shape_nodes:
        BlendShape.rename_blendshape_target(node, old_name, new_name)


def prompt_rename_smear(old_name):
    return prompt_smear_name(
        "Rename Smear", "Rename {} to:".format(old_name), old_name
    )


def get_smear_weight(smear_name, blend_shape_nodes):
    if not smear_name or not blend_shape_nodes:
        return None
    return pm.getAttr("{}.{}".format(blend_shape_nodes[0], smear_name))


def set_smear_weight(smear_name, blend_shape_nodes, value):
    for node in blend_shape_nodes:
        pm.setAttr("{}.{}".format(node, smear_name), value)


def lock_other_smears(smear_name, blend_shape_nodes):
    """Keyable/unlocked only for the active smear; all others locked so accidental scrubs don't touch them."""
    for node in blend_shape_nodes:
        aliases = mc.aliasAttr(node, query=True) or []
        for name in aliases[::2]:
            is_current = name == smear_name
            pm.setAttr("{}.{}".format(node, name), keyable=is_current, lock=not is_current)


def get_max_keyframe_time(attr):
    times = mc.keyframe(attr, q=True, timeChange=True) or []
    values = mc.keyframe(attr, q=True, valueChange=True) or []

    if not times:
        return pm.currentTime(q=True)

    return max(zip(times, values), key=lambda item: item[1])[0]


def set_key(smear_name, blend_shape_nodes):
    for node in blend_shape_nodes:
        mc.setKeyframe("{}.{}".format(node, smear_name))

    pm.inViewMessage(
        amg="<hl>Set Keyframe : {}</hl>".format(smear_name), pos="botCenter", fade=True
    )


def enter_edit_mode(smear_name, blend_shape_nodes):
    for node in blend_shape_nodes:
        # Equivalent of: sculptTarget -e -target -1 blendShape1;
        mc.sculptTarget(node, edit=True, target=-1)

        aliases = mc.aliasAttr(node, query=True) or []
        alias_dict = {aliases[i]: aliases[i + 1] for i in range(0, len(aliases), 2)}

        if smear_name in alias_dict:
            index = int(alias_dict[smear_name].split("[")[1].split("]")[0])
            mc.sculptTarget(node, edit=True, target=index)
        else:
            print("Target '{}' not found in '{}'".format(smear_name, node))


def select_nodes(nodes):
    pm.select(nodes)
