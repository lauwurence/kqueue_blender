################################################################################
## Project Widgets

import PyQt5.QtWidgets as qtw
import PyQt5.QtGui as qtg
import PyQt5.QtCore as qtc
from PyQt5.QtCore import Qt

from ..widgets.QPushButton import QPushButton
from ..widgets.QComboBox import QComboBox
from ..utils.pathutils import join
from ..config import *
from .. import store

from pathlib import Path


################################################################################
## Project Item Widget

class QBlendProject(qtw.QWidget):
    initialized = False

    def __init__ (self, project, parent=None):
        super(QBlendProject, self).__init__(parent)

        self.project = project

        # [hbox]
        self.w_hBoxLayout = qtw.QHBoxLayout()
        self.setLayout(self.w_hBoxLayout)

        def add_separator():

            # [frame} Separator
            separator = qtw.QFrame()
            separator.setFrameShape(qtw.QFrame.VLine)
            separator.setFrameShadow(qtw.QFrame.Plain)
            separator.setStyleSheet("""
                QFrame {
                    background-color: #4a4a4a;
                    color: #4a4a4a;
                    margin: 2px;
                }
            """)

            self.w_hBoxLayout.addWidget(separator)


        # [check] Active
        self.w_active = qtw.QCheckBox()
        self.w_hBoxLayout.addWidget(self.w_active)

        def toggle_active():
            project.active = self.w_active.isChecked()
            store.mw.update_list.emit(False)
            store.mw.update_widgets.emit()
            store.preset.set_need_save()

        self.w_active.clicked.connect(lambda: toggle_active())
        self.w_active.setStyleSheet("""
            QCheckBox::indicator {
                width: 12;
                height: 12;
            }
        """)

        # [label] Blend Filename
        self.w_filename = qtw.QLabel()
        self.w_hBoxLayout.addWidget(self.w_filename)

        add_separator()

        # [label] Frames
        self.w_frames = qtw.QLabel()
        self.w_hBoxLayout.addWidget(self.w_frames)

        add_separator()

        # [label] Resolution
        self.w_resolution = qtw.QLabel()
        self.w_hBoxLayout.addWidget(self.w_resolution)

        add_separator()

        # [label] Samples
        self.w_samples = qtw.QLabel()
        self.w_hBoxLayout.addWidget(self.w_samples)

        add_separator()

        # [label] Camera
        # self.w_camera = qtw.QLabel()
        # self.w_hBoxLayout.addWidget(self.w_camera)

        # [label] Output
        self.w_render_filepath = qtw.QLabel()
        self.w_hBoxLayout.addWidget(self.w_render_filepath)

        # [label] Open Render Output Image
        self.w_open_render_image = QPushButton("", clicked=project.open_render_output_image)
        self.w_open_render_image.setIcon(qtg.QIcon('kqueue/icons/open_render.svg'))
        self.w_open_render_image.setToolTip("Open the last render.")
        self.w_open_render_image.setIconSize(qtc.QSize(14, 14))
        self.w_open_render_image.setFixedSize(20, 20)
        self.w_open_render_image.setFlat(True)
        self.w_hBoxLayout.addWidget(self.w_open_render_image)

        # [label] Open Render Output Folder
        self.w_open_render_folder = QPushButton("", clicked=project.open_render_output_folder)
        self.w_open_render_folder.setIcon(qtg.QIcon('kqueue/icons/folder.svg'))
        self.w_open_render_folder.setToolTip("Open render folder.")
        self.w_open_render_folder.setIconSize(qtc.QSize(14, 14))
        self.w_open_render_folder.setFixedSize(20, 20)
        self.w_open_render_folder.setFlat(True)
        self.w_hBoxLayout.addWidget(self.w_open_render_folder)

        # [stretch]
        self.w_hBoxLayout.addStretch()

        self.w_open = None
        self.w_reload = None
        self.w_not_exists = None

        self.initialized = True

        self.UPDATE_LIST = [
            (project, 'file_exists'),
            (project, 'is_outdated'),
        ]

        self.update_widgets()


    def update_widgets(self):
        """
        """

        if not self.initialized:
            return

        update = False

        for obj, name in self.UPDATE_LIST:
            new_value = getattr(obj, name)()
            old_value = getattr(self, f'__{name}', None)

            if old_value == new_value:
                continue

            setattr(self, f'__{name}', new_value)
            update = True

        if not update:
            return

        if self.w_open:
            self.w_hBoxLayout.removeWidget(self.w_open)

        if self.w_reload:
            self.w_hBoxLayout.removeWidget(self.w_reload)

        if self.w_not_exists:
            self.w_hBoxLayout.removeWidget(self.w_not_exists)

        if self.project.file_exists():

            # [button] Start
            self.w_open = QPushButton("", clicked=lambda: self.project.open_file())
            self.w_open.setIcon(qtg.QIcon('kqueue/icons/blender_bw.svg'))
            self.w_open.setIconSize(qtc.QSize(16, 16))
            self.w_open.setFixedSize(20, 20)
            self.w_open.setToolTip("Open the Blender project.")
            self.w_hBoxLayout.addWidget(self.w_open)

            if self.project.is_outdated():

                # [button] Reload
                self.w_reload = QPushButton("", clicked=lambda: self.project.reload())
                self.w_reload.setIcon(qtg.QIcon('kqueue/icons/reload_project.svg'))
                self.w_reload.setIconSize(qtc.QSize(16, 16))
                self.w_reload.setFixedSize(20, 20)
                self.w_reload.setToolTip("Reload the Blender project.")
                self.w_hBoxLayout.addWidget(self.w_reload)

        else:
            self.w_not_exists = qtw.QLabel("Does not exist!")
            self.w_not_exists.setStyleSheet("color: red; font-weight: bold;")
            self.w_not_exists.setFixedWidth(75)
            self.w_hBoxLayout.addWidget(self.w_not_exists)

        self.w_open_render_image.setEnabled(bool(self.project.get_render_output_image()))
        self.w_open_render_folder.setEnabled(bool(self.project.get_render_output_folder()))


    def set_filename(self, filename):
        path = Path(filename)
        self.w_filename.setText(f'".../{path.name}"')
        self.w_filename.setStyleSheet("font-weight: bold;")

    def get_filename(self):
        return self.w_filename.text() or None

    def set_active(self, value: bool):
        self.w_active.setChecked(value)

    def set_frames(self, frames):
        self.w_frames.setText(f'Fra: [{frames}]')

        if self.project.frames_overrode():
            self.w_frames.setStyleSheet("font-weight: bold;")

    def set_samples(self, samples):
        self.w_samples.setText(f'Sam: {samples}')

    def set_resolution(self, resolution):
        self.w_resolution.setText(f'Res: {resolution}')

    # def set_camera(self, camera):
    #     self.w_camera.setText(f'Camera: "{camera}"')

    def set_render_filepath(self, filepath):
        self.w_render_filepath.setText(f'Out: "{filepath}"')

        if not self.project.render_filepath_exists():
            self.w_render_filepath.setStyleSheet("color: red;")


