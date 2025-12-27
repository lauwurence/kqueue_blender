################################################################################
## Queue Preset

import time
import subprocess
import PyQt5.QtCore as qtc

from re import search
from io import TextIOWrapper
from pathlib import Path
from .utils.pathutils import join
from .utils import monitor, audio
from .config import *
from . import store, main


################################################################################

class RenderThread(qtc.QThread):

    finished = qtc.pyqtSignal()
    listener_started = False


    def __init__(self):
        super().__init__()


    def run(self):
        preset = store.preset
        mw = store.mw

        audio.play(RENDER_START_AUDIO)
        preset.set_status('RENDERING')
        mw.update_widgets.emit()

        for project in preset.project_list:

            if not project.is_renderable():
                continue

            if preset.is_status('RENDERING_STOPPING', 'RENDERING_FINISHED'):
                break

            sc = project.get_scene()
            fl = project.get_frames_list()
            ca = project.get_camera()

            if not sc or not fl or not ca:
                continue

            PYTOH_FILE = join(store.working_dir, "blender/temp/render_settings.py")

            PYTHON = f"""
import bpy

scene = bpy.context.scene
cycles = scene.cycles
render = scene.render
image_settings = render.image_settings
shading = scene.display.shading

# Scene
if "{ca}" in bpy.data.objects:
    scene.camera = bpy.data.objects["{ca}"]

render.filepath = "{project.get_render_filepath().replace('\\', '/')}"
render.use_overwrite = True
render.use_persistent_data = {project.get_use_persistent_data()}

# Compositor
render.compositor_device = "GPU"
render.compositor_precision = "FULL"
"""
            # New data
            for name, value in [
                ('image_settings.file_format', project.get_file_format()),
                ('render.resolution_x', project.get_resolution_x()),
                ('render.resolution_y', project.get_resolution_y()),
                ('render.resolution_percentage', project.get_resolution_percentage())
            ]:

                if value is None or value == "None":
                    continue

                if isinstance(value, str):

                    if value.isnumeric():
                        value = eval(value)

                    else:
                        value = f'"{value}"'

                PYTHON += f'\n{name} = {value}'

            if preset.preview_render:
                PYTHON += f"""

# Render
render.use_simplify = True
render.simplify_subdivision_render = 0
render.use_border = False

# Shading
shading.color_type = "TEXTURE"
shading.show_cavity = True
shading.use_dof = True
shading.show_object_outline = True
shading.show_backface_culling = False
shading.show_shadows = False

# Compositor
render.compositor_device = "GPU"
render.compositor_precision = "FULL"
"""

            else:
                PYTHON += f"""
render.use_simplify = False
render.use_border = False

# Render
cycles.use_adaptive_sampling = {project.get_use_adaptive_sampling()}
cycles.samples = {project.get_samples()}

# Denoiser
cycles.denoiser = "{project.get_denoiser()}"
cycles.denoising_input_passes = "{project.get_denoising_input_passes()}"
cycles.denoising_prefilter = "{project.get_denoising_prefilter()}"
cycles.denoising_quality = "HIGH"
cycles.denoising_use_gpu = {project.get_denoising_use_gpu()}
"""

            # Technically, take scene settings and assigning sRGB
            if preset.assign_srgb or True:
                PYTHON += "\nimage_settings.color_management = 'FOLLOW_SCENE'"
                PYTHON += "\nscene.display_settings.display_device = 'sRGB'"

            # This message is needed to let us know that all our settings
            # were applied without errors.
            PYTHON += '\n\nprint("All settings loaded successfully!")'

            with open(PYTOH_FILE, 'w', encoding="utf-8") as f:
                f.write(PYTHON.strip())

            BATCH_FILE = join(store.working_dir, f'blender/temp/start_render.bat')
            BATCH = f"""
@CHCP 65001 > NUL
@echo ---BLENDER-RENDER-START
blender --background "{project.file}" --scene "{sc}" -E "{'CYCLES' if not preset.preview_render else 'BLENDER_WORKBENCH'}" --python "{PYTOH_FILE}" -f "{",".join([str(f) for f in fl])}"
@echo ---BLENDER-RENDER-END
"""

