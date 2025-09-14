################################################################################
## Project Widgets

import PyQt5.QtWidgets as qtw
import PyQt5.QtGui as qtg
import PyQt5.QtCore as qtc
from PyQt5.QtCore import Qt

from ..utils.path import join
from ..config import *
from .. import store


################################################################################
## Project Item Widget

class QBlendProject(qtw.QWidget):

    def __init__ (self, project, parent=None):
        super(QBlendProject, self).__init__(parent)

        self.project = project

        # [vbox]
        self.w_vBoxLayout = qtw.QVBoxLayout()
        self.setLayout(self.w_vBoxLayout)

        if True:

            # [hbox]
            self.w_hBoxLayout = qtw.QHBoxLayout()
            self.w_vBoxLayout.addLayout(self.w_hBoxLayout)

            # [check] Active
            self.w_active = qtw.QCheckBox()
            self.w_hBoxLayout.addWidget(self.w_active)

            def toggle_active():
                project.active = self.w_active.isChecked()
                store.mw.update_list.emit(False)
                store.mw.update_widgets.emit()

            self.w_active.clicked.connect(lambda: toggle_active())
            self.w_active.setStyleSheet("""
                QCheckBox::indicator {
                    width : 12;
                    height : 12;
                }
            """)

            # [label] Blend Filename
            self.w_filename = qtw.QLabel()
            self.w_hBoxLayout.addWidget(self.w_filename, Qt.AlignLeft)

        if True:

            # [hbox]
            self.w_hBoxLayout = qtw.QHBoxLayout()
            self.w_vBoxLayout.addLayout(self.w_hBoxLayout)

            # [label] Frames
            self.w_frames = qtw.QLabel()
            self.w_hBoxLayout.addWidget(self.w_frames)

            # [label] Samples
            self.w_samples = qtw.QLabel()
            self.w_hBoxLayout.addWidget(self.w_samples)

            # [label] Camera
            self.w_camera = qtw.QLabel()
            self.w_hBoxLayout.addWidget(self.w_camera)

            # [label] Output
            self.w_render_filepath = qtw.QLabel()
            self.w_hBoxLayout.addWidget(self.w_render_filepath, Qt.AlignLeft)

            # [button] Reload
            # self.w_shutdown = qtw.QPushButton("Reload")#, clicked=lambda: preset.shutdown())
            # self.w_shutdown.setFixedWidth(40)
            # self.w_hBoxLayout.addWidget(self.w_shutdown, Qt.AlignRight)

    def set_filename(self, filename):
        self.w_filename.setText(filename)

    def get_filename(self):
        return self.w_filename.text() or None

    def set_active(self, value: bool):
        self.w_active.setChecked(value)

    def set_frames(self, frames):
        self.w_frames.setText(f'Frames: [{frames}]')

    def set_samples(self, samples):
        self.w_samples.setText(f'| Samples: {samples}')

    def set_camera(self, camera):
        self.w_camera.setText(f'| Camera: "{camera}"')

    def set_render_filepath(self, filepath):
        self.w_render_filepath.setText(f'| Output: "{filepath}"')



################################################################################
## Project Settings Window

