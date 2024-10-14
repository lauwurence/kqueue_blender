################################################################################
## Path Utils

import subprocess

from os import getenv
from os.path import join as os_path_join
from os.path import normpath, isdir, isfile


def join(*args):
    """
    """
    return normpath(os_path_join(*args).replace("\\", "/"))


FILEBROWSER_PATH = join(getenv('WINDIR'), 'explorer.exe')


def open_folder(filename):
    """
    Open folder and select file if specified.
    """

    if not filename:
        return

    path = normpath(filename)

    if isdir(path):
        subprocess.run([FILEBROWSER_PATH, path])

    elif isfile(path):
        subprocess.run([FILEBROWSER_PATH, '/select,', path])