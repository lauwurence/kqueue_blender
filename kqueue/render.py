################################################################################
## Queue Preset

import time
import subprocess
import PyQt5.QtCore as qtc

from re import search
from io import TextIOWrapper
from pathlib import Path
from .utils.path import join
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

            if not project.active:
                continue

            if preset.is_status('RENDERING_STOPPING', 'RENDERING_FINISHED'):
                break

            sc = project.get_scene()
            fl = project.get_frames_list()
            ca = project.get_camera()

            if not sc or not fl or not ca:
                continue

            PYTOH_FILE = join(store.working_dir, "blender/temp/render_settings.py")

            if preset.preview_render:
                PYTHON = f"""
import bpy

scene = bpy.context.scene
render = scene.render
shading = scene.display.shading

# Output
scene.camera = bpy.data.objects["{ca}"]
render.filepath = "{project.get_render_filepath().replace('\\', '/')}"
render.use_overwrite = True
render.use_simplify = True
render.simplify_subdivision_render = 0
render.use_border = False

# Render
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
                PYTHON = f"""
import bpy

scene = bpy.context.scene
cycles = scene.cycles
render = scene.render

# Output
scene.camera = bpy.data.objects["{ca}"]
render.use_persistent_data = {project.get_use_persistent_data()}
render.filepath = "{project.get_render_filepath().replace('\\', '/')}"
render.use_overwrite = True
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

