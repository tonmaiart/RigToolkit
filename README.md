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

Tools: `Attribute`, `BeamSmear`, `EasyController`, `PythonReader`,
`QuickData`, `Renamer`, `Snapper`, `WeightPuller`.

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
