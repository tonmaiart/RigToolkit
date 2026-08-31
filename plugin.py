from __future__ import annotations

from pathlib import Path

TOOL_ID = "rig_toolkit"
TOOL_LABEL = "RigToolkit"
# Convention-only string match with plugins/repo_internal/maya_launcher/plugin.py
# — both resolve to the same active Project's plugin_data via
# ProjectPluginConfigStore, no coupling API needed. See that plugin's README
# for the full "contributions"/"labels" shape this writes into.
MAYA_ENV_BRIDGE_PLUGIN_ID = "maya_launcher_env_bridge"
ANY_VERSION = "*"


def register(api) -> None:
    # Tool folders (Attribute/, Renamer/, ...) sit directly under this repo's
    # own root as top-level packages — no maya-scripts/ wrapper like
    # MayaToolkit/AdvancedSkeleton use — so the PYTHONPATH entry has to be
    # this folder itself for `File.launch("Renamer")`'s
    # `importlib.import_module("Renamer.interface")` to resolve.
    tool_root = Path(__file__).resolve().parent

    bridge = api.project_plugin_config_store(MAYA_ENV_BRIDGE_PLUGIN_ID)
    if bridge is None:
        return

    contributions = bridge.get("contributions", {})
    contributions[TOOL_ID] = {
        "PYTHONPATH": {ANY_VERSION: [str(tool_root)]},
    }
    bridge.set("contributions", contributions)

    labels = bridge.get("labels", {})
    labels[TOOL_ID] = TOOL_LABEL
    bridge.set("labels", labels)

    # order ต้องน้อยกว่า UkoreMenu เอง (order 99) เพื่อให้ import (และ
    # register_item ของ UkoreRigToolkit) รันเสร็จก่อน UkoreMenu สั่ง
    # rebuild_menu — เมนู Renamer/Attribute/Local Script/Quick Data/Easy
    # Controller/Snapper/Weight Puller เดิมถูก MayaToolkit เป็นคน register
    # แทน (ทั้งที่ implementation ย้ายออกมาที่นี่แล้ว) ย้ายมาให้ปลั๊กอินนี้
    # ประกาศ launch_hooks ของตัวเองแทน แบบเดียวกับ AdvancedSkeleton/
    # UkoreReferenceEditor/ShotSplitter
    hooks = bridge.get("launch_hooks", {})
    hooks[TOOL_ID] = {
        "order": 25,
        "post_open_mel": 'python("try:\\n    import UkoreRigToolkit\\nexcept ImportError:\\n    pass");',
    }
    bridge.set("launch_hooks", hooks)
