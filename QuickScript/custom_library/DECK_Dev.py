from UkoreMaya.core import Pipeline
import tmlib

from tmlib.core import System

System.reload_scripts()


def export_shot_to_ue():
    pass

    Pipeline.export_shot_to_ue(
        export_path="C:/Users/natch/OneDrive/Documents/ExportTest",
        prefix_seperate=True,
        smooth_mesh=True,
        validate_material=True,
        export_anim=True,
        export_camera=False,
        export_head_locator=True,
        pick_character_enable=True,
        pick_character=["Kafka"],
    )
