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


# _taskbar_progress = None


# def set_taskbar_progress(value):
#     global _taskbar_progress

#     try:
#         if _taskbar_progress is None:
#             _taskbar_progress = TaskbarProgress(int(value))
#             _taskbar_progress.set_progress_type(ProgressType.NORMAL)
#             print(_taskbar_progress)

#         _taskbar_progress.set_progress(int(value))
#         print(value)

#     except Exception as e:
#         print("!!!!!! --------------------------------------- ", e)


# def finish_taskbar_progress():
#     global _taskbar_progress

#     if _taskbar_progress is None:
#         return

#     _taskbar_progress.set_progress_type(ProgressType.NOPROGRESS)
#     _taskbar_progress.flash_done()

#     _taskbar_progress = None
