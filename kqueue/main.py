################################################################################
## Main

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
from .project.widgets import QBlendProject, QBlendProjectSettings

from .render import RenderThread
from .loader import LoaderThread
from .config import *
from . import store

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


    def need_save(self, value=True):
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
        self.render_avg_time = set()
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
            return

        if filename == self.blender_exe:
            return

        self.blender_exe = filename
        mw.w_pathToBlender.setText(filename)

        log(f'Blender: {filename}')
        self.need_save()


    def save(self):
        """
        """

        if not self.filename:
            return

        from .save_load import save_file
        save_file([self.project_list, self.blender_exe], self.filename, version=1)

        self.set_save(self.filename)
        self.need_save(False)


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
        self.need_save(False)


    def load_from(self):
        """
        Load save from...
        """

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
        self.need_save(False)

        mw.update_list.emit(False)


    def set_save(self, filename):
        """
        Set currently loaded save.
        """

        if not filename or not Path(filename).exists():
            return

        self.filename = filename
        log(f'Loaded file: {filename}')

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


class MainWindow(qtw.QMainWindow):
    update_title = qtc.pyqtSignal()
    update_list = qtc.pyqtSignal(bool)
    update_widgets = qtc.pyqtSignal()
    log = qtc.pyqtSignal(str)

    def test(self):
        print(1)


    def __init__(self):
        super().__init__()

        self.setWindowIcon(qtg.QIcon(ICON))

        self.setMinimumWidth(1000)
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

            # [button] Locate Save
            self.w_locateSave = w_locateSave = qtw.QPushButton("", clicked=lambda: preset.save_as())
            w_locateSave.clicked.connect(lambda: self.update_widgets.emit())
            w_locateSave.setIcon(qtg.QIcon('kqueue/icons/save.svg'))
            w_locateSave.setToolTip("Save the current file in the desired location.")
            w_locateSave.setShortcut(qtg.QKeySequence("Ctrl+Shift+S"))
            # w_locateSave.setFixedWidth(100)
            w_hBoxLayout.addWidget(w_locateSave)

            # [shortcut] Save
            qtw.QShortcut('Ctrl+S', self).activated.connect(lambda: preset.save())

            # [button] Load
            self.w_locateLoad = w_locateLoad = qtw.QPushButton("", clicked=lambda: preset.load_from())
            w_locateLoad.clicked.connect(lambda: self.update_widgets.emit())
            w_locateLoad.setIcon(qtg.QIcon('kqueue/icons/folder.svg'))
            w_locateLoad.setToolTip("Open a kQueue file.")
            # w_locateLoad.setFixedWidth(100)
            w_hBoxLayout.addWidget(w_locateLoad)

            # [button] Locate Blender
            self.w_locateBlender = w_locateBlender = qtw.QPushButton("", clicked=lambda: preset.locate_blender())
            w_locateBlender.clicked.connect(lambda: self.update_widgets.emit())
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
            self.sw = QBlendProjectSettings(project)
            self.sw.show()

        self.w_listOfProjects = w_listOfProjects = QListWidget()
        w_listOfProjects.itemDoubleClicked.connect(lambda: open_project_settings(self))
        w_listOfProjects.setDragDropMode(qtw.QAbstractItemView.InternalMove)
        w_listOfProjects.model().rowsMoved.connect(lambda: self.update_list.emit(True))
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
        self.w_assign_srgb = w_assign_srgb = qtw.QCheckBox("Save as sRGB")
        w_vBoxLayout.addWidget(w_assign_srgb)

        def toggle_assign_srgb():
            preset.assign_srgb = w_assign_srgb.isChecked()
            self.update_list.emit(False)

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

        # Delete
        if event.key() == Qt.Key_Delete:

            if preset.project_list:
                project = self.get_selected_project()
                preset.project_list.remove(project)
                self.update_list.emit(False)
                self.update_widgets.emit()


    def get_selected_project(self):
        """
        Get selected project.
        """

        item = self.w_listOfProjects.currentItem()
        w_project = self.w_listOfProjects.itemWidget(item)
        return w_project.project if w_project else None


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

        if DEV_MODE:
            event.ignore()
            preset.stop_render()
            event.accept()

        else:
            result = qtw.QMessageBox.question(self,
                        "Confirm Exit...",
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

        for project in preset.project_list:
            w_project = QBlendProject(project=project)

            w_project.set_filename(project.file)
            w_project.set_active(project.active)
            w_project.set_frames(project.get_frames())
            w_project.set_samples(project.get_samples())
            w_project.set_camera(project.camera)
            w_project.set_render_filepath(project.get_render_filepath())

            item = qtw.QListWidgetItem(self.w_listOfProjects)
            item.setSizeHint(w_project.sizeHint())

            self.w_listOfProjects.addItem(item)
            self.w_listOfProjects.setItemWidget(item, w_project)

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


    def __update_widgets(self):

        if preset.is_status('RENDERING') or preset.is_status('RENDERING_STOPPING'):
            self.w_locateSave.setEnabled(False)
            self.w_locateLoad.setEnabled(False)
            self.w_locateBlender.setEnabled(False)
            self.w_selective.setEnabled(False)
            self.w_assign_srgb.setEnabled(False)
            self.w_preview_render.setEnabled(False)
            self.w_marker_render.setEnabled(False)

        else:
            self.w_locateSave.setEnabled(True)
            self.w_locateLoad.setEnabled(True)
            self.w_locateBlender.setEnabled(True)
            self.w_selective.setEnabled(True)
            self.w_assign_srgb.setEnabled(True)
            self.w_preview_render.setEnabled(True)
            self.w_marker_render.setEnabled(True)

        self.w_openFolder.setEnabled(bool(preset.blender_exe))

        self.w_startRender.setEnabled(bool(preset.blender_exe and not preset.is_status('RENDERING') and preset.project_list and preset.get_global_frames_number()))
        self.w_stopRender.setEnabled(preset.is_status('RENDERING') and not preset.is_status('RENDERING_STOPPING'))
        self.w_listOfProjects.setEnabled(bool(not preset.is_adding_projects and not preset.is_status('RENDERING')))
        self.w_cancelShutdown.setEnabled(bool(preset.is_shutting_down))
        self.w_openRender.setEnabled(bool(preset.renders_list))
        self.w_openRenderFolder.setEnabled(bool(preset.renders_list))

        self.w_selective.setChecked(bool(preset.selective_render))
        self.w_assign_srgb.setChecked(bool(preset.assign_srgb))
        self.w_preview_render.setChecked(bool(preset.preview_render))


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

windll.shell32.SetCurrentProcessExplicitAppUserModelID(APPID)
store.app = app = qtw.QApplication([])
store.mw = mw = MainWindow()
store.preset = preset = QueuePreset()
mw.update_widgets.emit()
# app.setStyle("fusion")
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
    preset.set_blender("H:/Blender Foundation/blender-4.3.2/blender.exe")
    # preset.add_projects("I:/Blender Library/00_Parts/00_Intro/03_HomeRoaming (old)/001.blend")
    #                     "I:/Blender Library/00_Parts/00_Intro/00_Inside/002_GuitarTuning.blend")
    # mw.update_widgets.emit()


############################################################################
# Run

mw.show()
exit(app.exec_())