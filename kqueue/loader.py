################################################################################
## Blend Files Loader

import subprocess
import PyQt5.QtCore as qtc
import json

from os import makedirs
from pathlib import Path
from .utils.path import join
from .config import *
from . import store
from .project.object import BlendProject
from . import main


class LoaderThread(qtc.QThread):


    def __init__(self, *files):
        super().__init__()

        self.files = files


    def run(self):
        preset = store.preset
        mw = store.mw

        makedirs(join(store.working_dir, "blender/temp"), exist_ok=True)
        CACHE_FILE = join(store.working_dir, "blender/cache.json")
        DATA_FILE = join(store.working_dir, "blender/temp/data.json")
        GET_DATA_PY = join(store.working_dir, "blender/get_data.py")

        preset.is_adding_projects = True
        mw.update_widgets.emit()

        # Read cache
        if Path(CACHE_FILE).exists():
            try:
                with open(CACHE_FILE, 'r') as json_file:
                    cache = json.load(json_file)
            except:
                main.log(f'Error reading cache file: {CACHE_FILE}')
                return
        else:
            cache = {}

        files = [ join(file) for file in self.files if file.endswith(".blend")]
        at_least_one = False

        for i, file in enumerate(files):
            mod_time = int(Path(file).stat().st_mtime)

            # Skip already loaded blend files
            if file in [ project.file for project in preset.project_list ]:
                continue

            if not at_least_one:
                print("------------------------")
                main.log("Loading new projects...")

            # Get cached project data
            if file in cache and cache[file]['mod_time'] == mod_time:
                data = cache[file]
                main.log(f'({i + 1}/{len(files)}) Loading cache: {file}')

            # Get project data
            else:
                BATCH_FILE = join(store.working_dir, f'blender/temp/get_data.bat')
                BATCH = f"""
@CHCP 65001 > NUL
blender "{file}" --factory-startup --background  --python "{GET_DATA_PY}" "{DATA_FILE}"
"""

                with open(BATCH_FILE, 'w') as f:
                    f.write(BATCH.strip())

                main.log(f'({i + 1}/{len(files)}) Opening project: {file}')

                process = subprocess.Popen([BATCH_FILE],
                                        # stderr=subprocess.STDOUT,
                                        # stdout=subprocess.PIPE,
                                        # stdin=subprocess.PIPE,
                                        #    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP, #DETACHED_PROCESS
                                        #    creationflags=subprocess.DETACHED_PROCESS, #DETACHED_PROCESS
                                        #    preexec_fn=os.setsid,
                                        cwd=join(Path(preset.blender_exe).parent),
                                        shell=True
                                        )

                process.wait()

                if not Path(DATA_FILE).exists():
                    main.log(f'Could not fetch project data: {file} | Data: {DATA_FILE}')
                    return

                # Read project data
                with open(DATA_FILE, 'r') as json_file:
                    data = json.load(json_file)

                # Write cache project data
                data['mod_time'] = mod_time
                cache[file] = data

                with open(CACHE_FILE, 'w') as json_file:
                    json_file.write(json.dumps(cache, indent=4))

            # Unpack project data
            project = BlendProject(
                file,
                frame_start=data['frame_start'],
                frame_end=data['frame_end'],
                scene=data['scene'],
                scene_list=data['scene_list'],
                camera=data['camera'],
                camera_list=data['camera_list'],
                render_filepath=data['render_filepath'],
                file_format=data['file_format'],
                use_persistent_data=data['use_persistent_data'],
                use_adaptive_sampling=data['use_adaptive_sampling'],
                samples=data['samples'],
                denoiser=data['denoiser'],
                denoising_use_gpu=data['denoising_use_gpu'],
                denoising_input_passes=data['denoising_input_passes'],
                denoising_prefilter=data['denoising_prefilter'],
            )

            preset.project_list.append(project)
            mw.update_list.emit(False)
            mw.update_widgets.emit()
            at_least_one = True

            preset.need_save()

        if at_least_one: main.log(f'All projects loaded!')
        preset.is_adding_projects = False

        mw.update_list.emit(False)
        mw.update_widgets.emit()