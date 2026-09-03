"""Maya-side operations for RigUpdater.

Swaps a rig's referenced model for an updated reference while carrying skin
weights across the mapped meshes. Kept independent of interface.py's Qt
widgets so the logic can run headless. Detection is deliberately manual --
the user loads the Source (current) and Update (new) references from
whatever node they have selected in the viewport, rather than the tool
guessing which reference is which the way the old
`QuickScript/custom_library/DECK_Rig.py`'s `update_model_for_rig` did
(`cmds.select("*:geo")` + auto latest-version-in-folder lookup).
"""

import os
import json

import maya.cmds as cmds

from tmlib.core import SkinWeight, Utility, Validate, Selection, QuickData

from MergeSkin import function as merge_skin_function

# Matches the top-level transform name every character rig's referenced
# model is expected to use, same convention the old auto-detect script
# relied on (it selected "*:geo" then renamed it "old_geo").
GEO_GROUP_NAME = "geo"

SESSION_FILE_NAME = "RigUpdaterSession.json"


def _build_ref_info(ref_node, ref_path):
    namespace = cmds.referenceQuery(ref_node, namespace=True).lstrip(":")

    geo_group = "{}:{}".format(namespace, GEO_GROUP_NAME)
    if not cmds.objExists(geo_group):
        return None

    return {
        "ref_node": ref_node,
        "ref_path": ref_path,
        "ref_name": os.path.basename(ref_path),
        "namespace": namespace,
        "geo_group": geo_group,
    }


def get_reference_info(node):
    """Resolve the reference node/file/namespace/geo-group for a selected node.

    Returns None if node isn't part of a reference, or the reference doesn't
    contain the expected top-level "geo" group.
    """
    if not cmds.objExists(node):
        return None

    if not cmds.referenceQuery(node, isNodeReferenced=True):
        return None

    ref_node = cmds.referenceQuery(node, referenceNode=True)
    ref_path = cmds.referenceQuery(ref_node, filename=True)
    return _build_ref_info(ref_node, ref_path)


def get_reference_info_by_path(ref_path):
    """Resolve reference info for a reference file already loaded in the scene.

    Used to restore a saved RigData session without requiring the user to
    reselect a node -- returns None if that file isn't referenced (loaded)
    in the current scene any more.
    """
    if not ref_path:
        return None

    target = os.path.normpath(ref_path)
    for ref_node in cmds.ls(type="reference"):
        if ref_node == "sharedReferenceNode":
            continue
        try:
            if not cmds.referenceQuery(ref_node, isLoaded=True):
                continue
            candidate_path = cmds.referenceQuery(ref_node, filename=True)
        except RuntimeError:
            continue

        if os.path.normpath(candidate_path) == target:
            return _build_ref_info(ref_node, candidate_path)

    return None


def list_geo_meshes(geo_group):
    """Full-path mesh transforms nested under geo_group."""
    return Selection.get_children_mesh(geo_group)


def _basename(path):
    return Utility.cut(path, hierarchy=True, namespace=True)


def auto_match(source_geo_list, update_geo_list):
    """Match Source Geo to Update Geo by basename (namespace/hierarchy-stripped).

    Returns {update_geo_path: [source_geo_path]} for every exact match;
    Update Geo entries with no matching name are simply absent, left for
    the user to resolve manually via "Resolve Selected".
    """
    source_by_name = {}
    for source in source_geo_list:
        source_by_name.setdefault(_basename(source), source)

    matches = {}
    for update_geo in update_geo_list:
        source = source_by_name.get(_basename(update_geo))
        if source:
            matches[update_geo] = [source]

    return matches


def _get_skin_cluster(mesh):
    skin_clusters = cmds.ls(cmds.listHistory(mesh), type="skinCluster")
    return skin_clusters[0] if skin_clusters else None


def _ensure_skin_cluster_for_merge(sources, target):
    """Bind target first if it has no skinCluster yet.

    MergeSkin.merge_skin only transfers weights onto an EXISTING
    skinCluster on target -- it never creates one, since its original
    use case (merging extra base meshes into an already-bound mesh)
    assumes that. Rig Updater's merge case (several Source Geo -> one
    freshly referenced Update Geo) usually isn't bound yet, so create a
    skinCluster from the union of every source's influences first, the
    same way SkinWeight.copy_weight bootstraps the 1:1 case -- the
    initial bind weights don't matter, merge_skin overwrites them
    per-vertex right after.
    """
    if _get_skin_cluster(target):
        return

    influences = []
    for source in sources:
        source_skin = _get_skin_cluster(source)
        if not source_skin:
            continue
        for joint in cmds.skinCluster(source_skin, q=True, influence=True):
            if joint not in influences:
                influences.append(joint)

    if not influences:
        cmds.warning(
            "RigUpdater: none of the Source Geo for '{}' have a skinCluster; "
            "skipping.".format(target)
        )
        return

    cmds.skinCluster(
        influences,
        target,
        toSelectedBones=True,
        bindMethod=0,
        skinMethod=0,
        normalizeWeights=1,
    )


