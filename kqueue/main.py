################################################################################
## Main

import ctypes
import subprocess

import PyQt5.QtWidgets as qtw
import PyQt5.QtGui as qtg
import PyQt5.QtCore as qtc
import PyQt5.QtSvg as qts
from PyQt5.QtCore import Qt

from os import getcwd, makedirs
from sys import exit
from time import time, sleep
from pathlib import Path
from psutil import Process
from threading import Thread

from .utils import monitor
from .utils.path import join, open_folder, open_image
from .project.widgets import QBlendProject, QBlendProjectSettings

from .render import RenderThread
from .loader import LoaderThread
from .config import *
from . import store

from .widgets.QPushButton import QPushButton

if hasattr(Qt, 'AA_EnableHighDpiScaling'):
    qtw.QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)

if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
    qtw.QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

################################################################################

# Init path variables
store.working_dir = join(getcwd() + "/kqueue")
store.cache_file = Path(join(getcwd(), CACHE_FILE))
store.bridge_file = Path(join(getcwd(), BRIDGE_FILE))
store.get_data_py = Path(join(getcwd(), GET_DATA_PY))
store.get_data_bat = Path(join(getcwd(), GET_DATA_BAT))
store.temp_folder = Path(join(getcwd(), TEMP_FOLDER))

print(store.get_data_bat, store.get_data_bat.exists())


################################################################################

# class GlobalPreset():

#     def __init__(self):

#         # Filename of the current preset.
#         self.filename = None

#         # Path to Blender executable.
#         self.blender_exe = None


class QueuePreset():

    def __init__(self):

        # Filename of this preset.
        self.filename = None

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

        # Render by markers?
        self.marker_render = False

        self.init_render_variables()


    def get_global_frames_number(self):
        """
        Get total frames number.
        """
        return sum([ len(p.get_frames_list()) for p in self.project_list if p.active ])


    def set_need_save(self, value=True):
        """
        Does the project need saving?
        """

        if value == self.save_needed:
            return

        self.save_needed = value
        mw.update_title.emit()


    def init_render_variables(self, gui=False):
        """
        Initialize or reset render variables for GUI.

        `gui` - update interface?
        """

        self.global_render_start_time = time()
        self.render_start_time = time()
        self.render_avg_time = []
        self.global_frames = sum([ len(p.get_frames_list()) for p in self.project_list if p.active ])
        self.global_frame = 0
        self.project_frames = 0
        self.project_frame = 0
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

        if not Path(filename).exists():
            self.blender_exe = None
            mw.w_pathToBlender.setText("Locate blender.exe first!")
            mw.w_pathToBlender.setStyleSheet("color: red")
            return

        mw.w_pathToBlender.setStyleSheet("")

        if filename == self.blender_exe:
            return

        self.blender_exe = filename
        mw.w_pathToBlender.setText(filename)

        log(f'Blender: {filename}')
        self.set_need_save()


    def save(self):
        """
        """

        filename = self.filename

        if not filename:
            return

        from .save_load import save_file
        save_file([self.project_list, self.blender_exe], filename, version=1)

        self.set_save(filename)
        self.set_need_save(False)

        log(f'Saved: {filename}')


    def save_as(self):
        """
        Save project state as a file.
        """

        if self.filename and False:
            path = self.filename
        else:
            path = join(store.working_dir, SAVE_FOLDER)
            makedirs(path, exist_ok=True)

        filename, _ = qtw.QFileDialog.getSaveFileName(mw, 'Save', path, "kQueue Project (*.kqp)")

        if not filename:
            return

        from .save_load import save_file
        save_file([self.project_list, self.blender_exe], filename, version=1)

        self.set_save(filename)
        self.set_need_save(False)

        log(f'Saved: {filename}')


    def load_from(self, filename=None):
        """
        Load save from...
        """

        if filename is None:

            if self.filename and False:
                path = self.filename
            else:
                path = join(store.working_dir, SAVE_FOLDER)
                makedirs(path, exist_ok=True)

            filename, _ = qtw.QFileDialog.getOpenFileName(mw, 'Load', path, "kQueue Project (*.kqp)")

            if not filename:
                return

        from .save_load import load_file
        version, data = load_file(filename)

        if not data:
            return

        if version == 1:
            self.project_list, blender_exe = data
            self.set_blender(blender_exe)

        self.set_save(filename)
        self.set_need_save(False)

        mw.update_list.emit(False)
        mw.update_widgets.emit()

        log(f'Loaded: {filename}')


    def set_save(self, filename):
        """
        Set currently loaded save.
        """

        if not filename or not Path(filename).exists():
            return

        self.filename = filename
        mw.update_title.emit()


    def add_projects(self, *files):
        """
        Add projects in background.
        """

        if not self.blender_exe:
            log("Locate blender.exe first!")
            return

        if self.is_adding_projects:
            return

        self.loader_thread = LoaderThread(*files)
        self.loader_thread.start()


    def reload_projects(self):
        """
        Reload outdated projects.
        """

        files = []

        for project in self.project_list:

            if not project.is_outdated():
                continue

            files.append(project.file)

        self.add_projects(*files)


    def get_outdated_projects(self):
        """
        """

        rv = []

        for project in self.project_list:

            if not project.is_outdated():
                continue

            rv.append(project)

        return rv


    def has_outdated_projects(self):
        """ """

        return bool(self.get_outdated_projects())


    def periodic(self):
        """
        """

        if self.is_status('RENDERING', 'RENDERING_STOPPING'):
            return

        mw.update_widgets.emit()


    def start_render(self):
        """
        Start rendering process.
        """

        if not self.is_status('READY_TO_RENDER') or not preset.project_list:
            return

        self.init_render_variables(gui=True)

        self.render_thread = RenderThread() #qtc.QThread()
        # self.render_worker = RenderThread()
        # self.render_worker.moveToThread(self.render_thread)

        # self.render_thread.started.connect(self.render_worker.run)
        self.render_thread.finished.connect(self.render_thread.deleteLater)

        # self.render_worker.finished.connect(self.render_thread.quit)
        # self.render_worker.finished.connect(self.render_worker.deleteLater)

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
            mw.update_widgets.emit()
            monitor.screen_on()

            for i in range(int(delay)):
                d = delay - i
                log(f'Shutting down in {d:.0f} {"seconds" if d > 1 else "second"}.')
                mw.update_widgets.emit()
                sleep(1)

                if not self.is_shutting_down:
                    log("Shutting down was cancelled.")
                    return

            log("Shutting down...")

            if not DEV_MODE:
                subprocess.call(["shutdown", "-s", "-t", "15"])

            mw.update_widgets.emit()

        t = Thread(target=do_shutdown, args=(delay,))
        t.start()


    def cancel_shutdown(self):
        """
        Cancel shutting down process.
        """

        self.is_shutting_down = False
        mw.update_widgets.emit()


