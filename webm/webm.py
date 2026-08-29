################################################################################
## ffmpeg 1 pass encoder

import re
import json
import winsound
import ffmpeg

from datetime import datetime
from PIL import Image, ImageCms, ImageEnhance
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from time import time
from sys import argv


################################################################################
## Global

input_file = Path(argv[1])
current_dir = input_file.parent

PROFILE_SRGB = ImageCms.ImageCmsProfile(ImageCms.createProfile('sRGB')).tobytes()

RESAMPLE = Image.Resampling.LANCZOS

EXIF_DATA = {
    ('artist', 315): "keyclap",
    ('copyright', 33432): f"Copyright {datetime.now().year} keyclap. All Rights Reserved.",
}

PREVIEW = False


################################################################################
## Default settings

DEFAULTS = {
    'suffix': ["#android", "", "@2"],
    'cv': 'libvpx-vp9',
    'resolution': [(1920, 1080), (1920, 1080), (3840, 2160)],
    'input_fps': 48,
    'output_fps': 60,
    'speed': 1.0,
    'pix_fmt': 'yuv420p',
    'loop': True,
    'reverse': False,
    'interpolate': 4,
    'cpu_used': 2,
    'threads': 0,#[4, 8, 12],
    'row_mt': [1, 1, 1],
    'tile_columns': [1, 2, 2],
    'tile_rows': [0, 0, 1],
    'crf': [35, 20, 10],
    'qv': [4, 2, 2],
    'image_quality': [75, 90, 95],
    'sharpen': [0.25, 0.25, 0.0],
}

if PREVIEW:
    DEFAULTS |= {
        'interpolate' : 1,
        'cpu_used': 8,
        'threads': 0,
        'row_mt': 1,
        'tile_columns': 2,
        'tile_rows': 1,
        'crf': 35,
    }


################################################################################
## Interpolation presets

MINTERPOLATE = {

    # Blend соседних кадров.
    # Быстро, но появляется ghosting / motion blur.
    1 : 'minterpolate=fps={}:mi_mode=blend',

    # MCI с параметрами FFmpeg по умолчанию.
    2 : 'minterpolate=fps={}',

    # MCI + Adaptive Overlapped Block Motion Compensation.
    # Bilateral motion estimation.
    3:  'minterpolate='
        'fps={}:'
        'mi_mode=mci:'
        'mc_mode=aobmc:'
        'me_mode=bilat',

    # То же самое, но bidirectional motion estimation.
    4 : 'minterpolate='
        'fps={}:'
        'mi_mode=mci:'
        'mc_mode=aobmc:'
        'me_mode=bidir',

    # Bidirectional + variable-size blocks.
    5 : 'minterpolate='
        'fps={}:'
        'mi_mode=mci:'
        'mc_mode=aobmc:'
        'me_mode=bidir:'
        'vsbmc=1',

    # То же самое + scene change detection.
    6 : 'minterpolate='
        'fps={}:'
        'mi_mode=mci:'
        'mc_mode=aobmc:'
        'me_mode=bidir:'
        'vsbmc=1:'
        'scd=fdiff',
}


################################################################################
## Functions

def ffmpeg_input(file):
    """
    Create FFmpeg input.

    For concat demuxer, `file` is a normal text file containing
    file/duration entries.
    """

    if isinstance(file, Path):
        file = str(file)

    return ffmpeg.input(file)


def extract_frame(file, output_file, frame=0, resolution=None, qv=2, sharpen=None):
    """
    Extract one frame and save it as a separate image.
    """

    print("Output:", output_file.resolve())

    output_file.unlink(missing_ok=True)

    filters = [ f'select=eq(n\\,{frame})' ]

    if resolution is not None:
        filters.append( f'scale={resolution[0]}:{resolution[1]}' )

    if sharpen:
        filters.append(
            'unsharp='
            f'luma_msize_x=3:'
            f'luma_msize_y=3:'
            f'luma_amount={sharpen}'
        )

    params = {
        'q:v': qv,
        'loglevel': 'error',
        'vf': ','.join(filters),
        'frames:v': 1,
    }

    ff_input = ffmpeg.input(str(file))

    ff_output = ff_input.output(str(output_file), **params)
    ff_output.run(overwrite_output=True)

    print(f"Frame {frame} extracted: {output_file}")


