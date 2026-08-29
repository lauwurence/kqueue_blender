################################################################################
## Create Settings File

import json

from sys import argv
from pathlib import Path

input_file = Path(argv[1])
current_dir = input_file.parent

def main():

    if not input_file.is_dir():
        return

    json_file = input_file / "settings.json"

    if json_file.exists():
        return

    data = {
        "input_fps" : 25,
        "output_fps" : 60,
        "speed" : 1.0,
        "loop" : True,
    }

    with open(json_file, 'w') as f:
        json.dump(data, f, indent=4)


################################################################################
## Run

if __name__ == '__main__':
    main()
