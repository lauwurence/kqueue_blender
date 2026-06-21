################################################################################
## Convert

import os
import re
import ffmpeg
import winsound

from pathlib import Path
from math import ceil
from sys import argv

################################################################################

# Sets how efficient the compression will be. The lower the value, the better
# quality, but slower: [0-5]
CPU_USED = 5

# Threads count: [0-12] 0 - auto.
THREADS = 0 #8

# Codec: libvpx-vp8, libvpx-vp9
CV = 'libvpx-vp9'

# Pixel format: yuv420p or rgb8
PIX_FMT = 'gbrp' #'yuv420p'

# Video Convert Quality: [4-63] The lower the value, the better quality
CRF = 20

# Image Extract Quality: [2-32] The lower the value, the better quality
QV = 4

# Output video FPS and speed
FPS = 60
SPEED = 3

# Interpolate frames, create new ones in between `FPS`
# INTERPOLATE = None #2

# Resolution e.g. (1920, 1080)
RESOLUTION = None
# RESOLUTION = (1920, 1080)

# Deflicker in frames: [2-129]
DEFLICKER_SIZE = None #10

# Mode: am, gm, hm, qm, cm, pm, median
DEFLICKER_MODE = 'pm'

# Incremental save?
INCREMENTAL_SAVE = False


################################################################################
## Paths

input_file = Path(argv[1])
output_file = Path(f'{input_file.stem}.webm')

# Handle duplicates
if INCREMENTAL_SAVE:
    __n = 2

    while output_file.resolve() == input_file.resolve() or output_file.exists():

        if output_file.stat().st_size == 0:
            output_file.unlink()
            break

        output_file = Path(f'{input_file.stem}_{__n}.webm')

        __n += 1


################################################################################
## Functions

def extract_frame(input_regex, output_regex, frame=0):
    """
    Extract `frame` frame and save into separate file.
    """

    filters = []

    # Select frames
    filters.append(f'select=eq(n\\,{frame})')

    # Set resolution
    if RESOLUTION is not None:
        filters.append(f'scale={RESOLUTION[0]}:{RESOLUTION[1]}')

    params = {
        'vf': ",".join(filters),
        'q:v' : QV,
        'loglevel' : 'error',
    }

    ffInput = ffmpeg.input(str(input_regex))

    ffOutput = ffInput.output(output_regex, **params)
    ffOutput.run(overwrite_output=True)

    print(f'Frame {frame} extracted as {output_regex}!')


def run_1st_pass(input_file, params):
    """
    Run 1st pass, create log file and return params.
    """

    print("1st pass started...")

    params.update({
        'pass': 1,
        'maxrate': params['b:v'],
        'bufsize': params['b:v'] * 2,
        'f': 'null'
    })

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

    ffInput = ffmpeg.input(str(input_file))
    ffOutput = ffInput.output(str(output_file), **params)
    ffOutput.run(overwrite_output=True)

    print("2nd pass finished.")


################################################################################
## Main

def main():

    # Handle folder with frames
    if input_file.is_dir():
        filenames = list(input_file.iterdir())

        if not filenames:
            raise Exception(f'No frames in directory: {input_file.resolve()}')

        file = Path(filenames[0])
        number = re.findall(r'\d+', file.stem)[-1]
        basename = file.stem.replace(number, rf'%0{len(number)}d')
        input_regex = f'{file.parent}/{basename}{file.suffix}'
        output_regex = f'{file.parent}.jpg'

        # Rename images to make them in order
        if int(number) not in [0, 1]:
            print(f'Frames are not in order! Renaming {len(filenames)} frames...')

            for i, fn in enumerate(filenames):
                os.rename(fn, input_regex % i)

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

    print("Input:", input_file.resolve())
    print("Output:", output_file.resolve())

    # Extract first frame
    extract_frame(input_regex, output_regex=output_regex)

    # Convert to webm
    params = {
        'threads': THREADS,
        'c:v': CV,

        # yuv420p or rgb8
        'pix_fmt' : PIX_FMT,

        # sRGB Color Space.
        'color_range' : 'pc',
        'color_primaries' : 'bt709',
        'color_trc' : 'bt709',
        'colorspace' : 'bt709',

        # [0-5], 0> faster, but affects quality.
        'cpu-used' : CPU_USED,
        # [4-63], The lower the value, the better quality.
        'crf' : CRF,
        # Enable constant quality mode.
        'b:v': 0,

        # Remove metadata.
        'map_metadata' : -1,
    }

    # Add filters if needed
    filter = []

    if FPS is not None:
        filter.append(f'fps={FPS}')

    if SPEED is not None:
        filter.append(f'setpts=PTS/{SPEED}')

    if RESOLUTION is not None:
        filter.append(f'scale={RESOLUTION[0]}:{RESOLUTION[1]}')

    if DEFLICKER_SIZE and DEFLICKER_MODE:
        filter.append(f'deflicker=mode={DEFLICKER_MODE}:size={DEFLICKER_SIZE}')

    # Motion Interpolation https://trac.ffmpeg.org/wiki/How%20to%20speed%20up%20/%20slow%20down%20a%20video
    # if INTERPOLATE is not None:
    #     filter.append(f'minterpolate=fps=3')
        # filter.append(f'minterpolate={FPS * INTERPOLATE},tblend=all_mode=average,framestep=2')
        # filter.append(f'minterpolate=fps={FPS * INTERPOLATE}:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1')

    # Time Blend
    # # filter.append(f'tblend')
    # filter.append(f'tblend=all_mode=average')
    # filter.append(f'tblend=average,setpts={FPS * 0.05}')

    # Time Mix
    # filter.append(f'tmix=frames={60/FPS}')
    # filter.append(f'tmix=frames={ceil(60/FPS)}:weights=50 100 50')

    if filter:
        params.update({
            'filter:v' : ",".join(filter),
        })

    params = run_1st_pass(input_regex, params=params)
    run_2nd_pass(input_regex, output_file, params=params)

    winsound.Beep(frequency=440, duration=750)
    print("Done")


################################################################################
## Run

if __name__ == '__main__':
    main()