# Compositor
render.compositor_device = "GPU"
render.compositor_precision = "FULL"
"""

            # Technically, take scene settings and assigning sRGB
            if preset.assign_srgb or True:
                PYTHON += "\nrender.image_settings.color_management = 'FOLLOW_SCENE'"
                PYTHON += "\nscene.display_settings.display_device = 'sRGB'"

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

                # self.listen_thread = qtc.QThread()
                # self.listen_worker = RenderListenThread()
                # self.listen_worker.moveToThread(self.listen_thread)

                self.listen_thread.gProgressBar_setValue.connect(mw.w_gProgressBar.setValue)
                self.listen_thread.gProgress_setText.connect(mw.w_gProgress.setText)

                self.listen_thread.pProgressBar_setValue.connect(mw.w_pProgressBar.setValue)
                self.listen_thread.pProgress_setText.connect(mw.w_pProgress.setText)

                self.listen_thread.rProgressBar_setValue.connect(mw.w_rProgressBar.setValue)
                self.listen_thread.gProgressETA_setText.connect(mw.w_gProgressETA.setText)

                self.listen_thread.listOfProjects_setCurrentItem.connect(mw.w_listOfProjects.setCurrentItem)
                self.listen_thread.listOfProjects_setStyleSheet.connect(mw.w_listOfProjects.setStyleSheet)

                # self.listen_thread.started.connect(self.listen_worker.run)
                # self.listen_worker.finished.connect(self.listen_thread.quit)

                # self.listen_worker.finished.connect(self.listen_worker.deleteLater)
                # self.listen_thread.finished.connect(self.listen_thread.deleteLater)

                self.listen_thread.start()

            preset.process.wait()

        if not preset.is_status('RENDERING_STOPPING'):
            preset.set_status('RENDERING_FINISHED')

        self.finished.emit()


################################################################################

class RenderListenThread(qtc.QThread):

    finished = qtc.pyqtSignal()

    gProgressBar_setValue = qtc.pyqtSignal(int)
    gProgress_setText = qtc.pyqtSignal(str)

    pProgressBar_setValue = qtc.pyqtSignal(int)
    pProgress_setText = qtc.pyqtSignal(str)

    rProgressBar_setValue = qtc.pyqtSignal(int)
    gProgressETA_setText = qtc.pyqtSignal(str)

    listOfProjects_setCurrentItem = qtc.pyqtSignal(object)
    listOfProjects_setStyleSheet = qtc.pyqtSignal(str)


    def __init__(self):
        super().__init__()


    def run(self):
        """
        Print info from Blender console.
        """
        preset = store.preset
        mw = store.mw
        log = main.log

        while True:

            if preset.is_status('RENDERING_STOPPING', 'RENDERING_FINISHED'):
                break

            try:
                if not preset.process:
                    break

                for line in TextIOWrapper(preset.process.stdout, encoding='utf-8'):
                    log(line)

                    current_time = time.time()

                    # Elapsed time
                    elapsed_time = current_time - preset.global_render_start_time
                    m, s = divmod(elapsed_time, 60)
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
                    eta_time = (preset.get_global_frames_number() + 1 - preset.global_frame) * avg_time
                    eta_m, eta_s = divmod(eta_time, 60)
                    eta_h, eta_m = divmod(eta_m, 60)

                    self.gProgressETA_setText.emit(f'Elapsed: {h:02.0f}:{m:02.0f}:{s:02.0f} | AVG: {avg_h:02.0f}:{avg_m:02.0f}:{avg_s:02.0f} | ETA: {eta_h:02.0f}:{eta_m:02.0f}:{eta_s:02.0f}')

                    # Change project
                    found = search(r'(?:.*)--background ["](.*?.blend)["].*?-f ["](.*?)["]', line)

                    if found:
                        file = found.group(1)
                        frames = found.group(2)
                        preset.last_frame_flag = None
                        preset.project_frame = 0
                        preset.project_frames = len(frames.split(','))

                        for i in range(mw.w_listOfProjects.count()):
                            item = mw.w_listOfProjects.item(i)
                            w_project = mw.w_listOfProjects.itemWidget(item)

                            if file.strip() != w_project.project.file.strip():
                                continue

                            self.listOfProjects_setCurrentItem.emit(item)
                            self.listOfProjects_setStyleSheet.emit("""
                                QListView::item:selected {
                                    color: rgb(25, 25, 25);
                                    background-color: rgb(255, 255, 255);
                                    border: 1px solid #e87d0d;
                                    border-radius: 4px;
                                }
                                QListView::item {
                                    color: rgb(125, 125, 125);
                                }
                                QListWidget {
                                    background-color: rgb(225, 225, 225);
                                    color: rgb(25, 25, 25);
                                    border-radius: 6px;
                                    padding: 2px;
                                    font-size: 12px;
                                }
                            """)
                            break

                        continue

                    # Local progress <100%
                    found = search(r'(?:.*)Rendered (\d+)/(\d+) Tiles, Sample (\d+)/(\d+)', line)

                    if found:
                        tile = int(found.group(1))
                        tiles = int(found.group(2))
                        sample = int(found.group(3))
                        samples = int(found.group(4))
                        progress = max(0.0, min(1.0, (tile * samples + sample) / (tiles * samples)))

                        self.rProgressBar_setValue.emit(round(progress * 100))

                        continue

                    # Progress 100%
                    found = search(r'(?:.*)Saved: [\'|\"](.*?)[\'|\"]', line)

                    if found:
                        file = found.group(1)
                        preset.renders_list.append(file)
                        preset.render_avg_time.append(current_time - preset.render_start_time)
                        preset.render_start_time = current_time

                        self.rProgressBar_setValue.emit(100)
                        self.pProgressBar_setValue.emit(100)
                        self.gProgress_setText.emit(f'{preset.global_frame}/{preset.global_frames}')
                        self.pProgress_setText.emit(f'{preset.project_frame}/{preset.project_frames}')

                        mw.update_widgets.emit()

                        continue

                    # Progress
                    found = search(r'(?:.*)Rendering single frame \(frame (\d+)\)', line)

                    if not found:
                        found = search(r'(?:.*)Rendering frame (\d+)', line)

                    if found:
                        preset.frame_flag = int(found.group(1))

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

        preset.set_status('READY_TO_RENDER')
        self.listOfProjects_setStyleSheet.emit("""
            QListWidget {
                background-color: rgb(255, 255, 255);
                color: rgb(25, 25, 25);
                border-radius: 6px;
                padding: 2px;
                font-size: 12px;
            }
            QListView::item:selected {
                color: #448fff;
                background-color: rgb(255, 255, 255);
                border: 1px solid #448fff;
                border-radius: 4px;
            }
        """)

        monitor.screen_on()

        mw.update_widgets.emit()
        self.finished.emit()