def save_image(file, output_file, resolution=None, quality=100, sharpen=None):
    """
    Save first frame as JPEG preview.
    """

    with Image.open(file) as img:

        if resolution is None:
            width = img.width
            height = img.height
        else:
            width, height = resolution

        if sharpen is not None:
            enhancer = ImageEnhance.Sharpness(img)
            img = enhancer.enhance(sharpen * 10)

        img.thumbnail((width, height), resample=RESAMPLE)

        icc_profile = img.info.get('icc_profile', PROFILE_SRGB)

        exif = img.getexif()

        for (label, index), value in EXIF_DATA.items():
            exif[index] = value

        rgb_img = img.convert('RGB')

        rgb_img.save(
            output_file,
            format='JPEG',
            quality=int(quality),
            compression='jpeg',
            icc_profile=icc_profile,
            exif=exif)

    print(f"Image saved: {output_file}")


def get_sorted_images(folder_path):
    """
    Get supported images and sort them naturally.
    """

    extensions = {'.jpg', '.jpeg', '.png', '.webp'}

    images = [ file for file in folder_path.iterdir() if file.is_file() and file.suffix.lower() in extensions ]

    def natural_sort(path):
        numbers = re.findall(r'\d+', path.stem)

        if numbers:
            return int(numbers[-1])

        return path.stem

    images.sort(key=natural_sort)

    return images


def create_concat_file(images, list_file, frame_duration):
    """
    Create FFmpeg concat demuxer file.

    The last image is repeated because concat demuxer needs
    the final file entry to establish the previous duration correctly.
    """

    with open(list_file, 'w', encoding='utf-8') as f:

        for image in images:
            path = image.resolve().as_posix()

            f.write(f"file '{path}'\n")
            f.write(f"duration {frame_duration:.12f}\n")

        if images:
            path = images[-1].resolve().as_posix()
            f.write(f"file '{path}'\n")


def build_filters(effective_fps, output_fps, interpolate, resolution, sharpen):
    """
    Build video filter chain.
    """

    step_1 = []
    step_2 = []
    step_3 = []

    # -------------------------------------------------------------------------
    # Filters
    # -------------------------------------------------------------------------

    if effective_fps < output_fps:

        if interpolate == 0:
            step_1.append(f'fps={effective_fps:g}')

        elif interpolate in MINTERPOLATE:
            step_1.append(MINTERPOLATE[interpolate].format(output_fps))

        else:
            raise ValueError(f'Unknown interpolation: {interpolate}')

    else:
        step_1.append(f'fps={output_fps:g}')

    # -------------------------------------------------------------------------
    # Spatial processing
    # -------------------------------------------------------------------------

    if resolution is not None:

        step_2.append(
            'scale='
            f'{resolution[0]}:'
            f'{resolution[1]}:'
            'flags=lanczos:'
            'param0=4'
        )

    # -------------------------------------------------------------------------
    # Sharpen
    # -------------------------------------------------------------------------

    if sharpen:

        step_3.append(
            'unsharp='
            'luma_msize_x=3:'
            'luma_msize_y=3:'
            f'luma_amount={sharpen}'
        )

    if PREVIEW:
        return step_2 + step_1 + step_3

    return step_1 + step_2 + step_3


################################################################################
## Convert

