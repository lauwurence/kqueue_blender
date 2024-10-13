################################################################################
## Path Utils

from os.path import join as os_path_join
from os.path import normpath


def join(*args):
    """
    """
    return normpath(os_path_join(*args).replace("\\", "/"))