class QBlendProjectSettings(qtw.QWidget):

    wResult_setText = qtc.pyqtSignal(str)


    def __init__(self, project):
        super().__init__()

        self.project = project

        # Window
        self.setWindowTitle("Project Settings")
        self.setWindowIcon(qtg.QIcon(ICON))
        self.setMinimumWidth(450)
        self.setFixedHeight(450)
        self.setWindowModality(Qt.ApplicationModal)

        # ! [vbox]
        layout = qtw.QVBoxLayout()
        self.setLayout(layout)

        # [label] Settings
        font = qtg.QFont()
        font.setPixelSize(18)

        self.label = qtw.QLabel(str(project.file))
        self.label.setFont(font)
        layout.addWidget(self.label, 0, Qt.AlignTop)

        # [form] Preset Override
        l_form = qtw.QFormLayout()
        layout.addLayout(l_form)

        # [edit] Frames
        self.w_frames = w_frames = qtw.QLineEdit(str(project.get_frames()))
        w_frames.setPlaceholderText(str(project.frames))
        l_form.addRow("Frames", self.w_frames)

        # # [label] Frames Result
        # self.w_result = w_result = qtw.QLabel("")
        # self.w_result.setFont(font)
        # l_form.addRow("", w_result)

        # self.wResult_setText.connect(w_result.setText)
        # self.w_frames.textChanged.connect(self.wResult_setText.emit)
        # .w_result.setText(f'{self.project.get_frames_list()}')

        # w_frames.
        # w_result.setText("!")

        # [edit] Samples
        self.w_samples = w_samples = qtw.QLineEdit(str(project.get_samples()))
        w_samples.setPlaceholderText(str(project.samples))
        w_samples.setValidator(qtg.QIntValidator(1, 99999, self))
        l_form.addRow("Samples", w_samples)

        # ! [hbox] Render Filepath
        w_hBoxLayoutRenderFilepath = qtw.QHBoxLayout()
        l_form.addRow("Render Filepath", w_hBoxLayoutRenderFilepath)

        # [edit] Render Filepath
        self.w_renderFilepath = w_renderFilepath = qtw.QLineEdit(str(project.get_render_filepath()))
        w_renderFilepath.setPlaceholderText(str(project.render_filepath))
        w_hBoxLayoutRenderFilepath.addWidget(w_renderFilepath)

        # [button] Render Filepath
        def locate_filepath():
            filepath, _ = qtw.QFileDialog.getSaveFileName(self, 'Set Render Filepath', w_renderFilepath.text())
            if not filepath: return
            w_renderFilepath.setText(join(filepath))
        w_locateFilepath = qtw.QPushButton("", clicked=locate_filepath)
        w_locateFilepath.clicked.connect(lambda: store.mw.update_widgets.emit())
        w_locateFilepath.setIcon(qtg.QIcon('kqueue/icons/folder.svg'))
        w_locateFilepath.setFixedWidth(30)
        w_hBoxLayoutRenderFilepath.addWidget(w_locateFilepath)

        # [edit] File Format
        self.w_fileFormat = w_fileFormat = qtw.QComboBox()
        w_fileFormat.addItems(['PNG', 'JPEG', 'JPEG2000', 'WEBP', 'TIFF'])
        w_fileFormat.setCurrentText(str(project.get_file_format()))
        l_form.addRow("File Format", w_fileFormat)

        # [edit] Camera
        self.w_camera = w_camera = qtw.QComboBox()
        w_camera.addItems(project.camera_list)
        w_camera.setCurrentText(str(project.get_camera()))
        l_form.addRow("Camera", w_camera)

        # [edit] Scene
        self.w_scene = w_scene = qtw.QComboBox()
        w_scene.addItems(project.scene_list)
        w_scene.setCurrentText(str(project.get_scene()))
        l_form.addRow("Scene", w_scene)

        # [edit] Persistent
        self.w_usePersistentData = w_usePersistentData = qtw.QPushButton(str(project.get_use_persistent_data()))
        w_usePersistentData.setCheckable(True)
        w_usePersistentData.setChecked(project.get_use_persistent_data())
        w_usePersistentData.clicked.connect(lambda: w_usePersistentData.setText(str(w_usePersistentData.isChecked())))
        l_form.addRow("Persistent Data", w_usePersistentData)

        # [edit] Persistent
        self.w_useAdaptiveSampling = w_useAdaptiveSampling = qtw.QPushButton(str(project.get_use_adaptive_sampling()))
        w_useAdaptiveSampling.setCheckable(True)
        w_useAdaptiveSampling.setChecked(project.get_use_adaptive_sampling())
        w_useAdaptiveSampling.clicked.connect(lambda: w_useAdaptiveSampling.setText(str(w_useAdaptiveSampling.isChecked())))
        l_form.addRow("Adaptive Sampling", w_useAdaptiveSampling)

        # [edit] Denoiser
        self.w_denoiser = w_denoiser = qtw.QComboBox()
        w_denoiser.addItems(['NONE', 'OPTIX', 'OPENIMAGEDENOISE'])
        w_denoiser.setCurrentText(str(project.get_denoiser()))
        l_form.addRow("Denoiser", w_denoiser)

        # [button] Denoiser Use GPU
        self.w_denoiserUseGPU = w_denoiserUseGPU = qtw.QPushButton(str(project.get_denoising_use_gpu()))
        w_denoiserUseGPU.setCheckable(True)
        w_denoiserUseGPU.setChecked(project.get_denoising_use_gpu())
        w_denoiserUseGPU.clicked.connect(lambda: w_denoiserUseGPU.setText(str(w_denoiserUseGPU.isChecked())))
        l_form.addRow("Use GPU", w_denoiserUseGPU)

        # [edit] Denoiser Input Passes
        self.w_denoiserInputPasses = w_denoiserInputPasses = qtw.QComboBox()
        w_denoiserInputPasses.addItems(['RGB', 'RGB_ALBEDO', 'RGB_ALBEDO_NORMAL'])
        w_denoiserInputPasses.setCurrentText(str(project.get_denoising_input_passes()))
        l_form.addRow("Input Passes", w_denoiserInputPasses)

        # [edit] Denoiser Use GPU
        self.w_denoiserPrefilter = w_denoiserPrefilter = qtw.QComboBox()
        w_denoiserPrefilter.addItems(['NONE', 'FAST', 'ACCURATE'])
        w_denoiserPrefilter.setCurrentText(str(project.get_denoising_prefilter()))
        l_form.addRow("Prefilter", w_denoiserPrefilter)

        # ! [hbox] Save & Cancel
        w_hBoxLayout = qtw.QHBoxLayout()
        layout.addLayout(w_hBoxLayout)

        # [button] Save
        w_save = qtw.QPushButton("Save", clicked=lambda: self.save_and_close())
        w_save.setFixedWidth(100)
        w_save.setFixedHeight(40)
        w_hBoxLayout.addWidget(w_save, 0, Qt.AlignRight)

        # [button] Cancel
        w_cancel = qtw.QPushButton("Cancel", clicked=lambda: self.close())
        w_cancel.setFixedWidth(100)
        w_cancel.setFixedHeight(40)
        w_hBoxLayout.addWidget(w_cancel)

        self.update_frames_result()


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
        # self.w_result.setText(f'{self.project.get_frames_list()}')


    def save_and_close(self):
        """
        Save values and close this window.
        """

        self.save()
        self.close()
        store.mw.update_list.emit(False)


    def save(self):
        """
        Save values and set need save if something changed.
        """

        def set_value(variable, value):

            if getattr(self.project, variable) == value:
                return

            setattr(self.project, variable, value)
            store.preset.need_save(True)

        set_value('frames_override', self.w_frames.text())
        set_value('samples_override', self.w_samples.text())
        set_value('render_filepath_override', self.w_renderFilepath.text())
        set_value('camera_override', self.w_camera.currentText())
        set_value('scene_override', self.w_scene.currentText())
        set_value('use_persistent_data_override', eval(self.w_usePersistentData.text()))
        set_value('use_adaptive_sampling_override', eval(self.w_useAdaptiveSampling.text()))
        set_value('denoiser_override', self.w_denoiser.currentText())
        set_value('denoising_use_gpu_override', eval(self.w_denoiserUseGPU.text()))
        set_value('denoising_input_passes', self.w_denoiserInputPasses.currentText())
        set_value('denoising_prefilter', self.w_denoiserPrefilter.currentText())


        # project.frames_override = self.w_frames.text()
        # project.samples_override = self.w_samples.text()
        # project.render_filepath_override = self.w_renderFilepath.text()
        # project.camera_override = self.w_camera.currentText()
        # project.scene_override = self.w_scene.currentText()
        # project.use_persistent_data_override = eval(self.w_usePersistentData.text())
        # project.use_adaptive_sampling_override = eval(self.w_useAdaptiveSampling.text())
        # project.denoiser_override = self.w_denoiser.currentText()
        # project.denoising_use_gpu_override = eval(self.w_denoiserUseGPU.text())
        # project.denoising_input_passes = self.w_denoiserInputPasses.currentText()
        # project.denoising_prefilter = self.w_denoiserPrefilter.currentText()