################################################################################
## Path Utils

import subprocess
import webbrowser
import threading

from pathlib import Path
from os import getenv
from os.path import join as os_path_join
from os.path import normpath, isdir, isfile


def join(*args):
    """
    """
    return normpath(os_path_join(*args).replace("\\", "/"))


def exists(filename):
    """
    """

    return Path(filename).exists()


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


def open_image(filename):
    """
    """

    def do_open_image():
        webbrowser.open(filename)

    t = threading.Thread(target=do_open_image)
    t.start()