################################################################################
## Project Settings Window

class QBlendProjectSettings(qtw.QWidget):
    wResult_setText = qtc.pyqtSignal(str)

    def __init__(self, project):
        super().__init__()

        self.project = project

        # Config
        FIELD_HEIGHT = 22

        # Window
        self.setWindowTitle(str(self.project.file))
        self.setWindowIcon(qtg.QIcon(ICON))
        self.setMinimumWidth(450)
        self.setFixedHeight(425)
        self.setWindowModality(Qt.ApplicationModal)
        self.resize(450, 400)

        from ..main import set_window_titlebar_dark
        set_window_titlebar_dark(self)

        # [vbox]
        layout = qtw.QVBoxLayout()
        self.setLayout(layout)

        # [form] Preset Override
        l_form = qtw.QFormLayout()
        layout.addLayout(l_form)


        # [hbox] Frames
        hbox = qtw.QHBoxLayout()
        l_form.addRow("Frames", hbox)

        if True:

            # [edit] Frames
            self.frames = qtw.QLineEdit(str(project.get_frames()))
            self.frames.setFixedHeight(FIELD_HEIGHT)
            self.frames.setPlaceholderText(str(project.frames))
            hbox.addWidget(self.frames)

            # [button] Frames Reset
            self.framesReset = QPushButton("", clicked=lambda: self.frames.setText(str(project.get_frames())))
            self.framesReset.setFixedHeight(FIELD_HEIGHT)
            self.framesReset.setFixedWidth(30)
            self.framesReset.setIcon(qtg.QIcon('kqueue/icons/reset.svg'))
            self.framesReset.setIconSize(qtc.QSize(18, 18))
            hbox.addWidget(self.framesReset)


        # [label] Frames Result
        self.result = qtw.QLabel("")
        self.result.setEnabled(False)
        self.result.setFixedHeight(FIELD_HEIGHT)
        self.result.setStyleSheet("font-size: 8px;")
        l_form.addRow("", self.result)

        def update_result():
            try:
                tt = project.get_frames_list_string(frames=self.frames.text())
            except:
                tt = "!"

            self.wResult_setText.emit(tt)

        self.wResult_setText.connect(self.result.setText)
        self.frames.textChanged.connect(update_result)


        # [hbox] Resolution
        hbox = qtw.QHBoxLayout()
        l_form.addRow("Resolution", hbox)

        if True:

            # [edit] Resolution X
            self.resX = qtw.QLineEdit(str(project.get_resolution_x()))
            self.resX.setFixedHeight(FIELD_HEIGHT)
            self.resX.setPlaceholderText(str(project.resolution_x))
            self.resX.setValidator(qtg.QIntValidator(1, 32 * 1024, self))
            hbox.addWidget(self.resX)

            # [edit] Resolution Y
            self.resY = qtw.QLineEdit(str(project.get_resolution_y()))
            self.resY.setFixedHeight(FIELD_HEIGHT)
            self.resY.setPlaceholderText(str(project.resolution_y))
            self.resY.setValidator(qtg.QIntValidator(1, 32 * 1024, self))
            hbox.addWidget(self.resY)

            # [edit] Resolution Percentage
            self.resPerc = qtw.QLineEdit(str(project.get_resolution_percentage()))
            self.resPerc.setFixedHeight(FIELD_HEIGHT)
            self.resPerc.setPlaceholderText(str(project.resolution_percentage))
            self.resPerc.setValidator(qtg.QIntValidator(1, 999999, self))
            hbox.addWidget(self.resPerc)

            # [button] Resolution Reset
            def reset_resolution():
                self.resX.setText(str(project.resolution_x))
                self.resY.setText(str(project.resolution_y))
                self.resPerc.setText(str(project.resolution_percentage))

            self.resReset = QPushButton("", clicked=reset_resolution)
            self.resReset.setIcon(qtg.QIcon('kqueue/icons/reset.svg'))
            self.resReset.setFixedWidth(30)
            self.resReset.setFixedHeight(FIELD_HEIGHT)
            self.resReset.setIconSize(qtc.QSize(18, 18))
            hbox.addWidget(self.resReset)


        # [edit] Samples
        self.samples = qtw.QLineEdit(str(project.get_samples()))
        self.samples.setFixedHeight(FIELD_HEIGHT)
        self.samples.setPlaceholderText(str(project.samples))
        self.samples.setValidator(qtg.QIntValidator(1, 99999, self))
        l_form.addRow("Samples", self.samples)


        # [hbox] Render Filepath
        hbox = qtw.QHBoxLayout()
        l_form.addRow("Render Filepath", hbox)

        if True:

            # [edit] Render Filepath
            self.renderFilepath = qtw.QLineEdit(str(project.get_render_filepath()))
            self.renderFilepath.setFixedHeight(FIELD_HEIGHT)
            self.renderFilepath.setPlaceholderText(str(project.render_filepath))
            hbox.addWidget(self.renderFilepath)

            # [button] Render Filepath
            def locate_filepath():
                filepath, _ = qtw.QFileDialog.getSaveFileName(self, 'Set Render Filepath', self.renderFilepath.text())

                if not filepath:
                    return

                self.renderFilepath.setText(join(filepath))

            self.locateFilepath = QPushButton("", clicked=locate_filepath)
            self.locateFilepath.setFixedWidth(30)
            self.locateFilepath.setFixedHeight(FIELD_HEIGHT)
            self.locateFilepath.setIcon(qtg.QIcon('kqueue/icons/folder.svg'))
            self.locateFilepath.setIconSize(qtc.QSize(18, 18))
            self.locateFilepath.clicked.connect(lambda: store.mw.update_widgets.emit())
            hbox.addWidget(self.locateFilepath)


        # [edit] File Format
        self.fileFormat = QComboBox()
        self.fileFormat.setFixedHeight(FIELD_HEIGHT)
        self.fileFormat.addItems(['PNG', 'JPEG', 'JPEG2000', 'WEBP', 'TIFF'])
        self.fileFormat.setCurrentText(str(project.get_file_format()))
        l_form.addRow("File Format", self.fileFormat)


        # [edit] Camera
        self.camera = QComboBox()
        self.camera.addItems(project.camera_list)
        self.camera.setCurrentText(str(project.get_camera()))
        self.camera.setFixedHeight(FIELD_HEIGHT)
        l_form.addRow("Camera", self.camera)


        # [edit] Scene
        self.scene = QComboBox()
        self.scene.setFixedHeight(FIELD_HEIGHT)
        self.scene.addItems(project.scene_list)
        self.scene.setCurrentText(str(project.get_scene()))
        l_form.addRow("Scene", self.scene)


        # [edit] Persistent
        self.usePersistentData = QPushButton(str(project.get_use_persistent_data()))
        self.usePersistentData.setFixedHeight(FIELD_HEIGHT)
        self.usePersistentData.setCheckable(True)
        self.usePersistentData.setChecked(project.get_use_persistent_data())
        self.usePersistentData.clicked.connect(lambda: self.usePersistentData.setText(str(self.usePersistentData.isChecked())))
        l_form.addRow("Persistent Data", self.usePersistentData)


        # [edit] Adaptive Sampling
        self.useAdaptiveSampling = QPushButton(str(project.get_use_adaptive_sampling()))
        self.useAdaptiveSampling.setFixedHeight(FIELD_HEIGHT)
        self.useAdaptiveSampling.setCheckable(True)
        self.useAdaptiveSampling.setChecked(project.get_use_adaptive_sampling())
        self.useAdaptiveSampling.clicked.connect(lambda: self.useAdaptiveSampling.setText(str(self.useAdaptiveSampling.isChecked())))
        l_form.addRow("Adaptive Sampling", self.useAdaptiveSampling)


        # [edit] Denoiser
        self.denoiser = QComboBox()
        self.denoiser.setFixedHeight(FIELD_HEIGHT)
        self.denoiser.addItems(['NONE', 'OPTIX', 'OPENIMAGEDENOISE'])
        self.denoiser.setCurrentText(str(project.get_denoiser()))
        l_form.addRow("Denoiser", self.denoiser)

        # [button] Denoiser Use GPU
        self.denoiserUseGPU = QPushButton(str(project.get_denoising_use_gpu()))
        self.denoiserUseGPU.setFixedHeight(FIELD_HEIGHT)
        self.denoiserUseGPU.setCheckable(True)
        self.denoiserUseGPU.setChecked(project.get_denoising_use_gpu())
        self.denoiserUseGPU.clicked.connect(lambda: self.denoiserUseGPU.setText(str(self.denoiserUseGPU.isChecked())))
        l_form.addRow("Use GPU", self.denoiserUseGPU)

        # [edit] Denoiser Input Passes
        self.denoiserInputPasses = QComboBox()
        self.denoiserInputPasses.addItems(['RGB', 'RGB_ALBEDO', 'RGB_ALBEDO_NORMAL'])
        self.denoiserInputPasses.setCurrentText(str(project.get_denoising_input_passes()))
        self.denoiserInputPasses.setFixedHeight(FIELD_HEIGHT)
        l_form.addRow("Input Passes", self.denoiserInputPasses)

        # [edit] Denoiser Use GPU
        self.denoiserPrefilter = QComboBox()
        self.denoiserPrefilter.addItems(['NONE', 'FAST', 'ACCURATE'])
        self.denoiserPrefilter.setCurrentText(str(project.get_denoising_prefilter()))
        self.denoiserPrefilter.setFixedHeight(FIELD_HEIGHT)
        l_form.addRow("Prefilter", self.denoiserPrefilter)


        layout.addSpacing(10)


        # [hbox] Save & Cancel
        hbox = qtw.QHBoxLayout()
        layout.addLayout(hbox)

        if True:

            # [button] Save
            save = QPushButton("Save", clicked=lambda: self.save_and_close())
            save.setFixedWidth(100)
            save.setFixedHeight(30)
            hbox.addWidget(save, 0, Qt.AlignRight)

            # [button] Cancel
            cancel = QPushButton("Cancel", clicked=lambda: self.close())
            cancel.setFixedWidth(100)
            cancel.setFixedHeight(30)
            hbox.addWidget(cancel)


        self.update_frames_result()
        update_result()


    def keyPressEvent(self, event):

        if event.key() == Qt.Key_Escape:
            self.close()

        elif event.key() == Qt.Key_Return:
            self.save_and_close()


    def update_frames_result(self):
        """
        """

        self.wResult_setText.emit(f'{self.project.get_frames_list()}')
        # print(f'{self.project.get_frames_list()}')
        # self.result.setText(f'{self.project.get_frames_list()}')


    def save_and_close(self):
        """
        Save values and close this window.
        """

        self.__save()
        self.close()
        store.mw.update_list.emit(False)


    def __save(self):
        """
        Save values and set need save if something changed.
        """

        need_save = False

        def set_value(name, new_value):
            new_value = new_value or None
            old_value = getattr(self.project, name)

            if new_value == old_value:
                return

            print(name, old_value, "=>", new_value)
            setattr(self.project, name, new_value)

            nonlocal need_save
            need_save = True

        set_value('resolution_x_override', self.resX.text())
        set_value('resolution_y_override', self.resY.text())
        set_value('resolution_percentage_override', self.resPerc.text())
        set_value('frames_override', self.frames.text())
        set_value('samples_override', self.samples.text())
        set_value('render_filepath_override', self.renderFilepath.text())
        set_value('camera_override', self.camera.currentText())
        set_value('scene_override', self.scene.currentText())
        set_value('use_persistent_data_override', eval(self.usePersistentData.text()))
        set_value('use_adaptive_sampling_override', eval(self.useAdaptiveSampling.text()))
        set_value('denoiser_override', self.denoiser.currentText())
        set_value('denoising_use_gpu_override', eval(self.denoiserUseGPU.text()))
        set_value('denoising_input_passes', self.denoiserInputPasses.currentText())
        set_value('denoising_prefilter', self.denoiserPrefilter.currentText())

        if need_save:
            store.preset.set_need_save()
            print("New settings applied.")
