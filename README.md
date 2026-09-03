# RigToolkit

Rigging tool suite for Maya, split out of `MayaToolkit`'s old
`maya-scripts/` toolkit folders into its own `cache/plugins/` clone.
Each tool is its own top-level package directly under this repo's root
(`Attribute/interface.py`, `Renamer/interface.py`, ...), launched via
`tmlib.core.File.launch("<Name>")` (`importlib.import_module("<Name>.interface")`)
the same way MayaToolkit's own toolkits used to be — depends on
MayaToolkit's `tmlib` being on `sys.path` (see `manifest.json`'s
`requires`), no direct import relationship, just the shared
`maya_launcher_env_bridge` `PluginConfigStore` convention.

Tools: `Attribute`, `BeamSmear`, `EasyController`, `MergeSkin`, `QuickData`,
`QuickScript`, `Renamer`, `RigScript`, `RigUpdater`, `Snapper`, `WeightPuller`.

`plugin.py`'s `register(api)` contributes this folder's own root to the
Maya Launcher env bridge's `PYTHONPATH`, plus a `launch_hooks` entry
(`import UkoreRigToolkit`) so `UkoreRigToolkit/__init__.py` registers this
plugin's menu items into `ukore_menu`'s central "Ukore Tools" registry —
own module, independent of `MayaToolkit`. These were the same menu items
(`renamer`, `attribute_tool`, `quick_data`, `easy_controller`, `snapper`,
`weight_puller` — same ids/order/category) that `MayaToolkit`'s
`menu_utils.py`/`__init__.py` used to register before the toolkit folders
moved here (`local_script` was renamed to `python_reader`/"Python Reader"
to match the actual tool name); `BeamSmear` is new and never had a
MayaToolkit menu item.

**2026-09-01: `PythonReader`'s "Config Global Paths" system removed.**
`PythonReader/interface.py` used to load a list of external script paths
from `PythonReader/config/GlobalPaths.json` (stale personal-machine paths
under someone's `G:/My Drive/...`) to build a function browser/runner UI —
that whole subsystem (`import_functions`, `import_all_functions`,
`get_function_object`, `reload_list_widget_library`,
`reload_list_widget_functions`, `edit_library_script`,
`open_extra_path_file`, `show_context_menu`, `quick_run_pure_function`,
`load_description`, `run_script`, `cast_to_type`, `clear_layout`,
`add_input_row`/`line_edit_action`) was already fully disconnected from
the UI (every signal connection was commented out) and depended entirely
on that config file, so it was removed rather than rewired. The actual
`custom_library/` scripts that config used to point at (`AttrDebugger.py`,
`DECK_Blender.py`, `DECK_Dev.py`, `DECK_MathKits.py`, `DECK_Model.py`,
`DECK_QuickData.py`, `DECK_Rig.py`, `Publisher.py`) moved from
`MayaToolkit/maya-scripts/UkoreMaya/custom_library/` into
`PythonReader/custom_library/` here instead — they're bundled with the
plugin now, not loaded through any config; several of them still `import
UkoreMaya`/`from UkoreMaya.core import ...`/`from UkoreMaya.menu import
...` directly, which still resolves at runtime through the shared
`maya_launcher_env_bridge` PYTHONPATH merge (RigToolkit already declares
`requires: ["maya_toolkit", ...]`), same flat-namespace convention
`tmlib.core.File.launch()` itself relies on. The "Local Script"/"Quick
Data" feature (a separate, unrelated feature reading scripts from the
active Quick Data folder, not from `custom_library`) is untouched.

**2026-09-02: `MergeSkin` added.** Pure-Python port of the third-party
`Maya-mergeSkin` MPxCommand plugin (github.com/Faruq00/Maya-mergeSkin) —
no compiled `.mll` involved. `MergeSkin/function.py` reimplements the
algorithm with `maya.api.OpenMaya`/`OpenMayaAnim` (closest-point-per-vertex
lookup + `MFnSkinCluster.getWeights`/`setWeights`, influences matched by
short name): for each base mesh's skinCluster, transfer each vertex's
weights onto the closest vertex on the target mesh's own skinCluster.
`MergeSkin/interface.py` + `ui.ui` wrap it in the same `ToolkitWindow`
pattern as `BeamSmear`/`WeightPuller` (pick base objects from selection,
pick a target, optional debug log). New tool, registered as `merge_skin`
("Merge Skin") in the "Rig" category, order 60 — never had a MayaToolkit
menu item.

