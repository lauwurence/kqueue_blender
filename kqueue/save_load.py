################################################################################
## Save and Load kQueue Files

from pickle import dump, load
from . import store


def save_file(data, filename, version):
    """
    Save file.
    """

    with open(filename, 'wb') as f:
        dump(version, f)
        dump(data, f)


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