# BLENDER_WORKBENCH, BLENDER_EEVEE_NEXT, CYCLES

#--cycles-device OPTIX

            with open(BATCH_FILE, 'w', encoding="utf-8") as f:
                f.write(BATCH.strip())

            preset.process = subprocess.Popen(
                [ BATCH_FILE ],
                stderr=subprocess.STDOUT,
                stdout=subprocess.PIPE,
                stdin=subprocess.PIPE,
                cwd=join(Path(preset.blender_exe).parent),
                #    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP, #DETACHED_PROCESS
                creationflags=subprocess.CREATE_NO_WINDOW,
                #    preexec_fn=os.setsid,
                shell=False
                )

            if not self.listener_started:
                self.listener_started = True


                self.listen_thread = RenderListenThread()
                self.timer_thread = RenderTimerThread()

                # self.listen_thread = qtc.QThread()
                # self.listen_worker = RenderListenThread()
                # self.listen_worker.moveToThread(self.listen_thread)

                self.listen_thread.gProgressBar_setValue.connect(mw.w_gProgressBar.setValue)
                self.listen_thread.gProgress_setText.connect(mw.w_gProgress.setText)

                self.listen_thread.pProgressBar_setValue.connect(mw.w_pProgressBar.setValue)
                self.listen_thread.pProgress_setText.connect(mw.w_pProgress.setText)

                self.listen_thread.rProgressBar_setValue.connect(mw.w_rProgressBar.setValueAnimated)
                # self.listen_thread.gProgressETA_setText.connect(mw.w_gProgressETA.setText)

                self.timer_thread.gProgressETA_setText.connect(mw.w_gProgressETA.setText)

                self.listen_thread.listOfProjects_setCurrentItem.connect(mw.w_listOfProjects.setCurrentItem)
                self.listen_thread.listOfProjects_setStyleSheet.connect(mw.w_listOfProjects.setStyleSheet)

                # self.listen_thread.started.connect(self.listen_worker.run)
                # self.listen_worker.finished.connect(self.listen_thread.quit)

                # self.listen_worker.finished.connect(self.listen_worker.deleteLater)
                # self.listen_thread.finished.connect(self.listen_thread.deleteLater)

                self.listen_thread.start()
                self.timer_thread.start()

            preset.process.wait()

        if not preset.is_status('RENDERING_STOPPING'):
            preset.set_status('RENDERING_FINISHED')

        self.finished.emit()


################################################################################
# Timer & ETA

class RenderTimerThread(qtc.QThread):
    gProgressETA_setText = qtc.pyqtSignal(str)

    def __init__(self):
        super().__init__()

    def run(self):
        preset = store.preset

        while True:

            if not preset.is_status('RENDERING'):
                break

            current_time = time.time()

            # Elapsed time
            elasped_frame_time = current_time - preset.render_start_time
            elapsed_global_time = current_time - preset.global_render_start_time
            m, s = divmod(elapsed_global_time, 60)
            h, m = divmod(m, 60)

            # Average time
            avg_list = preset.render_avg_time[-3:]

            if avg_list:
                avg_time = sum(avg_list) / len(avg_list)
            else:
                avg_time = 0

            avg_m, avg_s = divmod(avg_time, 60)
            avg_h, avg_m = divmod(avg_m, 60)

            # Estimated time
            eta_time = (preset.global_frames + 1 - preset.global_frame) * avg_time

            if eta_time > 0:
                eta_time -= elasped_frame_time

            eta_m, eta_s = divmod(eta_time, 60)
            eta_h, eta_m = divmod(eta_m, 60)

            if eta_time < 0:
                print("eta:", eta_time, eta_h, eta_m, eta_s, "avg:", avg_time, "glob:", preset.global_frames, "fra:", preset.global_frame)

            tt = f'Elapsed: {h:02.0f}:{m:02.0f}:{s:02.0f} | AVG: {avg_h:02.0f}:{avg_m:02.0f}:{avg_s:02.0f} | ETA: {eta_h:02.0f}:{eta_m:02.0f}:{eta_s:02.0f}'

            self.gProgressETA_setText.emit(tt)

            time.sleep(1.0)

        self.finished.emit()


