################################################################################
## Main

import json
import subprocess

import PyQt5.QtWidgets as qtw
import PyQt5.QtGui as qtg
import PyQt5.QtCore as qtc
from PyQt5.QtCore import Qt

from os import getcwd, makedirs
from sys import exit
from time import time, sleep
from pathlib import Path
from psutil import Process
from threading import Thread
from ctypes import windll

from .utils import monitor
from .utils.path import join, open_folder, open_image
from .project import BlendProject, BlendProjectWindow
from .render import RenderWorker
from .config import *
from . import store

if hasattr(Qt, 'AA_EnableHighDpiScaling'):
    qtw.QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)

if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
    qtw.QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

################################################################################

DEV_MODE = False
store.working_dir = join(getcwd() + "/kqueue")


################################################################################

class QueuePreset():

    def __init__(self):

        # Loaded save filename.
        self.loaded_save = None

        # Path to Blender executable.
        self.blender_exe = None

        # List of project objects.
        self.project_list = []

        # Process object.
        self.process = None

        # Status.
        self.blender_status = 'READY_TO_RENDER'

        # Are we currently loading new blender projects?
        self.is_adding_projects = False

        # Are we currently shutting down the PC?
        self.is_shutting_down = False

        # Save needed?
        self.save_needed = False

        # Enable selective render?
        self.selective_render = False

        # Assign sRGB profile?
        self.assign_srgb = True

        # Render preview?
        self.preview_render = False

        self.init_render_variables()


    def need_save(self, value=True):
        """
        Does the project need saving?
        """

        if value == self.save_needed:
            return

        self.save_needed = value
        mw.update_title()


    def init_render_variables(self, gui=False):
        """
        Initialize or reset render variables for GUI.

        `gui` - update interface?
        """

        self.global_render_start_time = time()
        self.render_start_time = time()
        self.render_avg_time = set()
        self.global_frame = 0
        self.global_frames = 0
        self.project_frame = 0
        self.project_frames = 0
        self.renders_list = []

        self.frame_flag = 0
        self.last_frame_flag = None

        if gui:
            mw.w_gProgressBar.setValue(0)
            mw.w_pProgressBar.setValue(0)
            mw.w_rProgressBar.setValue(0)


    def set_status(self, value, gui=True):
        """
        Set current status.
        """

        if value not in ['READY_TO_RENDER', 'RENDERING', 'RENDERING_STOPPING', 'RENDERING_FINISHED']:
            raise Exception(f'Unknown status "{value}".')

        self.blender_status = value
        # if gui: log(f'Status: {self.blender_status}', developer=True)


    def is_status(self, *values):
        """
        Check current status.
        """

        for value in values:

            if value not in ['READY_TO_RENDER', 'RENDERING', 'RENDERING_STOPPING', 'RENDERING_FINISHED']:
                raise Exception(f'Unknown status "{value}".')

        return self.blender_status in values


    def locate_blender(self):
        """
        Locate Blender executable file.
        """

        filename, _ = qtw.QFileDialog.getOpenFileName(mw, 'Single File', "H:/Blender Foundation/", 'blender.exe')

        if not filename:
            return

        self.set_blender(filename)


    def set_blender(self, filename):
        """
        Set current Blender executable.
        """

        if filename == self.blender_exe:
            return

        self.blender_exe = filename
        mw.w_pathToBlender.setText(filename)

        log(f'Blender: {filename}')
        self.need_save()


    def save_as(self):
        """
        Save project state as a file.
        """

        path = join(store.working_dir, SAVE_FOLDER)
        makedirs(path, exist_ok=True)

        filename, _ = qtw.QFileDialog.getSaveFileName(mw, 'Save', path, "kQueue Project (*.kqp)")

        if not filename:
            return

        from .save_load import save
        save([self.project_list, self.blender_exe], filename, version=1)

        self.set_save(filename)
        self.need_save(False)


    def load_from(self):
        """
        Load save from...
        """

        path = join(store.working_dir, SAVE_FOLDER)
        makedirs(path, exist_ok=True)

        filename, _ = qtw.QFileDialog.getOpenFileName(mw, 'Load', path, "kQueue Project (*.kqp)")

        if not filename:
            return

        from .save_load import load
        version, data = load(filename)

        if version == 1:
            self.project_list, blender_exe = data
            self.set_blender(blender_exe)

        self.set_save(filename)
        self.need_save(False)

        mw.update_list()


    def set_save(self, filename):
        """
        Set currently loaded save.
        """

        if not filename or not Path(filename).exists():
            return

        self.loaded_save = filename
        log(f'Current file: {filename}')

        mw.update_title()


    def add_projects(self, *files):
        """
        Add projects in background.
        """

        if not self.blender_exe:
            log("Locate blender.exe first!")
            return

        if self.is_adding_projects:
            return


        def do_add_projects(*files):

            makedirs(join(store.working_dir, "blender/temp"), exist_ok=True)
            CACHE_FILE = join(store.working_dir, "blender/cache.json")
            DATA_FILE = join(store.working_dir, "blender/temp/data.json")
            GET_DATA_PY = join(store.working_dir, "blender/get_data.py")

            self.is_adding_projects = True
            mw.update()

            # Read cache
            if Path(CACHE_FILE).exists():
                try:
                    with open(CACHE_FILE, 'r') as json_file:
                        cache = json.load(json_file)
                except:
                    log(f'Error reading cache file: {CACHE_FILE}')
                    return
            else:
                cache = {}

            files = [ join(file) for file in files if file.endswith(".blend")]
            amount = 0

            for i, file in enumerate(files):
                mod_time = int(Path(file).stat().st_mtime)

                skip = False

                for project in self.project_list:
                    if file == project.file:
                        skip = True
                        break

                if skip:
                    continue

                if not amount:
                    print("------------------------")
                    log("Loading new projects...")

                # Get cached project data
                if file in cache and cache[file]['mod_time'] == mod_time:
                    data = cache[file]
                    log(f'({i + 1}/{len(files)}) Loading cache: {file}')

                # Get project data
                else:
                    BATCH_FILE = join(store.working_dir, f'blender/temp/get_data.bat')
                    BATCH = f"""
@CHCP 65001 > NUL
blender "{file}" --factory-startup --background  --python "{GET_DATA_PY}" "{DATA_FILE}"
"""

                    with open(BATCH_FILE, 'w') as f:
                        f.write(BATCH.strip())

                    log(f'({i + 1}/{len(files)}) Opening project: {file}')

                    process = subprocess.Popen([BATCH_FILE],
                                            # stderr=subprocess.STDOUT,
                                            # stdout=subprocess.PIPE,
                                            # stdin=subprocess.PIPE,
                                            #    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP, #DETACHED_PROCESS
                                            #    creationflags=subprocess.DETACHED_PROCESS, #DETACHED_PROCESS
                                            #    preexec_fn=os.setsid,
                                            cwd=join(Path(self.blender_exe).parent),
                                            shell=True
                                            )

                    process.wait()

                    if not Path(DATA_FILE).exists():
                        log(f'Could not fetch project data: {file} | Data: {DATA_FILE}')
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

                self.project_list.append(project)
                mw.update_list(rearrange=False)
                amount += 1

                self.need_save()

            if amount: log(f'All projects loaded!')
            self.is_adding_projects = False
            mw.update()

        t = Thread(target=do_add_projects, args=tuple(files))
        t.start()


    def start_render(self):
        """
        Start rendering process.
        """

        if not self.is_status('READY_TO_RENDER') or not preset.project_list:
            return

        self.init_render_variables(gui=True)

        for project in self.project_list:
            self.global_frames += len(project.get_frames_list())

        self.render_thread = qtc.QThread()
        self.render_worker = RenderWorker()
        self.render_worker.moveToThread(self.render_thread)

        self.render_thread.started.connect(self.render_worker.run)
        self.render_thread.finished.connect(self.render_thread.deleteLater)

        self.render_worker.finished.connect(self.render_thread.quit)
        self.render_worker.finished.connect(self.render_worker.deleteLater)

        self.render_thread.start()


    def stop_render(self):
        """
        Stop rendering process.
        """

        if not self.is_status('RENDERING') or not self.process:
            return

        if self.is_status('RENDERING_STOPPING'):
            return

        self.set_status('RENDERING_STOPPING')
        log("Stopping rendering...")

        for proc in Process(self.process.pid).children(recursive=True):
            proc.terminate()

        self.process.terminate()
        self.process = None


    def shutdown(self, delay=15.0):
        """
        Show countdown and shotdown PC.
        """

        if mw.w_onComplete.currentText() != 'SHUTDOWN':
            return

        def do_shutdown(delay):
            self.is_shutting_down = True
            mw.update()
            monitor.screen_on()

            for i in range(int(delay)):
                d = delay - i
                log(f'Shutting down in {d:.0f} {"seconds" if d > 1 else "second"}.')
                mw.update()
                sleep(1)

                if not self.is_shutting_down:
                    log("Shutting down was cancelled.")
                    return

            log("Shutting down...")

            if not DEV_MODE:
                subprocess.call(["shutdown", "-s", "-t", "15"])

            mw.update()

        t = Thread(target=do_shutdown, args=(delay,))
        t.start()


    def cancel_shutdown(self):
        """
        Cancel shutting down process.
        """

        self.is_shutting_down = False
        mw.update()


