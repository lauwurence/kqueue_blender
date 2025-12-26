################################################################################
## Save and Load

import pickle

from pathlib import Path
from . import store

__cache = None
__persistent = None


def save_project_file(data, filename, version, backup=True):
    """
    Save project file.

    `backup` - create a backup file with a "1" suffix.
    """

    file = Path(filename)

    if backup:

        if file.exists():
            file_backup = Path(str(file) + "1")

            if file_backup.exists():
                file_backup.unlink()

            file.rename(file_backup)

    with open(file, 'wb') as f:
        pickle.dump(version, f)
        pickle.dump(data, f)


def load_project_file(filename):
    """
    Load project file.
    """

    file = Path(filename)
    version = None
    data = None

    if file.exists():

        try:
            with open(file, 'rb') as f:
                version = pickle.load(f)
                data = pickle.load(f)

        except:
            store.mw.log.emit(f'Unable to load file: {file.resolve()}')

    else:
        store.mw.log.emit(f'File does not exist: {file.resolve()}')

    return version, data


def save_cache(data):
    """
    Save cache data into file.
    """

    global __cache

    __cache = data

    __save(data, file=store.cache_file)


def load_cache(file=None):
    """
    Load cache file data.
    """

    global __cache

    if __cache:
        return __cache

    return __load(file=store.cache_file)


def save_persistent(data):
    """
    """

    global __persistent

    __persistent = data

    __save(data, file=store.persistent_file)


def load_persistent():
    """
    """

    global __persistent

    if __persistent:
        return __persistent

    return __load(file=store.persistent_file)


def __save(data, file):

    if not file.exists():
        file.parent.mkdir(parents=True, exist_ok=True)

    with open(file, 'wb') as f:
        pickle.dump(data, f)


def __load(file):

    if not file.exists():
        return {}

    with open(file, 'rb') as f:
        data = pickle.load(f)

    return data