If the target mesh already has ngSkinTools2 layers enabled,
`function._get_ngskintools_layers`/`_apply_ngskintools_layer` route the
transferred weights there instead of the raw skinCluster (same reason
`WeightPuller` special-cases ngSkinTools2 — writing straight to a
layers-enabled skinCluster gets silently overwritten by ngSkinTools2's own
composite). Each base object gets its **own** dedicated layer
(`MergeSkin_<base_name>`, created if missing, fully rebuilt on re-runs),
with its mask set to 1.0 only on the target vertices that base object
actually mapped onto and 0.0 (fully subtracted) everywhere else — so
overlapping base objects can never bleed into each other's region, no
manual masking needed. MergeSkin never creates layers on a target that
doesn't already use them, and falls back to the plain skinCluster path if
`ngSkinTools2` isn't installed or its layers API call fails.

**2026-09-03: `QuickScript` registered; `PythonReader` renamed to `RigScript`.**
`QuickScript` (a folder that already existed on disk but was never wired into
the menu) re-implements the function-browser feature described above
(`load_functions`/`import_all_functions`/`reload_list_widget_library`/
`reload_list_widget_functions`/`edit_library_script`/`quick_run_pure_function`
/`show_context_menu`) as its own tool, driven by its own
`QuickScript/config/GlobalPaths.json`. That config used to list the same kind
of stale personal-machine absolute paths the old removed system did
(`G:/My Drive/Mellowstar/dev/maya-scripts/UkoreMaya/custom_library/*.py`), so
the actual `custom_library/` scripts moved a second time — out of
`PythonReader/custom_library/` (where they'd been sitting unused, bundled but
not loaded through any config, per the entry above) into
`QuickScript/custom_library/` where they're now actually read — and
`GlobalPaths.json`'s entries became paths relative to `QuickScript/`'s own
folder (`custom_library/DECK_Rig.py`, ...), resolved in
`QuickScript/interface.py`'s `load_functions`/`open_extra_path_file` via
`os.path.join(os.path.dirname(__file__), relative_path)` instead of being
used as absolute paths directly. `QuickScript` is now registered in
`UkoreRigToolkit/__init__.py` as `quick_script`/"Quick Script" (`Rig`
category, order 15). With the function-browser feature now living in
`QuickScript`, the old `PythonReader` folder — left with only the unrelated
"Local Script"/"Quick Data" feature after the 2026-09-01 removal — was
renamed to `RigScript`, registered as `rig_script`/"Rig Script" (same order
10 the old `python_reader`/"Python Reader" entry used).

**`RigUpdater` added.** `update_model_for_rig` (`QuickScript/custom_library/
DECK_Rig.py`) was extracted out into its own tool, `RigUpdater/` (`interface.py`
+ `function.py`, hand-built `ui.ui`), registered as `rig_updater`/"Rig Updater"
(`Rig` category, order 65). Unlike the original one-click function, it no
longer auto-detects the rig via `cmds.select("*:geo")` or looks up "latest
version in folder" — the user loads the Source (current) and Update (new)
references themselves from whatever node they have selected in the
viewport, via each side's "Load" button (`get_reference_info` resolves the
reference node/file/namespace from that selection, requiring a top-level
`<namespace>:geo` group same as before; the line edit shows just
`ref_name` — the reference file's basename — not the full path). Loading a
reference lists every mesh under its `geo` group
(`Selection.get_children_mesh`) in that side's own table
(`tableWidget_geo_source_info` / `tableWidget_geo_update_info`, each with a
"Resolve Status" column). Mapping is pair-based, not row-fixed: selecting
one or more rows on each side and clicking "Add Selected to Mapping"
appends every source-row × update-row combination as its own pair into
`tableWidget_mapping_skin` (so one Update Geo can collect any number of
Source Geo, shown as that many separate preview rows) — "Auto Resolve"
does the same by exact basename match instead of manual selection, and
"Clear" (next to the Update table) drops every pair for the selected
Update Geo row(s). Whether a given Update Geo ends up a 1:1 transfer, a
many-to-one merge, or one source feeding several separate Update Geo is
never classified up front — at "Update Rig" time the pairs are grouped by
Update Geo and `transfer_skin` just branches on how many Source Geo that
group has: one calls `SkinWeight.copy_weight` directly, more than one
calls `MergeSkin.function.merge_skin` (the existing closest-vertex
transfer). Skin transfer runs *before* the old reference is touched (so
the mapped paths are still live), then a new "Keep Old Geo" checkbox
decides what happens to the source reference: checked imports it and
parks it hidden under `Delete_Grp` as `old_<namespace>` (like the original
always did, but namespaced instead of a single hardcoded `old_geo` so
repeat runs on different characters don't collide); unchecked just
`removeReference`s it outright, since nothing still needs it once skin has
moved.
