################################################################################
## Save and Load projects

from pickle import dump as p_dump
from pickle import load as p_load


def save(data, filename, version):
    """
    Save project.
    """

    with open(filename, "wb") as f:
        p_dump(version, f)
        p_dump(data, f)


def load(filename):
    """
    Load project.
    """

    with open(filename, "rb") as f:
        version = p_load(f)
        data = p_load(f)

    return version, data


