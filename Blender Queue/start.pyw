################################################################################
## Main

import os
import json
import psutil
import PyQt5.QtWidgets as qtw
import PyQt5.QtGui as qtg
import PyQt5.QtCore as qtc
from PyQt5.QtCore import Qt
import subprocess
import threading
import time
import ctypes

from os.path import normpath, join
from pathlib import Path
from utils import monitor, audio
from utils.navigation import open_folder

from project import BlendProject, BlendProjectWindow
from render import RenderWorker
from config import *
import store

################################################################################

DEV_MODE = True
store.working_dir = normpath(os.getcwd())

################################################################################


class QueuePreset():

    def __init__(self):
        self.blender_exe = None
        self.project_list = []
        self.process = None

        self.blender_status = 'READY_TO_RENDER'
        self.is_adding_projects = False
        self.is_shutting_down = False

        self.init_render_variables()


    def init_render_variables(self, gui=False):
        self.global_render_start_time = time.time()
        self.render_start_time = time.time()
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


    def set_status(self, value):
        if value not in ['READY_TO_RENDER', 'RENDERING', 'RENDERING_STOPPING', 'RENDERING_FINISHED']:
            raise Exception(f'Unknown status "{value}".')
        self.blender_status = value
        log(f'Status: {self.blender_status}', developer=True)


    def is_status(self, *values):
        for value in values:
            if value not in ['READY_TO_RENDER', 'RENDERING', 'RENDERING_STOPPING', 'RENDERING_FINISHED']:
                raise Exception(f'Unknown status "{value}".')
        return self.blender_status in values


    def locate_blender(self):
        filename, _ = qtw.QFileDialog.getOpenFileName(mw, 'Single File', "H:/Blender Foundation/blender-4.1.1", 'blender.exe')
        if not filename: return
        self.blender_exe = filename
        mw.w_pathToBlender.setText(filename)
        log(f'Blender: {filename}')


    def add_projects(self, *files):
        """
        Add projects in background.
        """
        if not self.blender_exe:
            log("Locate blender.exe first!")
            return

        if self.is_adding_projects:
            return

        t = threading.Thread(target=self.__add_projects, args=tuple(files))
        t.start()


    def __add_projects(self, *files):

        os.makedirs(normpath(join(store.working_dir, "blender/temp")), exist_ok=True)
        CACHE_FILE = normpath(join(store.working_dir, "blender/cache.json"))
        DATA_FILE = normpath(join(store.working_dir, "blender/temp/data.json"))
        GET_DATA_PY = normpath(join(store.working_dir, "blender/get_data.py"))

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

        files = [ normpath(file) for file in files if file.endswith(".blend")]
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
                log(f'({i + 1}/{len(files)}) Loading project cache: {file}')

            # Get project data
            else:
                BATCH_FILE = normpath(join(store.working_dir, f'blender/temp/get_data.bat'))
                BATCH = f"""
@CHCP 65001 > NUL
blender "{file}" --factory-startup --background  --python "{GET_DATA_PY}" "{DATA_FILE}"
""".strip()

                with open(BATCH_FILE, 'w') as f:
                    f.write(BATCH)

                log(f'({i + 1}/{len(files)}) Loading project: {file}')

                process = subprocess.Popen([BATCH_FILE],
                                        # stderr=subprocess.STDOUT,
                                        # stdout=subprocess.PIPE,
                                        # stdin=subprocess.PIPE,
                                        #    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP, #DETACHED_PROCESS
                                        #    creationflags=subprocess.DETACHED_PROCESS, #DETACHED_PROCESS
                                        #    preexec_fn=os.setsid,
                                        cwd=normpath(Path(self.blender_exe).parent),
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

        if amount: log(f'All projects loaded!')
        self.is_adding_projects = False
        mw.update()


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
        if self.is_status('RENDERING_STOPPING') or not self.process:
            return

        self.set_status('RENDERING_STOPPING')
        log("Stopping rendering...")

        for proc in psutil.Process(self.process.pid).children(recursive=True):
            proc.terminate()

        self.process.terminate()
        self.process = None


    def shutdown(self, delay=15.0):
        """
        Show countdown and shotdown PC.
        """
        if mw.w_onComplete.currentText() != 'SHUTDOWN':
            return
        t = threading.Thread(target=self.__shutdown, args=(delay,))
        t.start()


    def __shutdown(self, delay):
        self.is_shutting_down = True
        mw.update()

        for i in range(int(delay)):
            d = delay - i
            log(f'Shutting down in {d:.0f} {"seconds" if d > 1 else "second"}.')
            mw.update()
            time.sleep(1)

            if not self.is_shutting_down:
                log("Shutting down was cancelled.")
                return

        log("Shutting down...")
        if not DEV_MODE: os.system('shutdown -s')
        mw.update()
        monitor.screen_on()


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

        self.setWindowTitle(TITLE)
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

            # [button] Locate Blender
            w_locateBlender = qtw.QPushButton("Locate", clicked=lambda: preset.locate_blender())
            w_locateBlender.clicked.connect(lambda: self.update())
            w_locateBlender.setFixedWidth(100)
            w_hBoxLayout.addWidget(w_locateBlender)

            # [edit] Path to Blender
            self.w_pathToBlender = w_pathToBlender = qtw.QLineEdit("Locate blender.exe first!")
            w_pathToBlender.setEnabled(False)
            w_hBoxLayout.addWidget(w_pathToBlender)

            # [button] Locate Blender
            self.w_openFolder = w_openFolder = qtw.QPushButton("Open Folder", clicked=lambda: open_folder(preset.blender_exe))
            w_openFolder.setFixedWidth(100)
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
        self.w_gProgress = w_gProgress = qtw.QLabel()
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
        self.w_pProgress = w_pProgress = qtw.QLabel()
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

        w_vBoxLayout.addSpacing(20)

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
        w_hBoxLayoutOnComplete.addWidget(w_cancelShutdown, 2, Qt.AlignLeft)

        # ! [hbox] Start & Stop
        w_hBoxLayoutRender = qtw.QHBoxLayout()
        w_hBoxLayout.addLayout(w_hBoxLayoutRender)

        # [button] Start Render
        self.w_startRender = w_startRender = qtw.QPushButton("Render", clicked=lambda: preset.start_render())
        w_startRender.setFixedWidth(100)
        w_startRender.setFixedHeight(40)
        w_hBoxLayoutRender.addWidget(w_startRender)

        # [button] Stop Render
        self.w_stopRender = w_stopRender = qtw.QPushButton("Stop", clicked=lambda: preset.stop_render())
        w_stopRender.setFixedWidth(100)
        w_stopRender.setFixedHeight(40)
        w_hBoxLayoutRender.addWidget(w_stopRender, 1, Qt.AlignLeft)

        w_hBoxLayout.addSpacing(150)

        # [button] Screens Off
        w_screensOff = qtw.QPushButton("Screens Off", clicked=lambda: monitor.screen_off())
        w_screensOff.setFixedWidth(100)
        w_screensOff.setFixedHeight(40)
        w_hBoxLayout.addWidget(w_screensOff, 0, Qt.AlignRight)

        self.show()


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

        self.w_gProgress.setText(f'0/{global_frames}' if global_frames else "Global:")
        self.w_pProgress.setText(f'0/{project_frames}' if project_frames else "Project:")

        self.w_gProgressBar.setValue(0)
        self.w_pProgressBar.setValue(0)
        self.w_rProgressBar.setValue(0)


    def update(self):
        self.w_openFolder.setEnabled(bool(preset.blender_exe))
        self.w_startRender.setEnabled(bool(preset.blender_exe and not preset.is_status('RENDERING') and preset.project_list))
        self.w_stopRender.setEnabled(preset.is_status('RENDERING') and not preset.is_status('RENDERING_STOPPING'))
        self.w_listOfProjects.setEnabled(bool(not preset.is_adding_projects and not preset.is_status('RENDERING')))
        self.w_cancelShutdown.setEnabled(bool(preset.is_shutting_down))


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
    mw.set_log_text(line)
    print(line)

################################################################################
# App

ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APPID)
store.app = app = qtw.QApplication([])
store.mw = mw = MainWindow()
store.preset = preset = QueuePreset()

