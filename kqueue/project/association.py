################################################################################
## File Association

import os
import sys
import ctypes

def register_file_association():

    if sys.platform != "win32":
        return

    import winreg

    try:
        if getattr(sys, "frozen", False):
            # Если программа собрана в .exe
            app_path = sys.executable
            command = f'"{app_path}" "%1"'

        else:
            # Если запускаем .py напрямую
            app_path = os.path.abspath(sys.argv[0])
            pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")

            command = f'"{pythonw}" "{app_path}" "%1"'

        # .kqp -> kQueue.Project
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\.kqp") as key:
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, "kQueue.Project")

        # Описание типа файла
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\kQueue.Project") as key:
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, "kQueue Project")

        # Команда открытия
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\kQueue.Project\shell\open\command") as key:
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, command)

        ctypes.windll.shell32.SHChangeNotify(0x08000000, 0x0000, None, None)

        print("Association .kqp registered")

    except Exception as e:
        print(f"Unable to register .kqp: {e}")

    icon_path = os.path.abspath("kqueue/icons/kqp.ico")

    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\kQueue.Project\DefaultIcon") as key:
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, icon_path)
