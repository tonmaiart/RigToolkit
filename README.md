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
own module, independent of `MayaToolkit`. These were the exact same menu
items (`renamer`, `attribute_tool`, `local_script`, `quick_data`,
`easy_controller`, `snapper`, `weight_puller` — same ids/order/category)
that `MayaToolkit`'s `menu_utils.py`/`__init__.py` used to register before
the toolkit folders moved here; `BeamSmear` is new and never had a
MayaToolkit menu item.
