################################################################################
## Blend Files Loader

import subprocess
import PyQt5.QtCore as qtc
import json

from os import makedirs
from pathlib import Path
from .utils.pathutils import join
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

        if preset.is_adding_projects:
            return

        makedirs(store.temp_folder, exist_ok=True)

        preset.is_adding_projects = True
        mw.update_widgets.emit()

        # Load cache
        cache = save_load.load_cache()

        files = [ join(file) for file in self.files if file.endswith(".blend")]
        loaded_projects_list = []
        need_save = False

        for i, file in enumerate(files):
            mod_time = int(Path(file).stat().st_mtime)

            # Update the project that already exists
            project = None

            for p in preset.project_list:

                if file != p.file:
                    continue

                project = p
                break

            if not loaded_projects_list:
                print("------------------------")
                main.log("Loading new projects...")

            # Get cached project data
            if file in cache and (cache[file]['mod_time'] == mod_time):
                main.log(f'({i + 1}/{len(files)}) Loading cache: {file}')
                data = cache[file]

            # Get project data
            else:
                main.log(f'({i + 1}/{len(files)}) Reading project: {file}')

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

                # Update cache
                cache[file] = data
                save_load.save_cache(cache)

            # Unpack project data
            loaded_project = BlendProject(
                file,
                frame_start=data['frame_start'],
                frame_end=data['frame_end'],
                scene=data['scene'],
                scene_list=data['scene_list'],
                camera=data['camera'],
                camera_list=data['camera_list'],
                resolution_x=data['resolution_x'],
                resolution_y=data['resolution_y'],
                resolution_percentage=data['resolution_percentage'],
                render_filepath=data['render_filepath'],
                file_format=data['file_format'],
                use_persistent_data=data['use_persistent_data'],
                use_adaptive_sampling=data['use_adaptive_sampling'],
                samples=data['samples'],
                denoiser=data['denoiser'],
                denoising_use_gpu=data['denoising_use_gpu'],
                denoising_input_passes=data['denoising_input_passes'],
                denoising_prefilter=data['denoising_prefilter'],
                markers=data.get('markers', []),
                mod_time=mod_time,
            )

            if project is None:
                preset.project_list.append(loaded_project)
                need_save = True

            else:

                if project.frames != loaded_project.frames:
                    project.frames_override = loaded_project.frames_override

                for name in [
                    'frames',
                    'scene',
                    'scene_list',
                    'camera',
                    'camera_list',
                    'resolution_x',
                    'resolution_y',
                    'resolution_percentage',
                    'use_persistent_data',
                    'render_filepath',
                    'file_format',
                    'use_adaptive_sampling',
                    'samples',
                    'denoiser',
                    'denoising_use_gpu',
                    'denoising_input_passes',
                    'denoising_prefilter',
                    'markers',
                    'mod_time',
                ]:

                    if not hasattr(loaded_project, name):
                        continue

                    new_value = getattr(loaded_project, name)
                    old_value = getattr(project, name)

                    if new_value == old_value:
                        continue

                    setattr(project, name, new_value)

                    if name not in ['mod_time']:
                        need_save = True

                        print(name, old_value, "=>", new_value)

            mw.update_list.emit(False)
            mw.update_widgets.emit()

            loaded_projects_list.append(loaded_project)

        if loaded_projects_list:

            if need_save:
                preset.set_need_save()
                main.log(f'All projects loaded!')

            else:
                main.log(f'No new data loaded.')

        preset.is_adding_projects = False

        mw.update_list.emit(False)
        mw.update_widgets.emit()
