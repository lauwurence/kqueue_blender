################################################################################
## Convert

import winsound
import ffmpeg
import re
import os

from pathlib import Path
from math import ceil
from sys import argv

################################################################################

# [0-5], The lower the value, the better quality, but slower.
CPU_USED = 5

# Video Convert Quality: [4-63] The lower the value, the better quality.
CRF = 20

# Image Extract Quality: [2-32] The lower the value, the better quality.
QV = 4

# Output video FPS and speed.
FPS = 48
SPEED = 1

# Interpolate frames, create new ones in between `FPS`.
# INTERPOLATE = None #2

# Resolution e.g. (1920, 1080).
RESOLUTION = None

# Deflicker [2-129] size in frames and mode [am, gm, hm, qm, cm, pm, median].
DEFLICKER_SIZE = None #10
DEFLICKER_MODE = 'pm'


################################################################################
# Paths

input_file = Path(argv[1])
output_file = Path(f'{input_file.stem}.webm')


################################################################################
# Functions

def extract_frame(input_regex, output_regex, frame=0):
    """
    Extract `frame` frame and save into separate file.
    """

    params = {
        'vf' : rf"select=eq(n\,{frame})",
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
        'c:a' : "libvorbis",
        'b:a' : 192 * 1000,
        'f' : 'webm'
    })

    ffInput = ffmpeg.input(str(input_file))
    ffOutput = ffInput.output(str(output_file), **params)
    ffOutput.run(overwrite_output=True)

    print("2nd pass finished.")


################################################################################
# Main Thread

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
        output_regex = f'{input_file.stem}.jpg'

    print("Input:", input_file.resolve())
    print("Output:", output_file.resolve())

    # Extract first frame
    extract_frame(input_regex, output_regex=output_regex)

    # Convert to webm
    params = {
        'threads': 8,
        'c:v': 'libvpx-vp9',

        # yuv420p or rgb8
        'pix_fmt' : 'yuv420p',

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
        filter.append(f'setpts=PTS/{int(SPEED)}')

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
# Run

main()
