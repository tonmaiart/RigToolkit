"""Maya-side operations for MergeSkin.

Python port of the mergeSkin.mll MPxCommand (Maya-mergeSkin, Faruq00):
for each base mesh's skinCluster, transfer each vertex's influence weights
onto the closest vertex on the target mesh's own skinCluster, matching
influences by short name. Kept independent of interface.py's Qt widgets so
the transfer logic can run headless (script editor, batch) without a UI.
"""

import maya.cmds as mc
import maya.api.OpenMaya as om
import maya.api.OpenMayaAnim as oma

ZERO_WEIGHT_THRESHOLD = 1e-5


def _get_mesh_dag_path(mesh_name):
    selection = om.MSelectionList()
    try:
        selection.add(mesh_name)
    except RuntimeError:
        return None

    dag_path = selection.getDagPath(0)
    if dag_path.hasFn(om.MFn.kTransform):
        try:
            dag_path.extendToShape()
        except RuntimeError:
            return None

    if not dag_path.hasFn(om.MFn.kMesh):
        return None

    return dag_path


def _get_skin_cluster(mesh_dag_path):
    # listHistory(pruneDagObjects=True) walks upstream the same way the
    # original plugin's MItDependencyGraph(kUpstream) search did.
    history = mc.listHistory(mesh_dag_path.fullPathName(), pruneDagObjects=True) or []
    skin_nodes = mc.ls(history, type="skinCluster")
    if not skin_nodes:
        return None

    selection = om.MSelectionList()
    selection.add(skin_nodes[0])
    return selection.getDependNode(0)


def _closest_vertex_id(mesh_fn, position):
    _closest_point, face_id = mesh_fn.getClosestPoint(position, space=om.MSpace.kWorld)
    if face_id == -1:
        return -1

    nearest_id = -1
    nearest_dist = None
    for vtx_id in mesh_fn.getPolygonVertices(face_id):
        vtx_pos = mesh_fn.getPoint(vtx_id, om.MSpace.kWorld)
        dist = (position - vtx_pos).length()
        if nearest_dist is None or dist < nearest_dist:
            nearest_dist = dist
            nearest_id = vtx_id

    return nearest_id


def _get_ngskintools_layer(target):
    """Return the ngSkinTools2 layer to write target's transferred weights into, or None.

    Only returns a layer when ngSkinTools2 is installed AND target already has
    layers initialized -- writing straight into a layers-enabled mesh's
    skinCluster gets silently overwritten by ngSkinTools2's own composite next
    recompute, same reason WeightPuller special-cases ngSkinTools2 for its
    move/swap. MergeSkin never initializes layers on a mesh that doesn't
    already use them.
    """
    try:
        from ngSkinTools2.api import Layers, get_layers_enabled
    except ImportError:
        return None

    try:
        if not get_layers_enabled([target]):
            return None

        layers = Layers(target)
        layer = getattr(layers, "current_layer", None)
        if layer is None:
            existing = layers.list()
            layer = existing[0] if existing else None
        return layer
    except Exception as exc:
        om.MGlobal.displayWarning(
            "MergeSkin: could not access ngSkinTools2 layers on {} ({}); "
            "falling back to skinCluster weights.".format(target, exc)
        )
        return None


def _apply_ngskintools_weights(layer, vertex_data):
    """Write vertex_data ({target_vtx_id: {inf_index: weight}}) into an ngSkinTools2 layer.

    Layer.set_weights takes a full per-vertex array per influence, so each
    affected influence's existing array is read once and only the transferred
    vertex entries are overwritten -- untouched vertices on that influence are
    preserved. Influences absent from a given vertex's distribution are zeroed
    at that vertex, mirroring MFnSkinCluster.setWeights(normalize=False)'s
    full-replace-per-vertex behavior in the non-layers path below.
    """
    affected_influences = set()
    for distribution in vertex_data.values():
        affected_influences.update(distribution.keys())

    for inf_index in affected_influences:
        weights = list(layer.get_weights(inf_index))
        for vtx_id, distribution in vertex_data.items():
            weights[vtx_id] = distribution.get(inf_index, 0.0)
        layer.set_weights(inf_index, weights)


