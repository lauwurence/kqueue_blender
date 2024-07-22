################################################################################
## Navigation

import subprocess

from os import getenv
from os.path import normpath, isdir, isfile, join

FILEBROWSER_PATH = join(getenv('WINDIR'), 'explorer.exe')


def open_folder(filename):
    """
    Open folder and select file if specified.
    """
    path = normpath(filename)

    if isdir(path):
        subprocess.run([FILEBROWSER_PATH, path])

    elif isfile(path):
        subprocess.run([FILEBROWSER_PATH, '/select,', path])