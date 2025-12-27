################################################################################
## Config Variables

DEV_MODE = False
TITLE = "kQueue Blender"
DEVELOPER = 'keyclap'
VERSION = (0, 8)
APPID = f'{DEVELOPER}.{TITLE.replace(" ", "_")}.{".".join([str(v) for v in VERSION])}'.lower()

ICON = "kqueue/icons/icon.svg"
RENDER_START_AUDIO = "kqueue/audio/render_started.ogg"
RENDER_STOP_AUDIO = "kqueue/audio/render_stopped.ogg"
RENDER_FINISH_AUDIO = "kqueue/audio/render_finished.ogg"

SAVE_FOLDER = "saves/"
TEMP_FOLDER = "kqueue/blender/temp/"

CACHE_FILE = "kqueue/blender/.cache"
PERSISTENT_FILE = f"kqueue/{SAVE_FOLDER}/.persistent"
BRIDGE_FILE = f"{TEMP_FOLDER}data.json"
GET_DATA_BAT = f"{TEMP_FOLDER}get_data.bat"
GET_DATA_PY = "kqueue/blender/get_data.py"
