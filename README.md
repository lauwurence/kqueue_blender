# kQueue Blender
<img width="2479" height="1489" alt="image" src="https://github.com/user-attachments/assets/4a6d28a5-e8e5-4caf-bf0c-2a98792af92c" />

## What can it do:
1. Save and load kQueue project files.
2. Fetch and cache Blender project data.
3. Exclude specific Blender projects from render queue.
4. Render specific frames, override render settings.
5. Render in fast preview mode (Workbench rendered + SubD 0).
6. Render only unsaved images.
7. Open last rendered image or path.
8. Show thumbnail of the last rendered image in the folder.
9. Monitor VRAM usage, GPU load and heat.
10. Turn screens off.
11. Shutdown PC on complete.

## Installation:
Required libraries: PyQt6 (to draw the UI), psutil (to kill processes), pygame (to play sounds).
Install Python 3 and put this into the console:
```
pip install PyQt5; pywin32; psutil; pygame; numpy; screeninfo; pynvml
```

## Run:
Run `start.pyw`, locate the `blender.exe` executable, drop your Blender projects into the program interface, save the file.
Change the order by dragging items, double click to rewrite settings, save and start rendering.

## Documentation:
You can define frames, frame ranges or exclude specific frames.
- Input: 1-4 | Output [1, 2, 3, 4]
- Input: 2-4, 6, 7 | Output: [2, 3, 4, 6, 7]
- Input: 1-6, ^5 | Output: [1, 2, 3, 4, 6]
