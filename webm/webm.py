################################################################################
## Convert

import re
import json
import ffmpeg
import winsound

from PIL import Image, ImageCms, ImageEnhance
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from time import time
from sys import argv

input_file = Path(argv[1])
current_dir = input_file.parent

PROFILE_SRGB = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
RESAMPLE = Image.Resampling.LANCZOS

EXIF_DATA = {
    ('artist', 315) : "keyclap",
    ('copyright', 33432) : "Copyright 2026 keyclap. All Rights Reserved.",
}

################################################################################
## Functions

def extract_frame(file, output_file, frame=0, resolution=None, qv=2, sharpen=None):
    """
    Extract `frame` frame and save into separate file.
    """

    print("Output:", output_file.resolve())

    if output_file.exists():
        output_file.unlink()

    filters = []

    filters.append(f'select=eq(n\\,{frame})')

    if resolution is not None:
        filters.append(f'scale={resolution[0]}:{resolution[1]}')

    if sharpen:
        filters.append(f'unsharp=luma_msize_x=3:luma_msize_y=3:luma_amount={sharpen}')

    params = {
        'q:v' : qv,
        'loglevel' : 'error',
        'vf': ",".join(filters),
    }

    if isinstance(file, str) and file.startswith('concat:'):
        ffInput = ffmpeg.input(str(file), format='concat', safe=0)
    else:
        ffInput = ffmpeg.input(str(file))

    ffOutput = ffInput.output(str(output_file), **params)
    ffOutput.run(overwrite_output=True)

    print(f'Frame {frame} extracted: {output_file}')


def save_image(file, output_file, resolution=None, quality=100, sharpen=None):

    with Image.open(file) as img:

        if resolution is None:
            width = img.width
            height = img.height
        else:
            width = resolution[0]
            height = resolution[1]

        if sharpen is not None:
            enhancer = ImageEnhance.Sharpness(img)
            img = enhancer.enhance(sharpen * 10)

        img.thumbnail((width, height), resample=RESAMPLE)
        icc_profile = img.info.get('icc_profile', PROFILE_SRGB)
        exif = img.getexif()

        # Edit EXIF info
        for (label, index), value in EXIF_DATA.items():
            exif[index] = value

        # Convert from ARGB to RGB
        rgb_img = img.convert('RGB')
        compression = 'jpeg'

        rgb_img.save(output_file,
                     format='JPEG',
                     quality=int(quality),
                     compression=compression,
                     icc_profile=icc_profile,
                     exif=exif)

    print(f'Image saved: {output_file}')


def run_1st_pass(file, params):
    """
    Run 1st pass, create log file and return params.
    """

    print("1st pass started...")

    params.update({
        'pass': 1,
        'f': 'null'
    })

    if isinstance(file, str) and file.startswith('concat:'):
        ffInput = ffmpeg.input(str(file), format='concat', safe=0)
    else:
        ffInput = ffmpeg.input(str(file))

    ffOutput = ffInput.output('pipe:', **params)
    ffOutput.run(overwrite_output=True)

    print("1st pass finished!")

    return params


def run_2nd_pass(file, output_file, params):
    """
    Run 2nd pass and create output file.
    """

    print("2nd pass started.")

    params.update({
        'pass': 2,
        'c:a' : 'libvorbis',
        'b:a' : 192 * 1000,
        'f' : 'webm'
    })

    if isinstance(file, str) and file.startswith('concat:'):
        ffInput = ffmpeg.input(str(file), format='concat', safe=0)
    else:
        ffInput = ffmpeg.input(str(file))

    ffOutput = ffInput.output(str(output_file), **params)
    ffOutput.run(overwrite_output=True)

    print("2nd pass finished.")


def get_sorted_images(folder_path):
    """
    Get all images from folder and sort them naturally.
    """

    ext = ('.jpg', '.jpeg', '.png', '.webp')
    rv = []

    for file in folder_path.iterdir():

        if not file.is_file():
            continue

        if file.suffix.lower() not in ext:
            continue

        rv.append(file)

    def natural_sort(path):
        stem = path.stem
        numbers = re.findall(r'\d+', stem)

        if numbers:
            return int(numbers[-1])

        return stem

    rv.sort(key=natural_sort)

    return rv