################################################################################
## Main Window

class MainWindow(qtw.QMainWindow):

    def __init__(self):
        super().__init__()

        self.update_title()
        self.setWindowIcon(qtg.QIcon(ICON))

        self.setMinimumWidth(1200)
        self.setMinimumHeight(600)
        self.setAcceptDrops(True)
        self.setAttribute(Qt.WA_DeleteOnClose)

        # ! [widget]
        w = qtw.QWidget()
        self.setCentralWidget(w)

        # ! [vbox]
        w_vBoxLayout = qtw.QVBoxLayout()
        w.setLayout(w_vBoxLayout)

        if True:
            # ! [hbox] Locate Blender Horizontal Box
            w_hBoxLayout = qtw.QHBoxLayout()
            w_vBoxLayout.addLayout(w_hBoxLayout)

            # [button] Save
            self.w_locateSave = w_locateSave = qtw.QPushButton("", clicked=lambda: preset.save_as())
            w_locateSave.clicked.connect(lambda: self.update())
            w_locateSave.setIcon(qtg.QIcon('kqueue/icons/save.svg'))
            w_locateSave.setToolTip("Save the current file in the desired location.")
            # w_locateSave.setFixedWidth(100)
            w_hBoxLayout.addWidget(w_locateSave)

            # [button] Load
            self.w_locateLoad = w_locateLoad = qtw.QPushButton("", clicked=lambda: preset.load_from())
            w_locateLoad.clicked.connect(lambda: self.update())
            w_locateLoad.setIcon(qtg.QIcon('kqueue/icons/folder.svg'))
            w_locateLoad.setToolTip("Open a kQueue file.")
            # w_locateLoad.setFixedWidth(100)
            w_hBoxLayout.addWidget(w_locateLoad)

            # [button] Locate Blender
            self.w_locateBlender = w_locateBlender = qtw.QPushButton("", clicked=lambda: preset.locate_blender())
            w_locateBlender.clicked.connect(lambda: self.update())
            w_locateBlender.setIcon(qtg.QIcon('kqueue/icons/blender.svg'))
            w_locateBlender.setToolTip("Locate a Blender executable.")
            # w_locateBlender.setFixedWidth(100)
            w_hBoxLayout.addWidget(w_locateBlender)

            # [edit] Path to Blender
            self.w_pathToBlender = w_pathToBlender = qtw.QLineEdit("Locate blender.exe first!")
            w_pathToBlender.setEnabled(False)
            w_hBoxLayout.addWidget(w_pathToBlender)

            # [button] Locate Blender
            self.w_openFolder = w_openFolder = qtw.QPushButton("Open Folder", clicked=lambda: open_folder(preset.blender_exe))
            w_openFolder.setFixedWidth(100)
            w_openFolder.setEnabled(False)
            w_hBoxLayout.addWidget(w_openFolder)

        # [list] List of Projects
        def open_project_settings(self):
            project = self.get_selected_project()
            self.sw = BlendProjectWindow(project)
            self.sw.show()

        self.w_listOfProjects = w_listOfProjects = qtw.QListWidget()
        w_listOfProjects.itemDoubleClicked.connect(lambda: open_project_settings(self))
        w_listOfProjects.setDragDropMode(qtw.QAbstractItemView.InternalMove)
        w_listOfProjects.model().rowsMoved.connect(lambda: self.update_list(rearrange=True))
        w_vBoxLayout.addWidget(w_listOfProjects)

        # # [label] Global Settings
        # w_globalSettings = qtw.QLabel("Global Settings:")
        # w_vBoxLayout.addWidget(w_globalSettings)

        # # [form] Preset Override
        # l_presetOverride = qtw.QFormLayout()
        # w_vBoxLayout.addLayout(l_presetOverride)

        # # [edit] Samples
        # w_presetSamples = qtw.QLineEdit()
        # l_presetOverride.addRow("Samples", w_presetSamples)

        # [label] Output
        self.w_logOutput = qtw.QLabel("...")
        self.w_logOutput.setFixedHeight(40)
        self.w_logOutput.setEnabled(False)
        w_vBoxLayout.addWidget(self.w_logOutput)

        # ! [hbox] Global Progress
        w_hBoxLayout = qtw.QHBoxLayout()
        w_vBoxLayout.addLayout(w_hBoxLayout)

        # [label] Global Progress
        self.w_gProgress = w_gProgress = qtw.QLabel("Global:")
        w_hBoxLayout.addWidget(w_gProgress)

        # [bar] Global Progress Bar
        self.w_gProgressBar = w_gProgressBar = qtw.QProgressBar(self)
        w_gProgressBar.setRange(0, 100)
        w_gProgressBar.setValue(0)
        w_gProgressBar.setFixedHeight(20)
        # w_gProgressBar.setTextVisible(False)
        w_hBoxLayout.addWidget(w_gProgressBar)

        # ! [hbox] Project Progress
        w_hBoxLayout = qtw.QHBoxLayout()
        w_vBoxLayout.addLayout(w_hBoxLayout)

        # [label] Project Progress
        self.w_pProgress = w_pProgress = qtw.QLabel("Project:")
        w_hBoxLayout.addWidget(w_pProgress)

        # [bar] Project Progress Bar
        self.w_pProgressBar = w_pProgressBar = qtw.QProgressBar(self)
        w_pProgressBar.setRange(0, 100)
        w_pProgressBar.setValue(0)
        w_pProgressBar.setFixedHeight(10)
        w_pProgressBar.setTextVisible(False)
        w_hBoxLayout.addWidget(w_pProgressBar)


        # ! [hbox] Render Progress
        w_hBoxLayout = qtw.QHBoxLayout()
        w_vBoxLayout.addLayout(w_hBoxLayout)

        # [bar] Render Progress Bar
        self.w_rProgressBar = w_rProgressBar = qtw.QProgressBar(self)
        w_rProgressBar.setRange(0, 100)
        w_rProgressBar.setValue(0)
        w_rProgressBar.setFixedHeight(4)
        w_rProgressBar.setTextVisible(False)
        w_hBoxLayout.addWidget(w_rProgressBar)

        # [label] Global Progress
        self.w_gProgressETA = w_gProgressETA = qtw.QLabel()
        w_vBoxLayout.addWidget(w_gProgressETA)

        # w_vBoxLayout.addSpacing(10)



        # [check] Preview Render
        self.w_preview_render = w_preview_render = qtw.QCheckBox("Preview Render")
        w_vBoxLayout.addWidget(w_preview_render)

        def toggle_preview_render():
            preset.preview_render = w_preview_render.isChecked()
            self.update_list()
            print(preset.preview_render)

        w_preview_render.clicked.connect(lambda: toggle_preview_render())

        # [check] Selective Render
        self.w_selective = w_selective = qtw.QCheckBox("Selective Render")
        w_vBoxLayout.addWidget(w_selective)

        def toggle_selective():
            preset.selective_render = w_selective.isChecked()
            self.update_list()
            print(preset.selective_render)

        w_selective.clicked.connect(lambda: toggle_selective())

        # [check] Assign sRGB
        self.w_assign_srgb = w_assign_srgb = qtw.QCheckBox("Save as sRGB (preserve View, Look etc.)")
        w_vBoxLayout.addWidget(w_assign_srgb)

        def toggle_assign_srgb():
            preset.assign_srgb = w_assign_srgb.isChecked()
            self.update_list()
            print(preset.assign_srgb)

        w_assign_srgb.clicked.connect(lambda: toggle_assign_srgb())




        # ! [hbox] Start and Stop Render
        w_hBoxLayout = qtw.QHBoxLayout()
        w_vBoxLayout.addLayout(w_hBoxLayout)

        # ! [hbox] On Complete
        w_hBoxLayoutOnComplete = qtw.QHBoxLayout()
        w_hBoxLayout.addLayout(w_hBoxLayoutOnComplete)

        # [label] On Complete
        w_onCompleteLabel = qtw.QLabel("On Complete:")
        w_onCompleteLabel.setFixedHeight(40)
        w_hBoxLayoutOnComplete.addWidget(w_onCompleteLabel)

        # [box] On Complete
        self.w_onComplete = w_onComplete = qtw.QComboBox()
        w_onComplete.setFixedWidth(100)
        w_onComplete.setFixedHeight(25)
        w_onComplete.addItems(['NONE', 'SHUTDOWN'])
        w_onComplete.setCurrentText('NONE')
        w_hBoxLayoutOnComplete.addWidget(w_onComplete)

        # # [button] Shutdown
        # w_shutdown = qtw.QPushButton("Shutdown", clicked=lambda: preset.shutdown())
        # w_hBoxLayoutOnComplete.addWidget(w_shutdown)

        # [button] Cancel Shutdown
        self.w_cancelShutdown = w_cancelShutdown = qtw.QPushButton("Cancel", clicked=lambda: preset.cancel_shutdown())
        w_cancelShutdown.setFixedHeight(30)
        w_cancelShutdown.setEnabled(False)
        w_hBoxLayoutOnComplete.addWidget(w_cancelShutdown, 2, Qt.AlignLeft)

        # ! [hbox] Start & Stop
        w_hBoxLayoutRender = qtw.QHBoxLayout()
        w_hBoxLayout.addLayout(w_hBoxLayoutRender)

        # [button] Start Render
        self.w_startRender = w_startRender = qtw.QPushButton("", clicked=lambda: preset.start_render())
        w_startRender.setIcon(qtg.QIcon('kqueue/icons/play.svg'))
        w_startRender.setToolTip("Start rendering.")
        w_startRender.setFixedWidth(100)
        w_startRender.setFixedHeight(40)
        w_startRender.setEnabled(False)
        w_hBoxLayoutRender.addWidget(w_startRender)

        # [button] Stop Render
        self.w_stopRender = w_stopRender = qtw.QPushButton("", clicked=lambda: preset.stop_render())
        w_stopRender.setIcon(qtg.QIcon('kqueue/icons/stop.svg'))
        w_stopRender.setToolTip("Stop rendering.")
        w_stopRender.setFixedWidth(100)
        w_stopRender.setFixedHeight(40)
        w_stopRender.setEnabled(False)
        w_hBoxLayoutRender.addWidget(w_stopRender, 1, Qt.AlignLeft)

        w_hBoxLayout.addSpacing(10)

        # [button] Open Render
        def open_render():
            if not preset.renders_list:
                return
            open_image(preset.renders_list[-1])

        self.w_openRender = w_openRender = qtw.QPushButton("", clicked=lambda: open_render())
        w_openRender.setIcon(qtg.QIcon('kqueue/icons/open_render.svg'))
        w_openRender.setToolTip("Open last saved render.")
        w_openRender.setFixedWidth(40)
        w_openRender.setFixedHeight(40)
        w_hBoxLayout.addWidget(w_openRender)

        # [button] Open Render Folder
        def open_render_folder():
            if not preset.renders_list:
                return
            open_folder(preset.renders_list[-1])

        self.w_openRenderFolder = w_openRenderFolder = qtw.QPushButton("Open Folder", clicked=lambda: open_render_folder())
        # w_openRenderFolder.setIcon(qtg.QIcon('kqueue/icons/folder.svg'))
        w_openRenderFolder.setToolTip("Open last saved render folder.")
        w_openRenderFolder.setFixedWidth(80)
        w_openRenderFolder.setFixedHeight(40)
        w_hBoxLayout.addWidget(w_openRenderFolder)

        # [button] Screens Off
        w_screensOff = qtw.QPushButton("", clicked=lambda: monitor.screen_off())
        w_screensOff.setIcon(qtg.QIcon('kqueue/icons/screen_off.svg'))
        w_screensOff.setToolTip("Turn off the screens.")
        w_screensOff.setFixedWidth(40)
        w_screensOff.setFixedHeight(40)
        w_hBoxLayout.addWidget(w_screensOff)


    def update_title(self):
        """
        """

        title = TITLE if not DEV_MODE else APPID
        title += " " + ".".join([str(v) for v in VERSION])

        if store.preset and store.preset.loaded_save:
            filename = store.preset.loaded_save
            save_needed = store.preset.save_needed

            fn = filename.rsplit("/", 1)[-1].rsplit(".", 1)[0]
            title = f'{fn} [{filename}] - {title}'

            if save_needed:
                title = "* " + title

        else:
            title = f'(Unsaved) - {title}'

        self.setWindowTitle(title)


    def update_list(self, rearrange=False):
        """
        Update list widget and `preset.project_list` list.
        """

        if rearrange:
            file_list = []

            for i in range(self.w_listOfProjects.count()):
                item = self.w_listOfProjects.item(i)
                file_list.append(item.text().split(".blend")[0] + ".blend")

            project_list = preset.project_list.copy()
            preset.project_list = []

            for file in file_list:
                for project in project_list:
                    if file == project.file: preset.project_list.append(project)

        self.w_listOfProjects.clear()

        for project in preset.project_list:
            self.w_listOfProjects.addItem(f'{project.file} ({project.get_frames()} | {project.get_samples()} samples | {project.camera}) => {project.get_render_filepath()}')
            print(project.file)

        global_frames = 0
        project_frames = None

        for project in preset.project_list:
            frames = len(project.get_frames_list())
            global_frames += frames

            if project_frames is None:
                project_frames = frames

        self.w_gProgress.setText(f'0/{global_frames}' if global_frames or preset.project_list else "Global:")
        self.w_pProgress.setText(f'0/{project_frames}' if project_frames or preset.project_list else "Project:")

        self.w_gProgressBar.setValue(0)
        self.w_pProgressBar.setValue(0)
        self.w_rProgressBar.setValue(0)


    def update(self):

        if preset.is_status('RENDERING') or preset.is_status('RENDERING_STOPPING'):
            self.w_locateSave.setEnabled(False)
            self.w_locateLoad.setEnabled(False)
            self.w_locateBlender.setEnabled(False)
            self.w_selective.setEnabled(False)
            self.w_assign_srgb.setEnabled(False)
            self.w_preview_render.setEnabled(False)

        else:
            self.w_locateSave.setEnabled(True)
            self.w_locateLoad.setEnabled(True)
            self.w_locateBlender.setEnabled(True)
            self.w_selective.setEnabled(True)
            self.w_assign_srgb.setEnabled(True)
            self.w_preview_render.setEnabled(True)

        self.w_openFolder.setEnabled(bool(preset.blender_exe))
        self.w_startRender.setEnabled(bool(preset.blender_exe and not preset.is_status('RENDERING') and preset.project_list))
        self.w_stopRender.setEnabled(preset.is_status('RENDERING') and not preset.is_status('RENDERING_STOPPING'))
        self.w_listOfProjects.setEnabled(bool(not preset.is_adding_projects and not preset.is_status('RENDERING')))
        self.w_cancelShutdown.setEnabled(bool(preset.is_shutting_down))
        self.w_openRender.setEnabled(bool(preset.renders_list))
        self.w_openRenderFolder.setEnabled(bool(preset.renders_list))

        self.w_selective.setChecked(bool(preset.selective_render))
        self.w_assign_srgb.setChecked(bool(preset.assign_srgb))
        self.w_preview_render.setChecked(bool(preset.preview_render))


    def dragEnterEvent(self, event):

        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()


    def keyPressEvent(self, event):

        if event.key() == Qt.Key_Delete:

            if preset.project_list:
                project = self.get_selected_project()
                preset.project_list.remove(project)
                self.update_list()
                self.update()


    def get_selected_project(self):
        """
        Get selected project.
        """

        item = self.w_listOfProjects.currentItem()
        file = item.text().split(".blend")[0] + ".blend"

        for p in preset.project_list:

            if p.file == file:
                return p

        return None


    def dropEvent(self, event):
        """
        Add project.
        """

        files = [ url.toLocalFile() for url in event.mimeData().urls() ]
        preset.add_projects(*files)


    def closeEvent(self, event):
        """
        Close [x] event.
        """

        result = qtw.QMessageBox.question(self,
                      "Confirm Exit...",
                      "Are you sure you want to exit?",
                      qtw.QMessageBox.Yes| qtw.QMessageBox.No)
        event.ignore()

        if result == qtw.QMessageBox.Yes:
            preset.stop_render()
            event.accept()


    def set_log_text(self, line):
        self.w_logOutput.setText(line)


    def log(self, *args, **kwargs):
        log(*args, **kwargs)