################################################################################
# Style

app.setStyleSheet('''
QLabel {
    font-size: 12px;
}
QPushButton {
    font-size: 12px;
}
QProgressBar {
    background-color: rgb(200, 200, 200);
    color: rgb(255, 255, 255);
    border-style: none;
    border-radius: 4px;
    text-align: center;
    font-size: 14px;
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
    font-size: 15px;
}
''')

################################################################################

if DEV_MODE:
    mw.blender_exe = "H:/Blender Foundation/blender-4.1.1/blender.exe"
    preset.add_projects("I:/Blender Library/kQueue test 1.blend",
                        "I:/Blender Library/00_Parts/00_Intro/03_HomeRoaming/fire.blend")
    mw.update()

################################################################################
# Setup icons

app_icon = qtg.QIcon()

for size in [16, 24, 32, 48, 64, 128, 256]:
    path, suffix = ICON.rsplit(".", 1)
    icon_filename = join(store.working_dir, ICON)
    filename = normpath(join(store.working_dir, f'{path}_{size}x{size}.{suffix}'))

    if DEV_MODE:
        from PIL import Image
        with Image.open(icon_filename) as img:
            img.thumbnail((size, size), resample=Image.Resampling.LANCZOS)
            icc_profile = img.info.get('icc_profile', '')

            img.save(filename,
                    format='png',
                    quality=100,
                    compression='PNG',
                    icc_profile=icc_profile)

        print(f'Image created: {filename}')

    app_icon.addFile(filename, qtc.QSize(size, size))

app.setWindowIcon(app_icon)

################################################################################
# Run

app.exec_()