################################################################################

class RenderListenThread(qtc.QThread):

    finished = qtc.pyqtSignal()

    gProgressBar_setValue = qtc.pyqtSignal(int)
    gProgress_setText = qtc.pyqtSignal(str)

    pProgressBar_setValue = qtc.pyqtSignal(int)
    pProgress_setText = qtc.pyqtSignal(str)

    rProgressBar_setValue = qtc.pyqtSignal(int)

    listOfProjects_setCurrentItem = qtc.pyqtSignal(object)
    listOfProjects_setStyleSheet = qtc.pyqtSignal(str)


    def __init__(self):
        super().__init__()

        self.exit_message = None


    def stop_rendering(self, reason, exit_message=None):
        """
        Stop rendering process.
        """

        preset = store.preset
        log = main.log

        if reason == 'NOT_LOADED_SETTINGS':
            self.exit_message = 'Error during applying settings.'

        elif reason == 'UNSAVED_FRAMES':
            self.exit_message = 'Critical error, frames were not saved.'

        else:
            raise Exception(f'Bad reason: {reason}')

        if exit_message is not None:
            self.exit_message = exit_message

        if self.exit_message:
            log(self.exit_message)

        preset.stop_render()


    def run(self):
        """
        Print info from Blender console.
        """
        preset = store.preset
        mw = store.mw
        log = main.log

        # What is the current project we're rendering.
        current_project = None

        # What is the current frame we're rendering.
        current_frame = None

        # After project change, we should know if our settings were applied
        project_settings_flag = False

        # What renders were unsaved due to lack of VRAM or other issues.
        current_render = []
        saved_renders = []
        unsaved_renders = []

        while True:

            if preset.is_status('RENDERING_STOPPING', 'RENDERING_FINISHED'):
                break

            try:

                if not preset.process:
                    break

                for line in TextIOWrapper(preset.process.stdout, encoding='utf-8'):
                    log(line)

                    current_time = time.time()

                    # print("Saved:", saved_renders)
                    # print("Unsaved:", unsaved_renders)

                    # Change project
                    found = search(r'(?:.*)--background ["](.*?.blend)["].*?-f ["](.*?)["]', line)

                    if found:
                        project_settings_flag = True

                        file = found.group(1)
                        frames = found.group(2)
                        preset.last_frame_flag = None
                        preset.project_frame = 0
                        preset.project_frames = len(frames.split(','))

                        for i in range(mw.w_listOfProjects.count()):
                            item = mw.w_listOfProjects.item(i)
                            w_project = mw.w_listOfProjects.itemWidget(item)
                            project = w_project.project

                            if file.strip() != project.file.strip():
                                continue

                            current_project = project
                            self.listOfProjects_setCurrentItem.emit(item)

                        current_frame = None

                        continue

                    # Settings check
                    if project_settings_flag:
                        found = search(r'(?:.*)All settings loaded successfully!', line)

                        if found:
                            project_settings_flag = False
                            continue

                    # Local progress <100% with Tiles
                    found = search(r'(?:.*)Rendered (\d+)/(\d+) Tiles, Sample (\d+)/(\d+)', line)

                    if found:

                        if project_settings_flag:
                            self.stop_rendering(reason='NOT_LOADED_SETTINGS')
                            continue

                        tile = int(found.group(1))
                        tiles = int(found.group(2))
                        sample = int(found.group(3))
                        samples = int(found.group(4))
                        progress = max(0.0, min(1.0, (tile * samples + sample) / (tiles * samples)))

                        self.rProgressBar_setValue.emit(round(progress * 100))

                        continue

                    # Local progress <100%
                    found = search(r'(?:.*)Sample (\d+)/(\d+)', line)

                    if found:

                        if project_settings_flag:
                            self.stop_rendering(reason='NOT_LOADED_SETTINGS')
                            continue

                        sample = int(found.group(1))
                        samples = int(found.group(2))
                        progress = max(0.0, min(1.0, float(sample) / float(samples)))

                        self.rProgressBar_setValue.emit(round(progress * 100))

                        continue

                    # Progress 100%
                    found = search(r'(?:.*)Saved: [\'|\"](.*?)[\'|\"]', line)

                    if found:

                        if project_settings_flag:
                            self.stop_rendering(reason='NOT_LOADED_SETTINGS')
                            continue

                        file = found.group(1)
                        preset.renders_list.append(file)
                        preset.render_avg_time.append(current_time - preset.render_start_time)
                        preset.render_start_time = current_time

                        self.rProgressBar_setValue.emit(100)
                        self.pProgressBar_setValue.emit(100)
                        self.gProgress_setText.emit(f'{preset.global_frame}/{preset.global_frames}')
                        self.pProgress_setText.emit(f'{preset.project_frame}/{preset.project_frames}')

                        if current_render and current_render not in saved_renders:
                            saved_renders.append(current_render)

                        current_render = None
                        current_frame = None

                        mw.update_widgets.emit()

                        continue

                    # Progress...
                    found = search(r'(?:.*)Rendering single frame \(frame (\d+)\)', line)

                    if not found:
                        found = search(r'(?:.*)Rendering frame (\d+)', line)

                    if found:

                        if project_settings_flag:
                            self.stop_rendering(reason='NOT_LOADED_SETTINGS')
                            continue

                        current_frame = int(found.group(1))
                        preset.frame_flag = current_frame

                        if preset.frame_flag != preset.last_frame_flag:
                            preset.last_frame_flag = preset.frame_flag

                            preset.global_frame += 1
                            preset.project_frame += 1
                            gProgress = max(0.0, min(1.0, (preset.global_frame - 1) / preset.global_frames))
                            pProgress = max(0.0, min(1.0, (preset.project_frame -1 ) / preset.project_frames))

                            self.gProgressBar_setValue.emit(round(gProgress * 100))
                            self.pProgressBar_setValue.emit(round(pProgress * 100))
                            self.gProgress_setText.emit(f'{max(0, preset.global_frame - 1)}/{preset.global_frames}')
                            self.pProgress_setText.emit(f'{max(0, preset.project_frame - 1)}/{preset.project_frames}')

                            if current_render and current_render not in unsaved_renders:
                                unsaved_renders.append(current_render)

                                # Delete old render if the new one was not saved
                                p, f = current_render
                                path = Path(p.compose_render_filename(f))

                                if path.exists():
                                    print(f'Removed: {path}')
                                    path.unlink()

                            current_render = [current_project, current_frame]

                        continue

                if not preset.process:
                    break

                for line in TextIOWrapper(preset.process.stdin, encoding='utf-8'):
                    log(line)

            except Exception as e:
                log(f'Exception during listening: {repr(e)}')


        if preset.is_status('RENDERING_FINISHED'):
            self.gProgress_setText.emit(f'{preset.global_frame}/{preset.global_frames}')
            self.pProgress_setText.emit(f'{preset.project_frame}/{preset.project_frames}')
            self.gProgressBar_setValue.emit(100)
            self.rProgressBar_setValue.emit(100)

            audio.play(RENDER_FINISH_AUDIO)
            log("Rendering finished.")

            preset.shutdown()

        elif preset.is_status('RENDERING_STOPPING'):
            audio.play(RENDER_STOP_AUDIO)
            log("Rendering stopped.")

        else:
            log(f"Status: {preset.blender_status}")

        if self.exit_message:
            log(self.exit_message)

        preset.set_status('READY_TO_RENDER')

        monitor.screen_on()

        mw.update_widgets.emit()
        self.finished.emit()
