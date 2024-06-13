################################################################################
## Project

import store
from config import *

import PyQt5.QtWidgets as qtw
import PyQt5.QtGui as qtg
from PyQt5.QtCore import Qt

from os.path import normpath
from utils.filter_frames import filter_frames


################################################################################
## Blend Project Settings

class BlendProject():

    def __init__(self,
                 file,
                 frame_start,
                 frame_end,
                 scene,
                 scene_list,
                 camera,
                 camera_list,
                 use_persistent_data,
                 render_filepath,
                 use_adaptive_sampling,
                 samples,
                 denoiser,
                 denoising_use_gpu,
                 denoising_input_passes,
                 denoising_prefilter,):
        self.file = file if file else None
        self.frames, self.frames_override = f"{frame_start}-{frame_end}", None
        self.scene, self.scene_override = scene, None
        self.scene_list = scene_list
        self.camera, self.camera_override = camera, None
        self.camera_list = camera_list
        self.use_persistent_data, self.use_persistent_data_override = use_persistent_data, None
        self.render_filepath, self.render_filepath_override = normpath(render_filepath), None
        self.use_adaptive_sampling, self.use_adaptive_sampling_override = use_adaptive_sampling, None
        self.samples, self.samples_override = samples, None
        self.denoiser, self.denoiser_override = denoiser, None
        self.denoising_use_gpu, self.denoising_use_gpu_override = denoising_use_gpu, None
        self.denoising_input_passes, self.denoising_input_passes_override = denoising_input_passes, None
        self.denoising_prefilter, self.denoising_prefilter_override = denoising_prefilter, None

    def get_frames(self): return self.get(self.frames_override, self.frames)
    def get_frames_list(self): return filter_frames(self.get_frames())
    def get_scene(self): return self.get(self.scene_override, self.scene)
    def get_camera(self): return self.get(self.camera_override, self.camera)
    def get_use_persistent_data(self): return self.get(self.use_persistent_data_override, self.use_persistent_data)
    def get_render_filepath(self): return self.get(self.render_filepath_override, self.render_filepath)
    def get_use_adaptive_sampling(self): return self.get(self.use_adaptive_sampling_override, self.use_adaptive_sampling)
    def get_samples(self): return self.get(self.samples_override, self.samples)
    def get_denoiser(self): return self.get(self.denoiser_override, self.denoiser)
    def get_denoising_use_gpu(self): return self.get(self.denoising_use_gpu_override, self.denoising_use_gpu)
    def get_denoising_input_passes(self): return self.get(self.denoising_input_passes_override, self.denoising_input_passes)
    def get_denoising_prefilter(self): return self.get(self.denoising_prefilter_override, self.denoising_prefilter)

    def get(self, v1, v2):
        if v1 is None:
            return v2
        else:
            return v1


################################################################################
## Project Settings Window

class BlendProjectWindow(qtw.QWidget):


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
        font.setPixelSize(15)

        self.label = qtw.QLabel(f"{project.file}")
        self.label.setFont(font)
        layout.addWidget(self.label, 0, Qt.AlignTop)

        # [form] Preset Override
        l_form = qtw.QFormLayout()
        layout.addLayout(l_form)

        # [edit] Frames
        self.w_frames = w_frames = qtw.QLineEdit(str(project.get_frames()))
        w_frames.setPlaceholderText(str(project.frames))
        l_form.addRow("Frames", self.w_frames)

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
            w_renderFilepath.setText(normpath(filepath))
        w_locateFilepath = qtw.QPushButton(">", clicked=locate_filepath)
        w_locateFilepath.clicked.connect(lambda: self.update())
        w_locateFilepath.setFixedWidth(30)
        w_hBoxLayoutRenderFilepath.addWidget(w_locateFilepath)

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


    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
        elif event.key() == Qt.Key_Return:
            self.save_and_close()

    def save_and_close(self):
        self.save()
        self.close()
        store.mw.update_list()

    def save(self):
        project = self.project
        project.frames_override = self.w_frames.text()
        project.samples_override = self.w_samples.text()
        project.render_filepath_override = self.w_renderFilepath.text()
        project.camera_override = self.w_camera.currentText()
        project.scene_override = self.w_scene.currentText()
        project.use_persistent_data_override = eval(self.w_usePersistentData.text())
        project.use_adaptive_sampling_override = eval(self.w_useAdaptiveSampling.text())
        project.denoiser_override = self.w_denoiser.currentText()
        project.denoising_use_gpu_override = eval(self.w_denoiserUseGPU.text())
        print(project.denoising_use_gpu_override)
        project.denoising_input_passes = self.w_denoiserInputPasses.currentText()
        project.denoising_prefilter = self.w_denoiserPrefilter.currentText()
