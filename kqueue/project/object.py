################################################################################
## Project Object

import os
from pathlib import Path

from ..utils.filter_frames import filter_frames
from ..utils.pathutils import join, exists, open_folder, open_image
from ..config import *
from .. import store, save_load

FORMATS = {
    'PNG' : '.png',
    'WEBP' : '.webp',
    'JPEG' : '.jpeg',
    'JPEG2000' : 'jpg2',
    'TIFF' : '.tiff'
}


class BlendProject():
    active = True
    markers = []
    mod_time = None
    file_format, file_format_override = 'PNG', None
    resolution_x, resolution_x_override = None, None
    resolution_y, resolution_y_override = None, None
    resolution_percentage, resolution_percentage_override = None, None

    def __init__(self,
                 file,
                 frame_start,
                 frame_end,
                 scene,
                 scene_list,
                 camera,
                 camera_list,
                 resolution_x,
                 resolution_y,
                 resolution_percentage,
                 use_persistent_data,
                 render_filepath,
                 file_format,
                 use_adaptive_sampling,
                 samples,
                 denoiser,
                 denoising_use_gpu,
                 denoising_input_passes,
                 denoising_prefilter,
                 markers,
                 mod_time):
        self.active = True
        self.file = file if file else None
        self.frames, self.frames_override = f"{frame_start}-{frame_end}", None
        self.scene, self.scene_override = scene, None
        self.scene_list = scene_list
        self.camera, self.camera_override = camera, None
        self.camera_list = camera_list
        self.resolution_x, self.resolution_x_override = resolution_x, None
        self.resolution_y, self.resolution_y_override = resolution_y, None
        self.resolution_percentage, self.resolution_percentage_override = resolution_percentage, None
        self.use_persistent_data, self.use_persistent_data_override = use_persistent_data, None
        self.render_filepath, self.render_filepath_override = join(render_filepath), None
        self.file_format, self.file_format_override = file_format, None
        self.use_adaptive_sampling, self.use_adaptive_sampling_override = use_adaptive_sampling, None
        self.samples, self.samples_override = samples, None
        self.denoiser, self.denoiser_override = denoiser, None
        self.denoising_use_gpu, self.denoising_use_gpu_override = denoising_use_gpu, None
        self.denoising_input_passes, self.denoising_input_passes_override = denoising_input_passes, None
        self.denoising_prefilter, self.denoising_prefilter_override = denoising_prefilter, None
        self.markers = markers
        self.mod_time = mod_time


    def is_renderable(self):
        """ """

        return self.active and self.get_camera() and self.file_exists() and self.render_filepath_exists()


    def file_exists(self):
        """
        Does the project file exist?
        """

        if not self.file:
            return False

        return exists(self.file)


    def is_outdated(self):
        """
        Was the project updated after the last data fetch?
        """

        if not self.file_exists():
            return True

        cache = save_load.load_cache()

        if cache is None:
            return True

        mod_time = int(Path(self.file).stat().st_mtime)

        if self.file not in cache:
            return True

        if self.mod_time != mod_time:
            return True

        return False


    def get_frames(self):
        """ Get frames list as a string. """
        return self.get(self.frames_override, self.frames) or ""

    def frames_overrode(self):
        """ Are frames overrode? """
        return self.get_frames() != self.frames

    def reset_frames_override(self):
        """ Reset frames override settings. """
        self.frames_override = None


    def get_markers(self):
        """
        Get markers as a string.
        """

        markers = self.markers

        if not markers:
            return ""

        return ",".join([ str(m) for m in markers])


    def get_frames_list(self, frames=None):
        """
        Get frames as an int list.
        """

        if not frames:
            if not store.preset.marker_render:
                frames = self.get_frames()
            else:
                frames = self.get_markers()

        if store.preset.selective_render:
            rv = []

            for frame in filter_frames(frames) or []:
                filename = self.compose_render_filename(frame)

                if Path(filename).exists():
                    continue

                rv.append(frame)

            return rv or []

        return filter_frames(frames) or []


    def get_frames_list_string(self, frames=None):
        """
        Get frames list as a string.
        """

        return ",".join([ str(frame) for frame in self.get_frames_list(frames) ])


    def render_filepath_exists(self):
        """
        """

        return Path(self.get_render_filepath()).parent.exists()


    def compose_render_filename(self, frame):
        """
        Compose render filename.
        """

        format = self.get_file_format()
        suffix = FORMATS.get(format, None)

        if suffix is None:
            raise Exception(f'Unknown image format: {format}')

        filepath = self.get_render_filepath()
        path = Path(filepath)
        basename = path.stem
        zeros = basename.count("#") or 4
        number = str(frame)

        while len(number) < zeros:
            number = "0" + number

        to_replace = "#" * zeros

        if to_replace in basename:
            basename = basename.replace(to_replace, number)
        else:
            basename += number

        return path.parent / f'{basename}{suffix}'


    def get(self, v1, v2, other_list=None):
        rv = v1 if v1 is not None else v2

        if other_list and (rv not in other_list):
            rv = other_list[0]

        if rv == "None":
            rv = None

        return rv

    def get_scene(self): return self.get(self.scene_override, self.scene, self.scene_list)
    def get_camera(self): return self.get(self.camera_override, self.camera, self.camera_list)
    def get_resolution_x(self): return self.get(self.resolution_x_override, self.resolution_x) or 0
    def get_resolution_y(self): return self.get(self.resolution_y_override, self.resolution_y) or 0
    def get_resolution_percentage(self): return self.get(self.resolution_percentage_override, self.resolution_percentage) or 0
    def get_use_persistent_data(self): return self.get(self.use_persistent_data_override, self.use_persistent_data)
    def get_render_filepath(self): return join(self.get(self.render_filepath_override, self.render_filepath))
    def get_file_format(self): return self.get(self.file_format_override, self.file_format)
    def get_use_adaptive_sampling(self): return self.get(self.use_adaptive_sampling_override, self.use_adaptive_sampling)
    def get_samples(self): return self.get(self.samples_override, self.samples)
    def get_denoiser(self): return self.get(self.denoiser_override, self.denoiser)
    def get_denoising_use_gpu(self): return self.get(self.denoising_use_gpu_override, self.denoising_use_gpu)
    def get_denoising_input_passes(self): return self.get(self.denoising_input_passes_override, self.denoising_input_passes)
    def get_denoising_prefilter(self): return self.get(self.denoising_prefilter_override, self.denoising_prefilter)

    def get_final_resolution(self):
        """
        Get final render resolution.
        """

        x = self.get_resolution_x()
        y = self.get_resolution_y()
        perc = self.get_resolution_percentage()

        if not x or x == "None":
            x = 0

        if not y or x == "None":
            y = 0

        if not perc or perc == "None":
            perc = 0

        x = int(x)
        y = int(y)
        perc = int(perc)

        factor = perc / 100

        return int(x * factor), int(y * factor)


    def reload(self):
        """
        Reload the project data.
        """

        if not self.file_exists():
            return

        print(f'Reloading: {self.file}')

        store.preset.add_projects(self.file)


    def open_file(self):
        """
        Open project file.
        """

        if not self.file_exists():
            return

        print(f'Starting: {self.file}')

        os.startfile(self.file)


    def get_render_output_image(self):
        """
        Get render output image.
        """

        path = Path(self.get_render_filepath())
        dir = path.parent

        if not dir.exists():
            return None

        rv = None

        for local_path, _, files in dir.walk():

            for name in files:

                if not name.startswith(path.stem):
                    continue

                if not name.endswith(tuple(FORMATS.values())):
                    continue

                rv = local_path / name

        return rv


    def open_render_output_image(self):
        """
        """

        path = self.get_render_output_image()

        if not path:
            return

        open_image(path)


    def get_render_output_folder(self):
        """
        Get render output fodler.
        """

        path = Path(self.get_render_filepath())

        if not path.parent.exists():
            return None

        return path.parent


    def open_render_output_folder(self):
        """
        """

        path = self.get_render_output_folder()

        if not path:
            return

        open_folder(path)
