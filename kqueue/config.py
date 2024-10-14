################################################################################
## Config Variables

TITLE = "kQueue Blender"
DEVELOPER = 'keyclap'
VERSION = (0, 2)
APPID = f'{DEVELOPER}.{TITLE.replace(" ", "_")}.{".".join([str(v) for v in VERSION])}'.lower()

ICON = "kqueue/icons/icon.svg"
RENDER_START_AUDIO = "kqueue/audio/render_started.ogg"
RENDER_STOP_AUDIO = "kqueue/audio/render_stopped.ogg"
RENDER_FINISH_AUDIO = "kqueue/audio/render_finished.ogg"
SAVE_FOLDER = "saves/"