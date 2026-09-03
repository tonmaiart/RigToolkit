from tmlib.core import File

# ------------- File Launchers -------------------
# Each of these is its own top-level package under RigToolkit's repo root
# (Attribute/interface.py, Renamer/interface.py, ...), launched the same way
# MayaToolkit's menu_utils.py used to before these tools moved here.


def rig_script():
    File.launch("RigScript")


def quick_script():
    File.launch("QuickScript")


def renamer():
    File.launch("Renamer")


def attribute():
    File.launch("Attribute")


def quickdata():
    File.launch("QuickData")


def easy_controller():
    File.launch("EasyController")


def snapper():
    File.launch("Snapper")


def weight_puller():
    File.launch("WeightPuller")


def beam_smear():
    File.launch("BeamSmear")


def merge_skin():
    File.launch("MergeSkin")


def rig_updater():
    File.launch("RigUpdater")


# ------------- Register menu items into ukore_menu's central registry ----
try:
    from UkoreMenu import registry, MenuItemSpec, ReloadHandlerSpec, reload_package

    items = [
        # --- Common (same ids/order/category MayaToolkit used to own) ---
        MenuItemSpec(
            id="renamer",
            label="Renamer",
            category="Common",
            command="import UkoreRigToolkit; UkoreRigToolkit.renamer()",
            order=210,
        ),
        MenuItemSpec(
            id="attribute_tool",
            label="Attribute",
            category="Common",
            command="import UkoreRigToolkit; UkoreRigToolkit.attribute()",
            order=220,
        ),
        # --- Rig (same order/category MayaToolkit used to own; "local_script"
        # renamed to "python_reader"/"Python Reader" to match the actual
        # tool name, then renamed again to "rig_script"/"Rig Script" once
        # the function-browser feature that name referred to moved to the
        # new QuickScript tool below) ---
        MenuItemSpec(
            id="rig_script",
            label="Rig Script",
            category="Rig",
            command="import UkoreRigToolkit; UkoreRigToolkit.rig_script()",
            order=10,
        ),
        MenuItemSpec(
            id="quick_script",
            label="Quick Script",
            category="Rig",
            command="import UkoreRigToolkit; UkoreRigToolkit.quick_script()",
            order=15,
        ),
        MenuItemSpec(
            id="quick_data",
            label="Quick Data",
            category="Rig",
            command="import UkoreRigToolkit; UkoreRigToolkit.quickdata()",
            order=20,
        ),
        MenuItemSpec(
            id="easy_controller",
            label="Easy Controller",
            category="Rig",
            command="import UkoreRigToolkit; UkoreRigToolkit.easy_controller()",
            order=30,
        ),
        MenuItemSpec(
            id="snapper",
            label="Snapper",
            category="Rig",
            command="import UkoreRigToolkit; UkoreRigToolkit.snapper()",
            order=40,
        ),
        MenuItemSpec(
            id="weight_puller",
            label="Weight Puller",
            category="Rig",
            command="import UkoreRigToolkit; UkoreRigToolkit.weight_puller()",
            order=50,
        ),
        # BeamSmear never had a MayaToolkit menu item — new tool, registered
        # here for the first time.
        MenuItemSpec(
            id="beam_smear",
            label="Beam Smear",
            category="Rig",
            command="import UkoreRigToolkit; UkoreRigToolkit.beam_smear()",
            order=55,
        ),
        # Python port of Maya-mergeSkin (Faruq00) -- transfers skin weights
        # from one or more base meshes onto a target mesh by closest vertex,
        # matching influences by name. Never had a MayaToolkit menu item.
        MenuItemSpec(
            id="merge_skin",
            label="Merge Skin",
            category="Rig",
            command="import UkoreRigToolkit; UkoreRigToolkit.merge_skin()",
            order=60,
        ),
        # Extracted out of QuickScript/custom_library/DECK_Rig.py's
        # `update_model_for_rig` -- swaps a rig's referenced model for an
        # updated one and transfers skin weights across a user-resolved
        # mapping table (merge/separate/1:1 auto-detected by mapping
        # cardinality), reusing MergeSkin for the many-to-one case. Never
        # had a MayaToolkit menu item.
        MenuItemSpec(
            id="rig_updater",
            label="Rig Updater",
            category="Rig",
            command="import UkoreRigToolkit; UkoreRigToolkit.rig_updater()",
            order=65,
        ),
    ]

    for item in items:
        registry.register_item(item)

    registry.register_reload_handler(
        ReloadHandlerSpec(
            id="rig_toolkit",
            label="RigToolkit",
            callback=lambda: reload_package("UkoreRigToolkit"),
            order=25,
        )
    )

except ImportError:
    pass

__all__ = [
    "rig_script",
    "quick_script",
    "renamer",
    "attribute",
    "quickdata",
    "easy_controller",
    "snapper",
    "weight_puller",
    "beam_smear",
    "merge_skin",
    "rig_updater",
]
