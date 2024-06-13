# kQueue Blender
Blender Render Queue Program
Queue your Blender render projects and override settings.

![image](https://github.com/lauwurence/kqueue_blender/assets/46109734/9eccb088-0220-4c4a-bd12-daa020a25241)

## What can it do:
1. Fetch and cache Blender projects data.
2. Render specific frame ranges, override render settings.
3. Turn screens off.
4. Shutdown PC on complete.

## Installation:
Required libraries: PyQt5 (to draw the UI), psutil (to kill processes), pygame (to play audio).
Install Python 3 and write this into console:
```
pip install PyQt5; psutil; pygame
```

## Run:
Run `start.pyw`, locate your `blender.exe` executable, drop your Blender projects into the program interface.
Change the order by dragging items, double click to rewrite settings, save and click "Render".