def convert(
    file,
    name,
    suffix="",
    incremental_save=False,
    cpu_used=6,
    input_fps=48,
    output_fps=60,
    speed=1.0,
    cv='libvpx-vp9',
    pix_fmt='yuv420p',
    resolution=None,
    threads=0,
    row_mt=1,
    tile_columns=1,
    tile_rows=0,
    crf=30,
    qv=2,
    image_quality=90,
    sharpen=0.25,
    interpolate=0,
    loop=False,
    reverse=False,
    i=None):

    """
    Convert a video or image sequence to WebM.

    Main processing:

        input
          ↓
        temporal FPS processing
          ↓
        scaling
          ↓
        sharpening
          ↓
        VP9
          ↓
        WebM

    `speed` changes the effective input FPS:

        effective_fps = input_fps * speed

    If effective_fps < output_fps:
        interpolation may create intermediate frames.

    If effective_fps >= output_fps:
        frames are simply selected/downsampled.

    CRF + b:v=0 is used in one-pass constant-quality mode.
    """

    start_time = time()

    if not isinstance(file, Path):
        file = Path(file)

    # -------------------------------------------------------------------------
    # Validate
    # -------------------------------------------------------------------------

    if input_fps <= 0:
        raise ValueError(f'input_fps must be > 0: {input_fps}')

    if output_fps <= 0:
        raise ValueError(f'output_fps must be > 0: {output_fps}')

    if speed <= 0:
        raise ValueError(f'speed must be > 0: {speed}')

    if file.is_dir():
        images = get_sorted_images(file)

        if not images:
            raise ValueError(f'No supported images found in: {file.resolve()}')

    elif not file.exists():
        raise FileNotFoundError(f'Input file does not exist: {file.resolve()}')

    # -------------------------------------------------------------------------
    # Output names
    # -------------------------------------------------------------------------

    if reverse:
        name += "_reverse"

    output_file = current_dir / f'{name}{suffix}.webm'
    output_frame = current_dir / f'{name}{suffix}.jpg'

    # -------------------------------------------------------------------------
    # Incremental save
    # -------------------------------------------------------------------------

    if incremental_save:
        counter = 2

        while output_file.exists() or output_file.resolve() == file.resolve():

            if output_file.exists():
                if output_file.stat().st_size == 0:
                    output_file.unlink()
                    break

            output_file = current_dir / f'{name}{suffix}_{counter}.webm'
            counter += 1

    # -------------------------------------------------------------------------
    # Prepare input
    # -------------------------------------------------------------------------

    temporary_files = []

    try:

        if file.is_dir():

            effective_fps = input_fps * speed
            frame_duration = 1.0 / effective_fps
            list_file = file / f'{name}_{i if i is not None else "concat"}.txt'

            temporary_files.append(list_file)

            # -----------------------------------------------------------------
            # Image sequence
            # -----------------------------------------------------------------

            images = get_sorted_images(file)

            if not images:
                raise ValueError(f'No images found in: {file.resolve()}')

            if loop and interpolate != 0 and (effective_fps < output_fps):
                first_frame = images[0]
                last_frame = images[-1]
                images = images + [first_frame]

            if reverse:
                images.reverse()

            create_concat_file(
                images,
                list_file,
                frame_duration,
            )

            ff_input = ffmpeg.input(str(list_file), format='concat', safe=0)

            # -----------------------------------------------------------------
            # Preview
            # -----------------------------------------------------------------

            # Use the first REAL frame for preview, not the technical
            # loop frame inserted for interpolation.

            preview_frame = images[1] if loop and interpolate != 0 else images[0]

            save_image(
                preview_frame,
                output_frame,
                resolution=resolution,
                quality=image_quality,
                sharpen=sharpen,
            )

        else:

            # -----------------------------------------------------------------
            # Video input
            # -----------------------------------------------------------------

            ff_input = ffmpeg.input(str(file))

            extract_frame(
                file,
                output_frame,
                frame=0,
                resolution=resolution,
                qv=qv,
                sharpen=sharpen,
            )

            effective_fps = input_fps * speed

        # ---------------------------------------------------------------------
        # Build filters
        # ---------------------------------------------------------------------

        filters = build_filters(
            effective_fps=effective_fps,
            output_fps=output_fps,
            interpolate=interpolate,
            resolution=resolution,
            sharpen=sharpen,
        )

        # ---------------------------------------------------------------------
        # VP9 parameters
        # ---------------------------------------------------------------------

        params = {

            # -------------------------------------------------------------
            # Codec
            # -------------------------------------------------------------

            'c:v' : cv,
            'pix_fmt' : pix_fmt,

            # -------------------------------------------------------------
            # VP9 threading / tiling
            # -------------------------------------------------------------

            'threads' : threads,
            'row-mt' : row_mt,

            'tile-columns' : tile_columns,
            'tile-rows' : tile_rows,

            # Explicitly enable frame-parallel decoding metadata.
            'frame-parallel' : 1,

            # -------------------------------------------------------------
            # Encoding speed
            # -------------------------------------------------------------

            'cpu-used' : cpu_used,

            # -------------------------------------------------------------
            # Constant quality
            # -------------------------------------------------------------

            'crf' : max(0, min(63, crf)),

            # Required for libvpx-vp9 CRF mode.
            'b:v' : 0,

            # -------------------------------------------------------------
            # Color
            # -------------------------------------------------------------

            'color_range' : 'pc',
            'color_primaries' : 'bt709',
            'color_trc' : 'bt709',
            'colorspace' : 'bt709',

            # -------------------------------------------------------------
            # Metadata
            # -------------------------------------------------------------

            'map_metadata' : -1,

            # -------------------------------------------------------------
            # Filter chain
            # -------------------------------------------------------------

            'filter:v' : ','.join(filters),

            # -------------------------------------------------------------
            # WebM
            # -------------------------------------------------------------

            'f' : 'webm',

            # 'loglevel' : 'error',
        }

        # Сохранить аудио
        if file.is_dir():
            params['an'] = None

        else:
            params.update({
                'c:a': 'libvorbis',
                'b:a': 192 * 1000,
            })

        # One-pass encoding
        print()
        print(f"Encoding: {'PREVIEW' if PREVIEW else 'FINAL'}")
        print("  Input FPS:     ", input_fps)
        print("  Speed:         ", speed)
        print("  Effective FPS: ", effective_fps)
        print("  Output FPS:    ", output_fps)
        print("  Interpolate:   ", interpolate)
        print("  Resolution:    ", resolution)
        print("  CPU used:      ", cpu_used)
        print("  Threads:       ", threads)
        print("  Tile columns:  ", tile_columns)
        print("  Tile rows:     ", tile_rows)
        print("  CRF:           ", crf)
        print()

        ff_output = ff_input.output(str(output_file), **params)
        ff_output.run(overwrite_output=True)

        print()
        print(
            f'Converted in '
            f'{time() - start_time:.02f}s: '
            f'{output_file.resolve()}'
        )

        winsound.Beep(frequency=240, duration=250)

        return str(output_file)

    # Delete temporary files
    finally:
        for temp_file in temporary_files:
            try:
                Path(temp_file).unlink(missing_ok=True)
            except Exception as e:
                print(f'Warning: cannot delete {temp_file}: {e}')


