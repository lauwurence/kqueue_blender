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
from . import main, save_load


class LoaderThread(qtc.QThread):


    def __init__(self, *files):
        super().__init__()

        self.files = files


    def run(self):
        preset = store.preset
        mw = store.mw

        makedirs(store.temp_folder, exist_ok=True)

        preset.is_adding_projects = True
        mw.update_widgets.emit()

        # Load cache
        cache = save_load.load_cache(otherwise={})

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
            if file in cache and (cache[file]['mod_time'] == mod_time):
                main.log(f'({i + 1}/{len(files)}) Loading cache: {file}')
                data = cache[file]

            # Get project data
            else:
                main.log(f'({i + 1}/{len(files)}) Opening project: {file}')

                BATCH = f"""
@CHCP 65001 > NUL
blender "{file}" --factory-startup --background  --python "{store.get_data_py.resolve()}" "{store.bridge_file.resolve()}"
"""

                with open(store.get_data_bat, 'w') as f:
                    f.write(BATCH.strip())

                process = subprocess.Popen([store.get_data_bat.resolve()],
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

                if not store.bridge_file.exists():
                    main.log(f'Could not fetch project data: {file} | Bridge: {store.bridge_file}')
                    return

                # Read project data
                with open(store.bridge_file, 'r') as f:
                    data = json.load(f)

                # Write cache project data
                data['mod_time'] = mod_time
                cache[file] = data

                # Update cache
                save_load.save_cache(cache)

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

        if at_least_one:
            preset.need_save()
            main.log(f'All projects loaded!')

        preset.is_adding_projects = False

        mw.update_list.emit(False)
        mw.update_widgets.emit()
