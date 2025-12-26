################################################################################
## Utils

import psutil


def is_laptop_psutil():
    """
    Is it laptop? Check battery existence.
    """

    try:
        battery = psutil.sensors_battery()

        if battery is not None:
            return True

        import platform

        if platform.system() == "Linux":
            import os

            if os.path.exists("/sys/class/power_supply/BAT0"):
                return True

        return False
    except:
        return False