def _grouped_skin_weights(skin_cluster_obj, mesh_dag_path):
    skin_fn = oma.MFnSkinCluster(skin_cluster_obj)
    mesh_fn = om.MFnMesh(mesh_dag_path)
    num_vertices = mesh_fn.numVertices

    comp_fn = om.MFnSingleIndexedComponent()
    vertex_component = comp_fn.create(om.MFn.kMeshVertComponent)
    comp_fn.addElements(range(num_vertices))

    weights, inf_count = skin_fn.getWeights(mesh_dag_path, vertex_component)
    joint_names = [path.partialPathName() for path in skin_fn.influenceObjects()]

    records = []
    for v_idx in range(num_vertices):
        base = v_idx * inf_count
        influences = [
            (joint_names[inf_idx], weights[base + inf_idx])
            for inf_idx in range(inf_count)
            if weights[base + inf_idx] > ZERO_WEIGHT_THRESHOLD
        ]
        records.append(influences)

    return records


def merge_skin(base_objects, target, debug_log=False):
    """Transfer skin weights from each of base_objects onto target by closest vertex.

    Mirrors `mergeSkin -b {"obj1", "obj2"} -t "myShape"`.
    """
    target_dag = _get_mesh_dag_path(target)
    if target_dag is None:
        mc.error("Invalid target mesh object: {}".format(target))
        return

    target_skin_obj = _get_skin_cluster(target_dag)
    if target_skin_obj is None:
        mc.error("Target mesh does not have a skin cluster.")
        return

    target_skin_fn = oma.MFnSkinCluster(target_skin_obj)
    joint_to_index = {
        path.partialPathName(): idx
        for idx, path in enumerate(target_skin_fn.influenceObjects())
    }

    if debug_log:
        om.MGlobal.displayInfo(
            "Target skin cluster node: {}".format(target_skin_fn.name())
        )
        om.MGlobal.displayInfo("Target object is: {}".format(target_dag.fullPathName()))

    target_mesh_fn = om.MFnMesh(target_dag)
    ng_layer = _get_ngskintools_layer(target)
    ng_vertex_data = {} if ng_layer is not None else None

    if debug_log and ng_layer is not None:
        om.MGlobal.displayInfo(
            "Target has ngSkinTools2 layers enabled -- writing into layer '{}'.".format(
                getattr(ng_layer, "name", ng_layer)
            )
        )

    for base_name in base_objects:
        base_dag = _get_mesh_dag_path(base_name)
        if base_dag is None:
            om.MGlobal.displayWarning("Invalid base mesh object: {}".format(base_name))
            continue

        base_skin_obj = _get_skin_cluster(base_dag)
        if base_skin_obj is None:
            continue

        if debug_log:
            om.MGlobal.displayInfo("{} as Base object.".format(base_dag.fullPathName()))

        records = _grouped_skin_weights(base_skin_obj, base_dag)
        base_mesh_fn = om.MFnMesh(base_dag)

        for v_idx, influences in enumerate(records):
            if not influences:
                continue

            source_pt = base_mesh_fn.getPoint(v_idx, om.MSpace.kWorld)
            target_vtx_id = _closest_vertex_id(target_mesh_fn, source_pt)
            if target_vtx_id == -1:
                continue

            inf_indices = []
            weights_arr = []
            for joint_name, weight in influences:
                idx = joint_to_index.get(joint_name)
                if idx is not None:
                    inf_indices.append(idx)
                    weights_arr.append(weight)

            if not inf_indices:
                continue

            if ng_vertex_data is not None:
                ng_vertex_data[target_vtx_id] = dict(zip(inf_indices, weights_arr))
                continue

            comp_fn = om.MFnSingleIndexedComponent()
            target_comp = comp_fn.create(om.MFn.kMeshVertComponent)
            comp_fn.addElement(target_vtx_id)

            # normalize=False: match the original plugin, which skips
            # auto-normalize per-vertex and leaves the target skinCluster's
            # own normalization (if any) to settle it afterward.
            target_skin_fn.setWeights(
                target_dag,
                target_comp,
                om.MIntArray(inf_indices),
                om.MDoubleArray(weights_arr),
                normalize=False,
            )

    if ng_vertex_data:
        _apply_ngskintools_weights(ng_layer, ng_vertex_data)

    om.MGlobal.displayInfo("Skin weights transfer completed successfully!")
