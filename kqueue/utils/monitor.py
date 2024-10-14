################################################################################

# import ctypes
import win32api
import win32con


def screen_off():
    print("Turning screen off...")
    win32api.PostMessage(win32con.HWND_BROADCAST,
                         win32con.WM_SYSCOMMAND,
                         win32con.SC_MONITORPOWER, 2)
    # ctypes.windll.user32.SendMessageW(65535, 274, 61808, 2)


def screen_on():
    print("Turning screen on...")
    win32api.PostMessage(win32con.HWND_BROADCAST,
                         win32con.WM_SYSCOMMAND,
                         win32con.SC_MONITORPOWER, -1)
    # ctypes.windll.user32.SendMessageW(65535, 274, 61808, -1)
    # win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, 0, 0)