def get_frame_count(file):
    """
    Get frame count from file.
    """

    probe = ffmpeg.probe(
        str(file),
        v='error',
        count_frames=None,
        select_streams='v:0',
        show_entries='stream=nb_read_frames'
    )

    if probe and 'streams' in probe and probe['streams']:
        nb_frames = probe['streams'][0].get('nb_read_frames')

        if nb_frames:
            return int(nb_frames)

    return None


################################################################################
## Convert

def convert(
        file,
        name,
        suffix="",
        incremental_save=False,
        cpu_used=5,
        input_fps=25,
        output_fps=60,
        speed=2,
        cv='libvpx-vp9',
        pix_fmt='gbrp',
        resolution=None,
        threads=0,
        crf=30,
        qv=2,
        image_quality=90,
        sharpen=0.25,
        interpolate_mode=1,
        loop=False,
        reverse=False,
        i=None,
        ):
    """
    Covert video or a frames folder into .webm.

    Fields:
        `suffix` - Output filename suffix.
        `incremental_save` - Incremental save.
        `cpu_used` - [0-5] - Sets how efficient the compression will be. The lower the value, the better
        quality, but slower. 4 or 5 is for Ren'Py, программный декодинг зависит от этого.
        `crf` - [4-63] - Video Convert Quality.  The lower the value, the better quality.
        `threads` - [0-...] - Threads count. 0 - auto. The lower the threads count, the better quality.
        `cv` - Codec: 'libvpx-vp8', 'libvpx-vp9'.
        `pix_fmt` - Pixel format. 'yuv420p' or 'rgb8'.
        `qv` - [2-32] - Image Extract Quality. The lower the value, the better quality.
        `image_quality` - [0-100] - Image save quality.
        `input_fps` - Input FPS. Default for ffmpeg is 25.
        `output_fps` - Output FPS. Default for Ren'Py is 60.
        `speed` - Video speed.
        `sharpen` - Sharpen filter.
        `interpolate_mode` - Frame interpolation quality.
        `loop` - Place first frame at the end and last frame at the start.

    """

    s = time()

    if reverse:
        name += "_reverse"

    # Temp files to delete later
    _temp_files = []

    # Input and output
    if not isinstance(file, Path):
        file = Path(file)

    output_file = current_dir / f'{name}{suffix}.webm'
    output_frame = current_dir / f'{name}{suffix}.jpg'

    # Handle duplicates
    if incremental_save:
        __n = 2

        while output_file.exists() or (output_file.resolve() == file.resolve()):

            if output_file.stat().st_size == 0:
                output_file.unlink()
                break

            output_file = current_dir / f'{name}{suffix}_{__n}.webm'

            __n += 1

    # Handle folder with frames
    if file.is_dir():
        filenames = list(file.iterdir())

        if not filenames:
            raise Exception(f'No images found in directory: {file.resolve()}')

        sorted_images = get_sorted_images(file)

        if loop:
            first_frame = sorted_images[0]
            last_frame = sorted_images[-1]
            sorted_images.insert(0, last_frame)
            sorted_images.append(first_frame)

        if reverse:
            sorted_images.reverse()

        # Create a temporary file list for ffmpeg concat
        list_file = file / f"{i}.txt"
        _temp_files.append(list_file)

        with open(list_file, 'w') as f:

            for img in sorted_images:
                f.write(f"file '{img.absolute()}'\n")
                f.write(f"duration {1.0 / input_fps / speed}\n")

        # Use concat demuxer for image sequence
        file = f'concat:{list_file}'

        # Save image
        save_image(sorted_images[0],
                   output_frame,
                   resolution=resolution,
                   quality=image_quality,
                   sharpen=sharpen)

    # Handle video file
    else:

        if not file.exists():
            raise Exception(f'Input file does not exist: {file.resolve()}')

        # Extract first frame
        extract_frame(file,
                      output_frame,
                      resolution=resolution,
                      qv=qv,
                      sharpen=sharpen)

    # Default
    params = {
        'threads' : threads,

        # Codec: libvpx-vp9, libvpx-vp8, libx264, libx265, libaom-av1
        'c:v' : cv,

        # yuv420p or rgb8
        'pix_fmt' : pix_fmt,

        # sRGB Color Space.
        'color_range' : 'pc',
        'color_primaries' : 'bt709',
        'color_trc' : 'bt709',
        'colorspace' : 'bt709',

        # [0-5], 0> faster, but affects quality.
        'cpu-used' : cpu_used,

        # [4-63], The lower the value, the better quality.
        'crf' : max(0, min(63, crf)),

        # Enable constant quality mode.
        'b:v' : 0,

        # Not needed for Ren'Py
        'maxrate' : 0,
        'bufsize' : 0,

        'frame-parallel' : 1,

        # Remove metadata.
        'map_metadata' : -1,
    }

    if i is not None:
        passlogfile = f'{name}-{i}'
        params.update({'passlogfile' : passlogfile})
        log_file = current_dir / f'{passlogfile}-0.log'
        log_file.unlink(missing_ok=True)
        _temp_files.append(log_file)

    # Apply filters
    filters = []

    # Размер
    if resolution:
        filters.append(f'scale={resolution[0]}:{resolution[1]}:flags=lanczos:param0=4')

    # Резкость
    if sharpen:
        filters.append(f'unsharp=luma_msize_x=3:luma_msize_y=3:luma_amount={sharpen}')

    # Быстрый (просто дублирует кадры)
    if interpolate_mode == 1:
        filters.append(f'minterpolate=fps={output_fps}:mi_mode=dup')

    # Средний (усредняет соседние кадры) (очень плохой результат)
    elif interpolate_mode == 2:
        filters.append(f'minterpolate=fps={output_fps}:mi_mode=blend')

    # Качественный (анализирует движение объектов и создаёт вектор) (очень хороший результат)
    elif interpolate_mode == 3:
        filters.append(f'minterpolate=fps={output_fps}:mi_mode=mci:mc_mode=aobmc')

    # Медленнее x3 (1080p) x12 (2160p) (разбивает на блоки разного размера)
    elif interpolate_mode == 4:
        filters.append(f'minterpolate=fps={output_fps}:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1')

    # if SPEED is not None:
    #     filters.append(f'setpts=PTS/{SPEED}')

    # Combine filters
    if filters:
        params.update({
            'filter:v' : ",".join(filters),
        })

    # Run in 2 pass
    params = run_1st_pass(file, params=params)
    run_2nd_pass(file, output_file, params=params)

    # Delete temporary files
    for f in _temp_files:

        if not isinstance(f, Path):
            f = Path(f)

        f.unlink(missing_ok=True)

    print(f'Converted in {time() - s:.02f}s: {output_file.resolve()}')