def log(*args, developer=False):
    """
    Print log in console and output text.
    """

    if developer and not DEV_MODE:
        return

    line = " ".join(args).rstrip()

    if not line:
        return

    if not line.startswith('WARN '):
        mw.set_log_text(line)

    print(line)


################################################################################

windll.shell32.SetCurrentProcessExplicitAppUserModelID(APPID)
store.app = app = qtw.QApplication([])
store.mw = mw = MainWindow()
store.preset = preset = QueuePreset()
mw.update()

app.setStyleSheet('''
QLabel {
    font-size: 10px;
}
QPushButton {
    font-size: 10px;
}
QLineEdit {
    font-size: 10px;
}
QComboBox {
    font-size: 10px;
}
QProgressBar {
    background-color: rgb(200, 200, 200);
    color: rgb(255, 255, 255);
    border-style: none;
    border-radius: 4px;
    text-align: center;
    font-size: 12px;
}
QProgressBar::chunk {
    border-radius: 14px;
    background-color: qlineargradient(
        spread:pad, x1:0, y1:0.511364, x2:1, y2:0.523,
        stop:0 rgba(38, 87, 135, 255),
        stop:1 rgba(232, 125, 13, 255));
}
QListWidget {
    background-color: rgb(255, 255, 255);
    color: rgb(25, 25, 25);
    border-radius: 6px;
    padding: 2px;
    font-size: 12px;
}
''')


############################################################################

if DEV_MODE:
    preset.set_blender("H:/Blender Foundation/blender-4.3.0/blender.exe")
    preset.add_projects("I:/Blender Library/00_Parts/00_Intro/00_Inside/001_Butterflies.blend",
                        "I:/Blender Library/00_Parts/00_Intro/00_Inside/002_GuitarTuning.blend")
    mw.update()


############################################################################
# Run

mw.show()
exit(app.exec_())