def transfer_skin(sources, target, debug_log=False):
    """Copy skin weights onto target from one or more sources.

    Cardinality alone decides the path -- callers don't need to classify a
    row as merge/separate/1:1 themselves: one source is a direct copy, more
    than one is a merge (MergeSkin's existing closest-vertex transfer). A
    single source reused across several rows (the "separate skin geo" case)
    falls out naturally since each row is processed independently.
    """
    if not sources:
        return

    if len(sources) == 1:
        SkinWeight.copy_weight(sources[0], target)
    else:
        _ensure_skin_cluster_for_merge(sources, target)
        merge_skin_function.merge_skin(sources, target, debug_log=debug_log)


def backup_skin(meshes):
    """Best-effort skin backup before the swap; never blocks the update."""
    if not meshes:
        return

    try:
        cmds.select(meshes, replace=True)
        QuickData.export_skin_quick()
    except Exception as exc:
        cmds.warning("RigUpdater: skin backup skipped ({}).".format(exc))


def discard_source_reference(ref_path):
    """Remove the source reference outright (used when Keep Old Geo is off)."""
    cmds.file(ref_path, removeReference=True)


def keep_source_reference_as_backup(ref_info):
    """Import the source reference and park it, hidden, under Delete_Grp.

    Runs after skin has already been transferred off of it, so this is
    pure bookkeeping -- the geo group is renamed old_<namespace> (unique
    per character, replacing any previous backup of the same character)
    rather than the old script's single hardcoded "old_geo".
    """
    cmds.file(ref_info["ref_path"], importReference=True)
    cmds.namespace(removeNamespace=ref_info["namespace"], mergeNamespaceWithRoot=True)

    if not cmds.objExists("Delete_Grp"):
        cmds.group(empty=True, name="Delete_Grp")

    old_name = "old_{}".format(ref_info["namespace"])
    if cmds.objExists(old_name):
        cmds.delete(old_name)

    cmds.parent(GEO_GROUP_NAME, "Delete_Grp")
    cmds.rename(GEO_GROUP_NAME, old_name)
    cmds.setAttr("{}.v".format(old_name), False)


def attach_update_geo(update_ref_info):
    """Parent the update reference's geo group under Geometry, same as before."""
    if cmds.objExists("Geometry"):
        cmds.parent(update_ref_info["geo_group"], "Geometry")
    else:
        cmds.warning(
            "RigUpdater: no 'Geometry' group found in scene; leaving {} in place.".format(
                update_ref_info["geo_group"]
            )
        )


def cleanup_materials():
    Validate.cleanup_materials()


# ------------------------------------------------------------------
# RigData -- temporary session persistence
# ------------------------------------------------------------------
# Scene-adjacent "RigData" folder, same convention as tmlib.core.QuickData's
# "QuickData" folder, so the current mapping isn't lost if the tool window
# is closed (or Maya crashes) before "Update Rig" runs. Auto-created
# on save, unlike QuickData which needs an explicit create step first --
# this is just a lightweight, disposable cache, not data anyone browses.


def get_rig_data_dir():
    scene_path = cmds.file(q=True, sceneName=True)
    if not scene_path:
        return False

    rig_data_dir = os.path.join(os.path.dirname(scene_path), "RigData")
    os.makedirs(rig_data_dir, exist_ok=True)
    return rig_data_dir


def get_session_path():
    rig_data_dir = get_rig_data_dir()
    if not rig_data_dir:
        return None
    return os.path.join(rig_data_dir, SESSION_FILE_NAME)


def save_session(data):
    """Best-effort temp save of the current tool state; never blocks the UI."""
    session_path = get_session_path()
    if not session_path:
        return

    try:
        with open(session_path, "w") as f:
            json.dump(data, f, indent=4)
    except Exception as exc:
        cmds.warning("RigUpdater: could not save session ({}).".format(exc))


def load_session():
    session_path = get_session_path()
    if not session_path or not os.path.exists(session_path):
        return None

    try:
        with open(session_path) as f:
            return json.load(f)
    except Exception as exc:
        cmds.warning("RigUpdater: could not load session ({}).".format(exc))
        return None


def clear_session():
    session_path = get_session_path()
    if session_path and os.path.exists(session_path):
        try:
            os.remove(session_path)
        except OSError:
            pass
