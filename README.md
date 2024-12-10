# kQueue Blender
Queue your Blender render projects and override settings.

![image](https://github.com/user-attachments/assets/fc5a8bfc-e99e-4699-b25b-9f8eb8a986d4)

## What can it do:
1. Save and load kQueue project files.
2. Fetch and cache Blender project data.
3. Render specific frame ranges, override render settings.
4. Open last rendered frame or path.
5. Turn screens off.
6. Shutdown PC on complete.
7. (TODO:) Render frames that were not rendered.

## Installation:
Required libraries: PyQt5 (to draw the UI), psutil (to kill processes), pygame (to play sounds).
Install Python 3 and put this into the console:
```
pip install PyQt5; psutil; pygame
```

## Run:
Run `start.pyw`, locate the `blender.exe` executable, drop your Blender projects into the program interface, save the file.
Change the order by dragging items, double click to rewrite settings, save and start rendering.

## Documentation:
You can define frames, frame ranges or exclude specific frames.
- Input: 1-4 | Output [1, 2, 3, 4]
- Input: 2-4, 6, 7 | Output: [2, 3, 4, 6, 7]
- Input: 1-6, ^5 | Output: [1, 2, 3, 4, 6]
