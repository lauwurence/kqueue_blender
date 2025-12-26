################################################################################
## Monitor Utils

import win32api
import win32con

from threading import Thread
from time import sleep
from screeninfo import get_monitors


def screen_off(delay=0.0):

    def func():
        sleep(delay)

        print(f'Turning screens off in {delay}s...')

        win32api.PostMessage(win32con.HWND_BROADCAST,
                            win32con.WM_SYSCOMMAND,
                            win32con.SC_MONITORPOWER, 2)

        # ctypes.windll.user32.SendMessageW(65535, 274, 61808, 2)

    if delay > 0:
        t = Thread(target=func)
        t.start()
    else:
        func()


def screen_on(delay=0.0):

    def func():
        sleep(delay)

        print(f'Turning screens on in {delay}s...')

        win32api.PostMessage(win32con.HWND_BROADCAST,
                            win32con.WM_SYSCOMMAND,
                            win32con.SC_MONITORPOWER, -1)

        # ctypes.windll.user32.SendMessageW(65535, 274, 61808, -1)
        # win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, 0, 0)

    if delay > 0:
        t = Thread(target=func)
        t.start()
    else:
        func()


def get_primary_display_info():
    """
    Get primary display info.
    """

    monitors = get_monitors()

    return next((m for m in monitors if m.is_primary), monitors[0])