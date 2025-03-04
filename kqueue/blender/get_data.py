
import os
import sys
import bpy
import json
from pathlib import Path

BRIDGE_FILE = sys.argv[6]

scene = bpy.context.scene
cycles = scene.cycles
render = scene.render

print("BLENDER-START----------------------------------------")

def main():

    bridge_file = Path(BRIDGE_FILE)

    if bridge_file.suffix != ".json":
        raise Exception(f'Bad data file name: {bridge_file.resolve()}')

    data = {}

    try:
        for key, value in {
            'frame_start' : 'scene.frame_start',
            'frame_end' : 'scene.frame_end',
            'scene' : 'scene.name',
            'scene_list' : 'bpy.data.scenes.keys()',
            'camera' : 'scene.camera.name if scene.camera else None',
            'camera_list' : '[obj.name for obj in bpy.data.objects if obj.type == "CAMERA"]',
            'render_filepath' : 'render.filepath',
            'file_format' : 'render.image_settings.file_format',
            'use_persistent_data' : 'render.use_persistent_data',
            'use_adaptive_sampling' : 'cycles.use_adaptive_sampling',
            'samples' : 'cycles.samples',
            'denoiser' : 'cycles.denoiser',
            'denoising_use_gpu' : 'cycles.denoising_use_gpu', # OPENIMAGEDENOISE, OPTIX
            'denoising_input_passes' : 'cycles.denoising_input_passes',
            'denoising_prefilter' : 'cycles.denoising_prefilter',
        }.items():
            data[key] = eval(value)

    except:
        if bridge_file.exists():
            os.remove(bridge_file.resolve())

        raise Exception("Error fetching data.")

    with open(bridge_file, 'w') as f: #encoding="utf-8"
        f.write(json.dumps(data, indent=4))

    print("Data fetched successfully.")

main()

print("BLENDER-END------------------------------------------")