################################################################################
## Main

DEFAULTS = {
        'suffix' : ["#android", "", "@2"],
        'cv' : 'libvpx-vp9',
        'resolution' : [(1920, 1080), (1920, 1080), (3840, 2160)],
        'input_fps' : 25,
        'output_fps' : 60,
        'speed' : 1.0,
        'pix_fmt' : 'yuv420p', #gbrp
        'loop' : True,
        'reverse' : False,
        'interpolate_mode' : [3, 3, 3],
        'cpu_used' : 4,
        'threads' : 8,#4,
        'crf' : [40, 30, 25],
        'qv' : [4, 2, 2],
        'image_quality' : [75, 90, 95],
        'sharpen' : [0.25, 0.25, 0.0],
    }

def main():
    json_file = input_file / "data.json"
    preset = argv[2]
    tasks = {}
    params = DEFAULTS.copy()

    print(f'Input: {input_file.resolve()}')

    if json_file.exists():
        print(f'Settings: {json_file.resolve()}')

        with open(json_file, 'r') as f:
            data = json.load(f)

        for name in params.keys():

            if name not in data:
                continue

            params[name] = data[name]

    else:
        print(f'Settings file not found: {json_file.resolve()}')

    for name in params.keys():

        if not isinstance(params[name], list):
            params[name] = [ params[name] ] * 3

    if preset in ['android', 'all']:
        tasks[0] = {
            'file' : input_file,
            'name' : input_file.stem,
        } | { k : v[0] for k, v in params.items() }

    if preset in ['1080p', 'all']:
        tasks[1] = {
            'file' : input_file,
            'name' : input_file.stem,
        } | { k : v[1] for k, v in params.items() }

    if preset in ['4K', '2160p', 'all']:
        tasks[2] = {
            'file' : input_file,
            'name' : input_file.stem,
        } | { k : v[2] for k, v in params.items() }

    with ProcessPoolExecutor(max_workers=len(tasks)) as executor:
        futures = [ executor.submit(convert, i=i, **task) for i, task in tasks.items() ]

        for future in as_completed(futures):
            print(future.result() or "")

    winsound.Beep(frequency=240, duration=250)


################################################################################
## Run

if __name__ == '__main__':
    main()
