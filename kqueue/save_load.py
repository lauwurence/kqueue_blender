################################################################################
## Save and Load kQueue Files

from pickle import dump, load
from json import dumps
from . import store


def load_file(filename):
    """
    Load file.
    """

    try:
        with open(filename, 'rb') as f:
            version = load(f)
            data = load(f)

    except:
        version = None
        data = None
        store.mw.log.emit(f'Unable to load file: {filename}')

    return version, data


def save_file(data, filename, version):
    """
    Save file.
    """

    with open(filename, 'wb') as f:
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
