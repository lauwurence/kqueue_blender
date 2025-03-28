# kQueue Blender
Queue Blender projects and override settings.

![image](https://github.com/user-attachments/assets/846f88b2-884a-4fcc-bf8f-5055c2b66b17)

## What can it do:
1. Save and load kQueue files.
2. Fetch and cache Blender project data.
3. Exclude specific Blender projects from render queue. 
4. Render specific frame ranges, override render settings.
5. Render in render preview mode (Workbench rendered, SubD 0).
6. Render only non-existing images.
7. Save as sRGB (if you work in other color spaces).
8. Open last rendered image or its path.
9. Turn screens off.
10. Shutdown PC on complete.

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
