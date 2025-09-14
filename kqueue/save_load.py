################################################################################
## Save and Load kQueue Files

from pickle import dump, load
from json import dumps
from pathlib import Path
from . import store


def load_file(filename):
    """
    Load file.
    """

    file = Path(filename)
    version = None
    data = None

    if file.exists():

        try:
            with open(file, 'rb') as f:
                version = load(f)
                data = load(f)

        except:
            store.mw.log.emit(f'Unable to load file: {file.resolve()}')

    else:
        store.mw.log.emit(f'File does not exist: {file.resolve()}')

    return version, data


def save_file(data, filename, version, backup=True):
    """
    Save file.

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
        dump(version, f)
        dump(data, f)


def load_cache(otherwise=None):
    """
    Load cache file data.
    """

    try:

        with open(store.cache_file, 'r') as f:
            data = load(f)

        return data

    except:
        return otherwise


def save_cache(data):
    """
    Save cache data into file.
    """

    with open(store.cache_file, 'w') as f:
        f.write(dumps(data, indent=4))
