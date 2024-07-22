
import os
import sys
import bpy
import json
from pathlib import Path

DATA_FILE = sys.argv[6]

scene = bpy.context.scene
cycles = scene.cycles
render = scene.render

print("BLENDER-START----------------------------------------")

def main():

    if not DATA_FILE.endswith(".json"):
        raise Exception(f'Bad data file name: {DATA_FILE}')

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
        if Path(DATA_FILE).exists():
            os.remove(DATA_FILE)

        raise Exception("Error fetching data.")

    with open(DATA_FILE, 'w') as json_file:
        json_file.write(json.dumps(data, indent=4))

    print("Data fetched without errors.")

main()

print("BLENDER-END------------------------------------------")