################################################################################
## Main Window

class QSvgWidget(qts.QSvgWidget):
    """
    Custom widget to track current file.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_filename = None

    def setImage(self, filename):

        if filename == self.current_filename:
            return

        self.current_filename = filename
        self.load(filename)


class QListWidget(qtw.QListWidget):
    """
    Custom List Widget that fixed disappearing items.
    https://stackoverflow.com/questions/74263946/widget-inside-qlistwidgetitem-disappears-after-internal-move
    """

    def dragMoveEvent(self, event):

        if ((target := self.row(self.itemAt(event.pos()))) ==
            (current := self.currentRow()) + 1 or
            (current == self.count() - 1 and target == -1)):
            event.ignore()

        else:
            super().dragMoveEvent(event)


def set_window_titlebar_dark(window):
    """
    Set dark Windows title bar.
    """

    try:
        hwnd = window.winId().__int__()
        DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        DWMWA_USE_IMMERSIVE_DARK_MODE_BEFORE_20H1 = 19

        value = ctypes.c_int(2)
        result = ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_USE_IMMERSIVE_DARK_MODE,
            ctypes.byref(value),
            ctypes.sizeof(value)
        )

        if result != 0:
            value = ctypes.c_int(1)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd,
                DWMWA_USE_IMMERSIVE_DARK_MODE_BEFORE_20H1,
                ctypes.byref(value),
                ctypes.sizeof(value)
            )

    except Exception as e:
        pass


class MainWindow(qtw.QMainWindow):
    update_title = qtc.pyqtSignal()
    update_list = qtc.pyqtSignal(bool)
    update_widgets = qtc.pyqtSignal()
    log = qtc.pyqtSignal(str)

    def __init__(self):
        super().__init__()

        set_window_titlebar_dark(self)

        self.setWindowIcon(qtg.QIcon(ICON))

        self.setMinimumWidth(900)
        self.setMinimumHeight(600)
        self.setAcceptDrops(True)
        self.setAttribute(Qt.WA_DeleteOnClose)

        # [widget]
        w = qtw.QWidget()
        self.setCentralWidget(w)

        # [vbox]
        w_vBoxLayout = qtw.QVBoxLayout()
        w.setLayout(w_vBoxLayout)

        if True:

            # [hbox]
            w_hBoxLayout = qtw.QHBoxLayout()
            w_vBoxLayout.addLayout(w_hBoxLayout)

            # [button] Locate Save
            self.w_locateSave = w_locateSave = QPushButton("", clicked=lambda: preset.save_as())
            w_locateSave.clicked.connect(lambda: self.update_widgets.emit())
            w_locateSave.setIcon(qtg.QIcon('kqueue/icons/save.svg'))
            w_locateSave.setFixedHeight(26)
            w_locateSave.setToolTip("Save the current file in the desired location.")
            w_locateSave.setShortcut(qtg.QKeySequence("Ctrl+Shift+S"))
            w_hBoxLayout.addWidget(w_locateSave)

            # [shortcut] Save
            qtw.QShortcut('Ctrl+S', self).activated.connect(lambda: preset.save())

            # [button] Load
            self.w_locateLoad = w_locateLoad = QPushButton("", clicked=lambda: preset.load_from())
            w_locateLoad.clicked.connect(lambda: self.update_widgets.emit())
            w_locateLoad.setIcon(qtg.QIcon('kqueue/icons/folder.svg'))
            w_locateLoad.setFixedHeight(26)
            w_locateLoad.setToolTip("Open a kQueue file.")
            w_hBoxLayout.addWidget(w_locateLoad)

            # [edit] Path to Blender
            self.w_pathToBlender = w_pathToBlender = qtw.QLineEdit("Locate blender.exe first!")
            w_pathToBlender.setEnabled(False)
            w_pathToBlender.setFixedHeight(26)
            w_hBoxLayout.addWidget(w_pathToBlender)

            # [button] Locate Blender
            self.w_locateBlender = w_locateBlender = QPushButton("", clicked=lambda: preset.locate_blender())
            w_locateBlender.clicked.connect(lambda: self.update_widgets.emit())
            w_locateBlender.setIcon(qtg.QIcon('kqueue/icons/blender.svg'))
            w_locateBlender.setIconSize(qtc.QSize(18, 18))
            w_locateBlender.setToolTip("Locate a Blender executable.")
            w_locateBlender.setFixedHeight(26)
            w_hBoxLayout.addWidget(w_locateBlender)

        # [list] List of Projects
        def open_project_settings():
            self.sw = QBlendProjectSettings(self.get_selected_project())
            self.sw.show()

        self.w_listOfProjects = w_listOfProjects = QListWidget()
        w_listOfProjects.itemDoubleClicked.connect(open_project_settings)
        w_listOfProjects.setDragDropMode(qtw.QAbstractItemView.InternalMove)
        w_listOfProjects.model().rowsMoved.connect(lambda: self.update_list.emit(True))
        w_vBoxLayout.addWidget(w_listOfProjects)

        # [hbox]
        w_hBoxLayout = qtw.QHBoxLayout()
        w_vBoxLayout.addLayout(w_hBoxLayout)

        # [check] Global active
        self.w_global_active = qtw.QCheckBox("All")
        w_hBoxLayout.addWidget(self.w_global_active)

        def toggle_global_active():
            active = self.w_global_active.isChecked()
            changed = False

            for project in preset.project_list:

                if active == project.active:
                    continue

                project.active = active
                changed = True

            if not changed:
                return

            store.mw.update_list.emit(False)
            store.mw.update_widgets.emit()
            store.preset.set_need_save()

        self.w_global_active.clicked.connect(toggle_global_active)
        self.w_global_active.setStyleSheet("""
            QCheckBox::indicator {
                width: 12;
                height: 12;
            }
        """)

        l_form = qtw.QFormLayout()
        w_hBoxLayout.addLayout(l_form)

        # [button] Set Sample Globally
        def toggle_global_active(samples):

            def func():
                changed = False

                for project in store.preset.project_list:

                    if samples == project.samples_override:
                        continue

                    project.samples_override = samples
                    changed = True

                if not changed:
                    return

                store.mw.update_list.emit(False)
                store.mw.update_widgets.emit()
                store.preset.set_need_save()

                return

            return func

        self.w_setGlobalSamples_list = []

        for sample in [ 32, 64, 128, 256, 512, 1024, 2048, 4096 ]:
            w_setGlobalSamples = QPushButton(f'{sample}', clicked=toggle_global_active(sample))
            w_setGlobalSamples.setFixedWidth(48)
            w_setGlobalSamples.setToolTip(f'Set {sample} samples globally.')
            w_hBoxLayout.addWidget(w_setGlobalSamples)

            self.w_setGlobalSamples_list.append(w_setGlobalSamples)

        # [button] Reload
        self.w_global_reload = QPushButton("", clicked=lambda: preset.reload_projects())
        self.w_global_reload.setIcon(qtg.QIcon('kqueue/icons/reload_project.svg'))
        self.w_global_reload.setToolTip("Reload all the projects.")
        self.w_global_reload.setFixedWidth(24)
        w_hBoxLayout.addWidget(self.w_global_reload)

        # # [label] Global Settings
        # w_globalSettings = qtw.QLabel("Global Settings:")
        # w_vBoxLayout.addWidget(w_globalSettings)

        # # [form] Preset Override
        # l_presetOverride = qtw.QFormLayout()
        # w_vBoxLayout.addLayout(l_presetOverride)

        # # [edit] Samples
        # w_presetSamples = qtw.QLineEdit()
        # l_presetOverride.addRow("Samples", w_presetSamples)

        # [hbox]
        w_hBoxLayout = qtw.QHBoxLayout()
        w_vBoxLayout.addLayout(w_hBoxLayout)

        if True:

            # [label] Status
            self.w_logStatus = QSvgWidget("kqueue/icons/status_loading.svg")
            self.w_logStatus.setFixedSize(16, 16)
            w_hBoxLayout.addWidget(self.w_logStatus)

            # [label] Output
            self.w_logOutput = qtw.QLabel("...")
            self.w_logOutput.setFixedHeight(40)
            self.w_logOutput.setEnabled(False)
            w_hBoxLayout.addWidget(self.w_logOutput)


        # [hbox]
        w_hBoxLayout = qtw.QHBoxLayout()
        w_vBoxLayout.addLayout(w_hBoxLayout)

        if True:

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

            # [hbox] Project Progress
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


            # [hbox] Render Progress
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


        # [check] Preview Render
        self.w_preview_render = w_preview_render = qtw.QCheckBox("Preview Render")
        w_vBoxLayout.addWidget(w_preview_render)

        def toggle_preview_render():
            preset.preview_render = w_preview_render.isChecked()
            self.update_list.emit(False)

        w_preview_render.clicked.connect(lambda: toggle_preview_render())

        # [check] Selective Render
        self.w_selective = w_selective = qtw.QCheckBox("Selective Render")
        w_vBoxLayout.addWidget(w_selective)

        def toggle_selective():
            preset.selective_render = w_selective.isChecked()
            self.update_list.emit(False)
            self.update_widgets.emit()

        w_selective.clicked.connect(lambda: toggle_selective())

        # [check] Marker Render
        self.w_marker_render = w_marker_render = qtw.QCheckBox("Marker Render")
        w_vBoxLayout.addWidget(w_marker_render)

        def toggle_marker_render():
            preset.marker_render = w_marker_render.isChecked()
            self.update_list.emit(False)

        w_marker_render.clicked.connect(lambda: toggle_marker_render())

        # [check] Assign sRGB
        # self.w_assign_srgb = w_assign_srgb = qtw.QCheckBox("Save as sRGB")
        # w_vBoxLayout.addWidget(w_assign_srgb)

        # def toggle_assign_srgb():
        #     preset.assign_srgb = w_assign_srgb.isChecked()
        #     self.update_list.emit(False)

        # w_assign_srgb.clicked.connect(lambda: toggle_assign_srgb())


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
        # w_shutdown = QPushButton("Shutdown", clicked=lambda: preset.shutdown())
        # w_hBoxLayoutOnComplete.addWidget(w_shutdown)

        # [button] Cancel Shutdown
        self.w_cancelShutdown = w_cancelShutdown = QPushButton("Cancel", clicked=lambda: preset.cancel_shutdown())
        w_cancelShutdown.setFixedHeight(25)
        w_cancelShutdown.setEnabled(False)
        w_hBoxLayoutOnComplete.addWidget(w_cancelShutdown, 2, Qt.AlignLeft)

        # ! [hbox] Start & Stop
        w_hBoxLayoutRender = qtw.QHBoxLayout()
        w_hBoxLayout.addLayout(w_hBoxLayoutRender)

        # [button] Start Render
        self.w_startRender = w_startRender = QPushButton("", clicked=lambda: preset.start_render())
        w_startRender.setIcon(qtg.QIcon('kqueue/icons/play.svg'))
        w_startRender.setToolTip("Start rendering.")
        w_startRender.setFixedWidth(100)
        w_startRender.setFixedHeight(40)
        w_startRender.setEnabled(False)
        w_hBoxLayoutRender.addWidget(w_startRender)

        # [button] Stop Render
        self.w_stopRender = w_stopRender = QPushButton("", clicked=lambda: preset.stop_render())
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

        self.w_openRender = w_openRender = QPushButton("", clicked=lambda: open_render())
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

        self.w_openRenderFolder = w_openRenderFolder = QPushButton("", clicked=lambda: open_render_folder())
        w_openRenderFolder.setIcon(qtg.QIcon('kqueue/icons/folder.svg'))
        w_openRenderFolder.setToolTip("Open last saved render folder.")
        w_openRenderFolder.setFixedWidth(40)
        w_openRenderFolder.setFixedHeight(40)
        w_hBoxLayout.addWidget(w_openRenderFolder)

        # [button] Screens Off
        w_screensOff = QPushButton("", clicked=lambda: monitor.screen_off(delay=1.0))
        w_screensOff.setIcon(qtg.QIcon('kqueue/icons/screen_off.svg'))
        w_screensOff.setToolTip("Turn off the screens.")
        w_screensOff.setFixedWidth(40)
        w_screensOff.setFixedHeight(40)
        w_hBoxLayout.addWidget(w_screensOff)

        # Signals
        self.update_widgets.connect(self.__update_widgets)
        self.update_list.connect(self.__update_list)
        self.update_title.connect(self.__update_title)
        self.log.connect(self.__log)

        self.update_title.emit()


    def dragEnterEvent(self, event):
        """
        Handle drag and drop .blend files.
        """

        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()


    def keyPressEvent(self, event):
        """
        Handle key presses.
        """

        if preset.is_status('RENDERING') or preset.is_status('RENDERING_STOPPING'):
            return

        # Delete
        if event.key() == Qt.Key_Delete:

            if preset.project_list:
                project = self.get_selected_project()
                preset.project_list.remove(project)

                self.update_list.emit(False)
                self.update_widgets.emit()
                preset.set_need_save()


    def get_selected_project(self):
        """
        Get selected project.
        """

        item = self.w_listOfProjects.currentItem()
        w_project = self.w_listOfProjects.itemWidget(item)
        return w_project.project if w_project else None


    def dropEvent(self, event):
        """
        Load projects on drag and drop.
        """

        files = [ url.toLocalFile() for url in event.mimeData().urls() ]
        preset.add_projects(*files)


    def closeEvent(self, event):
        """
        Close [x] event.
        """

        if DEV_MODE:
            event.ignore()
            preset.stop_render()
            event.accept()

        else:
            result = qtw.QMessageBox.question(self,
                        "Confirm Exit",
                        "Are you sure you want to exit?",
                        qtw.QMessageBox.Yes| qtw.QMessageBox.No)
            event.ignore()

            if result == qtw.QMessageBox.Yes:
                preset.stop_render()
                event.accept()


    ############################################################################
    # Emitters

    def __update_title(self):
        """
        Update title.
        """

        title = TITLE if not DEV_MODE else APPID
        title += " " + ".".join([str(v) for v in VERSION])

        if store.preset and store.preset.filename:
            filename = store.preset.filename
            save_needed = store.preset.save_needed

            fn = filename.rsplit("/", 1)[-1].rsplit(".", 1)[0]
            title = f'{fn} [{filename}] - {title}'

            if save_needed:
                title = "* " + title

        else:
            title = f'(Unsaved) - {title}'

        self.setWindowTitle(title)


    def __update_list(self, sync=False):
        """
        Update list widget and `preset.project_list` list.
        """

        old_value = self.w_listOfProjects.verticalScrollBar().value()
        old_files = [ p.file for p in preset.project_list ]

        # Sync variable with the list widget
        if sync:
            project_list = []

            for i in range(self.w_listOfProjects.count()):
                item = self.w_listOfProjects.item(i)
                w_project = self.w_listOfProjects.itemWidget(item)
                project_list.append(w_project.project)

            preset.project_list = project_list

        # Add items to the list widget
        self.w_listOfProjects.clear()
        global_active = True

        for project in preset.project_list:
            w_project = QBlendProject(project=project)

            w_project.set_filename(project.file)
            w_project.set_active(project.active)
            w_project.set_frames(project.get_frames())
            w_project.set_samples(project.get_samples())
            # w_project.set_camera(project.camera)
            w_project.set_render_filepath(project.get_render_filepath())
            w_project.update_widgets()

            item = qtw.QListWidgetItem(self.w_listOfProjects)
            item.setSizeHint(w_project.sizeHint())

            self.w_listOfProjects.addItem(item)
            self.w_listOfProjects.setItemWidget(item, w_project)

            if not project.active:
                global_active = False

        # Set global active
        self.w_global_active.setChecked(global_active)

        # Calculate frames
        project_frames = None

        for project in preset.project_list:

            if not project.active:
                continue

            frames = len(project.get_frames_list())

            if project_frames is None:
                project_frames = frames

        global_frames = preset.get_global_frames_number()
        self.w_gProgress.setText(f'0/{global_frames or 0}' if global_frames or preset.project_list else "Global:")
        self.w_pProgress.setText(f'0/{project_frames or 0}' if project_frames or preset.project_list else "Project:")

        self.w_gProgressBar.setValue(0)
        self.w_pProgressBar.setValue(0)
        self.w_rProgressBar.setValue(0)

        # If list changed
        new_files = [ p.file for p in preset.project_list ]

        if old_files != new_files:
            preset.set_need_save()

        max_cycles = 1000

        while self.w_listOfProjects.verticalScrollBar().value() != old_value and max_cycles > 0:
            self.w_listOfProjects.verticalScrollBar().setValue(old_value)

            max_cycles -= 1


    def __update_widgets(self):

        if preset.is_status('RENDERING') or preset.is_status('RENDERING_STOPPING'):
            self.w_locateSave.setEnabled(False)
            self.w_locateLoad.setEnabled(False)
            self.w_locateBlender.setEnabled(False)
            self.w_selective.setEnabled(False)
            # self.w_assign_srgb.setEnabled(False)
            self.w_preview_render.setEnabled(False)
            self.w_marker_render.setEnabled(False)
            self.w_global_reload.setEnabled(False)

            self.w_logStatus.setImage("kqueue/icons/status_loading.svg")
            self.w_global_active.setEnabled(False)

            for widget in self.w_setGlobalSamples_list:
                widget.setEnabled(False)

        else:
            self.w_locateSave.setEnabled(True)
            self.w_locateLoad.setEnabled(True)
            self.w_locateBlender.setEnabled(True)
            self.w_selective.setEnabled(True)
            # self.w_assign_srgb.setEnabled(True)
            self.w_preview_render.setEnabled(True)
            self.w_marker_render.setEnabled(True)
            self.w_global_reload.setEnabled(preset.has_outdated_projects())

            if preset.is_adding_projects:
                self.w_logStatus.setImage("kqueue/icons/status_loading.svg")
            else:
                self.w_logStatus.setImage("kqueue/icons/status_idle.svg")

            self.w_global_active.setEnabled(True)

            for widget in self.w_setGlobalSamples_list:
                widget.setEnabled(bool(preset.project_list))

        self.w_startRender.setEnabled(bool(preset.blender_exe and not preset.is_status('RENDERING') and preset.project_list and preset.get_global_frames_number()))
        self.w_stopRender.setEnabled(preset.is_status('RENDERING') and not preset.is_status('RENDERING_STOPPING'))
        self.w_listOfProjects.setEnabled(bool(not preset.is_adding_projects and not preset.is_status('RENDERING')))
        self.w_cancelShutdown.setEnabled(bool(preset.is_shutting_down))
        self.w_openRender.setEnabled(bool(preset.renders_list))
        self.w_openRenderFolder.setEnabled(bool(preset.renders_list))

        self.w_selective.setChecked(bool(preset.selective_render))
        # self.w_assign_srgb.setChecked(bool(preset.assign_srgb))
        self.w_preview_render.setChecked(bool(preset.preview_render))

        for i in range(self.w_listOfProjects.count()):
            item = self.w_listOfProjects.item(i)
            w_project = self.w_listOfProjects.itemWidget(item)
            w_project.update_widgets()


    def __log(self, text):
        self.w_logOutput.setText(text)


################################################################################

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
        mw.log.emit(line)

    print(line)


################################################################################

ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APPID)
store.app = app = qtw.QApplication([])
store.mw = mw = MainWindow()
store.preset = preset = QueuePreset()
mw.update_widgets.emit()
# app.setStyle("fusion")


app.setStyleSheet('''
* {
    font-family: Segoe UI, Arial, sans-serif;
}

QLabel {
    font-size: 10px;
    color: #e0e0e0;
}

QLabel:disabled {
    font-size: 10px;
    color: #707070;
}

QPushButton {
    font-size: 11px;
    background-color: #3a3a3a;
    color: #e0e0e0;
    border: 1px solid #555555;
    border-radius: 4px;
    padding: 4px 8px;
}

QPushButton:hover {
    background-color: #4a4a4a;
    border: 1px solid #666666;
}

QPushButton:pressed {
    background-color: #2a2a2a;
}

QPushButton:disabled {
    background-color: #2a2a2a;
    color: #707070;
    border: 1px solid #404040;
}

QLineEdit {
    font-size: 10px;
    background-color: #2d2d2d;
    color: #e0e0e0;
    border: 1px solid #555555;
    border-radius: 4px;
    padding: 2px;
    selection-background-color: #448fff;
}

QLineEdit:focus {
    border: 1px solid #448fff;
}

QLineEdit:disabled {
    background-color: #252525;
    color: #707070;
    border: 1px solid #404040;
}

QComboBox {
    font-size: 11px;
    background-color: #3a3a3a;
    color: #e0e0e0;
    border: 1px solid #555555;
    border-radius: 4px;
    padding: 5px;
    min-height: 10px;
}

QComboBox::drop-down {
    border: none;
    width: 20px;
}

QComboBox::down-arrow {
    image: url(down_arrow.svg);
    width: 12px;
    height: 12px;
}

QComboBox QAbstractItemView {
    background-color: #3a3a3a;
    color: #e0e0e0;
    border: 1px solid #555555;
    border-radius: 4px;
    selection-background-color: #448fff;
    selection-color: #ffffff;
    font-size: 11px;
}

QComboBox:disabled {
    background-color: #2a2a2a;
    color: #707070;
    border: 1px solid #404040;
}

QListWidget {
    color: #e0e0e0;
    border-radius: 6px;
    padding: 2px;
    font-size: 12px;
    border: 1px solid #555555;
    outline: none;
}

QListWidget::item {
    padding: 4px;
    border: 1px solid transparent;
    border-radius: 4px;
    margin: 0px;
}

QListWidget::item:hover {
    border: 1px solid #666666;
    outline: none;
}

QListWidget::item:selected {
    color: #ffffff;
    border: 2px solid #448fff;
    outline: none;
}

QListWidget::item:selected:active {
    color: #1e1e1e;
    background-color: #1e1e1e;
    border: 2px solid #3377dd;
    outline: none;
}

QScrollBar:vertical {
    background-color: transparent;
    width: 14px;
    border: none;
    margin: 0px;
    padding: 2px;
}

QScrollBar::handle:vertical {
    background-color: rgba(85, 85, 85, 120);
    border-radius: 5px;
    min-height: 20px;
    margin: 0px 0px;
}

QScrollBar::handle:vertical:hover {
    background-color: rgba(102, 102, 102, 180);
}

QScrollBar:vertical:hover {
    background-color: rgba(45, 45, 45, 30);
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    border: none;
    background: transparent;
    height: 0px;
}

QScrollBar::up-arrow:vertical,
QScrollBar::down-arrow:vertical,
QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {
    background: transparent;
    border: none;
}

QScrollBar:horizontal {
    background-color: transparent;
    height: 14px;
    border: none;
    margin: 0px;
    padding: 2px;
}

QScrollBar::handle:horizontal {
    background-color: rgba(85, 85, 85, 120);
    border-radius: 5px;
    min-width: 20px;
    margin: 0px 0px;
}

QScrollBar::handle:horizontal:hover {
    background-color: rgba(102, 102, 102, 180);
}

QScrollBar:horizontal:hover {
    background-color: rgba(45, 45, 45, 30);
}

QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {
    border: none;
    background: transparent;
    width: 0px;
}

QScrollBar::left-arrow:horizontal,
QScrollBar::right-arrow:horizontal,
QScrollBar::add-page:horizontal,
QScrollBar::sub-page:horizontal {
    background: transparent;
    border: none;
}

QMainWindow, QDialog, QWidget {
    background-color: #1e1e1e;
}

QMenuBar {
    background-color: #2d2d2d;
    color: #e0e0e0;
    font-size: 11px;
}

QMenuBar::item:selected {
    background-color: #448fff;
}

QMenu {
    background-color: #2d2d2d;
    color: #e0e0e0;
    border: 1px solid #555555;
    font-size: 11px;
}

QMenu::item:selected {
    background-color: #448fff;
}

QCheckBox, QRadioButton {
    color: #e0e0e0;
    font-size: 11px;
}

QCheckBox::indicator, QRadioButton::indicator {
    width: 14px;
    height: 14px;
}

QCheckBox::indicator:unchecked {
    background-color: #2d2d2d;
    border: 1px solid #555555;
    border-radius: 3px;
}

QCheckBox::indicator:checked {
    background-color: #448fff;
    border: 1px solid #448fff;
    border-radius: 3px;
}

QCheckBox::indicator:unchecked:disabled {
    background-color: #212121;
    border: 1px solid #2e2d2d;
}

QCheckBox::indicator:checked:disabled {
    background-color: #224880;
    border: 1px solid #224880;
}

QGroupBox {
    color: #e0e0e0;
    border: 1px solid #555555;
    border-radius: 5px;
    margin-top: 10px;
    font-size: 11px;
    font-weight: bold;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px 0 5px;
}

QTabWidget::pane {
    border: 1px solid #555555;
    background-color: #2d2d2d;
    border-radius: 4px;
}

QTabBar::tab {
    background-color: #3a3a3a;
    color: #e0e0e0;
    padding: 6px 12px;
    margin-right: 2px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    font-size: 11px;
}

QTabBar::tab:selected {
    background-color: #448fff;
    color: #ffffff;
}

QTabBar::tab:hover:!selected {
    background-color: #4a4a4a;
}

QTextEdit, QPlainTextEdit {
    background-color: #2d2d2d;
    color: #e0e0e0;
    border: 1px solid #555555;
    border-radius: 4px;
    padding: 5px;
    font-size: 11px;
    selection-background-color: #448fff;
}

QHeaderView::section {
    background-color: #3a3a3a;
    color: #e0e0e0;
    padding: 5px;
    border: 1px solid #555555;
    font-size: 11px;
}

QTableView, QTreeView {
    background-color: #2d2d2d;
    color: #e0e0e0;
    alternate-background-color: #252525;
    selection-background-color: #448fff;
    selection-color: #ffffff;
    font-size: 11px;
}

QTableView::item, QTreeView::item {
    padding: 2px;
}

QProgressBar {
    border: none;
    border-radius: 4px;
    background-color: #37474f;
    color: #e0e0e0;
    text-align: center;
    font-size: 11px;
    height: 4px;
}

QProgressBar::chunk {
    border-radius: 4px;
    background-color: #448fff;
    margin: 0px;
}

QToolTip {
    background-color: #3a3a3a;
    color: #e0e0e0;
    border: 1px solid #555555;
    border-radius: 4px;
    padding: 5px;
    font-size: 11px;
}
''')


############################################################################

if DEV_MODE:
    preset.load_from("F:/RenPy/00_Renders/kqueue_blender/kqueue/saves/06_Night.kqp")
    # preset.set_blender("H:/Blender Foundation/blender-5.0.0/blender.exe")
    # preset.add_projects("I:/Blender Library/00_Parts/00_Intro/03_HomeRoaming (old)/001.blend")
    #                     "I:/Blender Library/00_Parts/00_Intro/00_Inside/002_GuitarTuning.blend")
    # mw.update_widgets.emit()


############################################################################
# Periodic Loop

def __start_periodic(interval=1.0):
    """
    Start periodic function.
    """

    def loop():

        while True:
            preset = store.preset

            if preset:
                preset.periodic()

            sleep(interval)

    t = Thread(target=loop, daemon=True)
    t.start()


############################################################################
# Run

__start_periodic()

mw.show()
exit(app.exec_())



