################################################################################
## Convert

import re
import ffmpeg
import winsound

from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from time import time
from sys import argv

current_dir = Path.cwd()


################################################################################
## Functions

def extract_frame(input_file, output_file, frame=0, resolution=None, qv=2, sharpen=None):
    """
    Extract `frame` frame and save into separate file.
    """

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

    if isinstance(input_file, str) and input_file.startswith('concat:'):
        ffInput = ffmpeg.input(str(input_file), format='concat', safe=0)
    else:
        ffInput = ffmpeg.input(str(input_file))

    ffOutput = ffInput.output(output_file, **params)
    ffOutput.run(overwrite_output=True)

    print(f'Frame {frame} extracted: {output_file}')


def run_1st_pass(input_file, params):
    """
    Run 1st pass, create log file and return params.
    """

    print("1st pass started...")

    params.update({
        'pass': 1,
        'f': 'null'
    })

    if isinstance(input_file, str) and input_file.startswith('concat:'):
        ffInput = ffmpeg.input(str(input_file), format='concat', safe=0)
    else:
        ffInput = ffmpeg.input(str(input_file))

    ffOutput = ffInput.output('pipe:', **params)
    ffOutput.run(overwrite_output=True)

    print("1st pass finished!")

    return params


def run_2nd_pass(input_file, output_file, params):
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

    if isinstance(input_file, str) and input_file.startswith('concat:'):
        ffInput = ffmpeg.input(str(input_file), format='concat', safe=0)
    else:
        ffInput = ffmpeg.input(str(input_file))

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


################################################################################
## Convert