################################################################################
## Main

def main():

    json_file = input_file / "data.json"
    preset = argv[2]
    params = DEFAULTS.copy()

    print(f'Input: {input_file.resolve()}')

    # -------------------------------------------------------------------------
    # JSON settings
    # -------------------------------------------------------------------------

    if input_file.is_dir() and json_file.exists():
        print(f'Settings: {json_file.resolve()}')

        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        for name in params:
            if name in data:
                params[name] = data[name]

    else:
        print(f'Settings file not found: {json_file.resolve()}')

    # -------------------------------------------------------------------------
    # Normalize preset arrays
    # -------------------------------------------------------------------------

    for name in params:

        if not isinstance(params[name], list):
            params[name] = [ params[name] ] * 3

    # -------------------------------------------------------------------------
    # Create tasks
    # -------------------------------------------------------------------------

    tasks = {}

    if preset in ['android', 'all']:
        tasks[0] = {
            'file': input_file,
            'name': input_file.stem,
        } | { key: value[0] for key, value in params.items() }

    if preset in ['1080p', 'all']:
        tasks[1] = {
            'file': input_file,
            'name': input_file.stem,
        } | { key: value[1] for key, value in params.items() }

    if preset in ['4K', '2160p', 'all']:
        tasks[2] = {
            'file': input_file,
            'name': input_file.stem,
        } | { key: value[2] for key, value in params.items() }

    if not tasks:
        raise ValueError(f'Unknown preset: {preset}')

    # -------------------------------------------------------------------------
    # Execute
    # -------------------------------------------------------------------------

    # minterpolate + VP9 are both CPU-heavy.
    #
    # Running several encoders simultaneously can actually make the total
    # conversion slower because they compete for CPU/cache/memory bandwidth.
    #
    # Change to 2 if benchmarking shows that it is beneficial on your CPU.

    max_workers = min(1, len(tasks))

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = [ executor.submit(convert, i=i, **task) for i, task in tasks.items() ]

        for future in as_completed(futures):
            try:
                print(future.result() or "")
            except Exception as e:
                print(f'Conversion failed: {e}')
                raise


################################################################################
## Run

if __name__ == '__main__':
    main()