def convert(
        input_file,
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
        sharpen=0.25,
        interpolate_mode=1,
        i=None
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
        `input_fps` - Input FPS. Default for ffmpeg is 25.
        `output_fps` - Output FPS. Default for Ren'Py is 60.
        `speed` - Video speed.
        `sharpen` - Sharpen filter.
        `interpolate_mode` - Frame interpolation quality.

    """

    s = time()

    # Temp files to delete later
    _temp_files = []

    # Input and output
    if not isinstance(input_file, Path):
        input_file = Path(input_file)

    output_file = Path(f'{input_file.stem}{suffix}.webm')

    # Handle duplicates
    if incremental_save:
        __n = 2

        while output_file.resolve() == input_file.resolve() or output_file.exists():

            if output_file.stat().st_size == 0:
                output_file.unlink()
                break

            output_file = Path(f'{input_file.stem}{suffix}_{__n}.webm')

            __n += 1

    # Handle folder with frames
    if input_file.is_dir():
        filenames = list(input_file.iterdir())

        if not filenames:
            raise Exception(f'No images found in directory: {input_file.resolve()}')

        first_file = Path(filenames[0])
        output_regex = f'{first_file.parent}{suffix}.jpg'

        sorted_images = get_sorted_images(input_file)

        # Create a temporary file list for ffmpeg concat
        list_file = input_file / f"{i}.txt"
        _temp_files.append(list_file)

        with open(list_file, 'w') as f:

            for img in sorted_images:
                f.write(f"file '{img.absolute()}'\n")
                f.write(f"duration {1.0 / input_fps / speed}\n")

        # Use concat demuxer for image sequence
        input_regex = f'concat:{list_file}'

    # Handle video file
    else:

        if not input_file.exists():
            raise Exception(f'Input file "{input_file.resolve()}" does not exist.')

        input_regex = input_file
        output_regex = f'{output_file.stem}.jpg'

    # Remove old image
    output_frame = Path(output_regex)

    if output_frame.exists():
        output_frame.unlink()

    print("Output:", output_file.resolve())

    # Extract first frame
    extract_frame(input_regex,
                  output_regex,
                  resolution=resolution,
                  qv=qv,
                  sharpen=sharpen)

    # Default
    params = {
        'threads': threads,

        # Codec: libvpx-vp9, libvpx-vp8, libx264, libx265, libaom-av1
        'c:v': cv,

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
        'b:v': 0,

        # Not needed for Ren'Py
        'maxrate': 0,
        'bufsize': 0,

        # Remove metadata.
        'map_metadata' : -1,
    }

    if i is not None:
        passlogfile = f'{input_file.stem}-{i}'
        params.update({'passlogfile' : passlogfile})
        log_file = current_dir / f'{passlogfile}-0.log'
        log_file.unlink(missing_ok=True)
        _temp_files.append(log_file)

    # Apply filters
    filters = []

    if resolution:
        filters.append(f'scale={resolution[0]}:{resolution[1]}:flags=lanczos:param0=4')

    if sharpen:
        filters.append(f'unsharp=luma_msize_x=3:luma_msize_y=3:luma_amount={sharpen}')

    # Быстрый (просто дублирует кадры)
    if interpolate_mode == 1:
        filters.append(f'minterpolate=fps={output_fps}:mi_mode=dup')

    # Средний (усредняет соседние кадры)
    elif interpolate_mode == 2:
        filters.append(f'minterpolate=fps={output_fps}:mi_mode=blend')

    # Качественный (анализирует движение объектов и создаёт вектор)
    elif interpolate_mode == 3:
        filters.append(f'minterpolate=fps={output_fps}:mi_mode=mci:mc_mode=aobmc')

    # Медленнее x3 (1080p) x12 (2160p) (разбивает на блоки разного размера)
    elif interpolate_mode == 4:
        filters.append(f'minterpolate=fps={output_fps}:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1')

    # if SPEED is not None:
    #     filters.append(f'setpts=PTS/{SPEED}')

    if filters:
        params.update({
            'filter:v' : ",".join(filters),
        })

    # Run in 2 pass
    params = run_1st_pass(input_regex, params=params)
    run_2nd_pass(input_regex, output_file, params=params)

    # Delete temporary files
    for f in _temp_files:

        if not isinstance(f, Path):
            f = Path(f)

        f.unlink(missing_ok=True)

    print(f'Converted in {time() - s:.02f}s: {output_file.resolve()}')


################################################################################
## Main

def main():
    input_file = Path(argv[1])
    preset = argv[2]
    tasks = []

    print("Input:", input_file.resolve())

    if preset in ['android', 'all']:
        tasks.append({
            'input_file' : input_file,
            'suffix' : "#android",
            'resolution' : (1920, 1080),
            'cpu_used' : 5,
            'input_fps' : 25,
            'output_fps' : 60,
            'speed' : 2,
            'cv' : 'libvpx-vp9',
            'pix_fmt' : 'gbrp',
            'threads' : 4,
            'crf' : 45,
            'qv' : 4,
            'sharpen' : 0.25,
            'interpolate_mode' : 1,
        })

    if preset in ['1080p', 'all']:
        tasks.append({
            'input_file' : input_file,
            'suffix' : "",
            'resolution' : (1920, 1080),
            'cpu_used' : 5,
            'input_fps' : 25,
            'output_fps' : 60,
            'speed' : 2,
            'cv' : 'libvpx-vp9',
            'pix_fmt' : 'gbrp',
            'threads' : 4,
            'crf' : 35,
            'qv' : 2,
            'sharpen' : 0.25,
            'interpolate_mode' : 1,
        })

    if preset in ['4K', '2160p', 'all']:
        tasks.append({
            'input_file' : input_file,
            'suffix' : "@2",
            'resolution' : (3840, 2160),
            'cpu_used' : 5,
            'input_fps' : 25,
            'output_fps' : 60,
            'speed' : 2,
            'cv' : 'libvpx-vp9',
            'pix_fmt' : 'gbrp',
            'threads' : 4,
            'crf' : 30,
            'qv' : 2,
            'sharpen' : 0,
            'interpolate_mode' : 1,
        })

    with ProcessPoolExecutor(max_workers=3) as executor:
        futures = [ executor.submit(convert, i=i, **task) for i, task in enumerate(tasks) ]

        for future in as_completed(futures):
            print(future.result() or "")

    winsound.Beep(frequency=440, duration=750)


################################################################################
## Run

if __name__ == '__main__':
    main()
