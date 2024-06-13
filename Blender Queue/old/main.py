
# import io
# import os
# import tkinter as tk
# import time
# import subprocess
# import threading
# import psutil

# from tkinter import ttk
# from tkinter import filedialog
# from pathlib import Path
# from ctypes import windll

# # Allow font size adjustment
# windll.shcore.SetProcessDpiAwareness(1)

# ################################################################################
# ## Root Parameters

# TITLE = "kQueue Blender"
# ROOT_SIZE = (1200, 600)
# ROOT_ICON = "icons/blender.png"

# ################################################################################

# def join(*paths): return os.path.join(*paths).replace("\\", "/")
# WORKING_DIR = join(os.getcwd())

# ################################################################################

# from tkinterdnd2 import DND_FILES, TkinterDnD

# root = TkinterDnD.Tk()
# blend_app_filename = "H:/Blender Foundation/blender-4.1.1/blender.exe"
# # blend_app_filename = None
# lbl_blender = None

# lst_projects = None
# # project_filenames = ["I:/Blender Library/00_Parts/00_Intro/03_HomeRoaming/001_Table.blend"]
# project_filenames = []

# process = None
# flag_stop_render = False
# is_rendering = False

# ################################################################################

# def log(*args):
#     for arg in args:
#         text = arg.rstrip()
#         lbl_output.config(text=text)
#         print(text)

# def locate_blender_exe():
#     global blend_app_filename
#     filename = filedialog.askopenfilename(filetypes=[("Blender", "blender.exe")])
#     if not filename: return
#     lbl_blender.config(text=filename, bg='white', fg='grey')
#     blend_app_filename = filename
#     log(f'Blender path: {filename}')

# def add_project(e):
#     import re
#     found = re.findall(r'(?:{)(.*?.blend)(?:})|(^\S*.blend)', e.data)

#     for f1, f2 in found:
#         fn = f1 or f2
#         if fn:
#             project_filenames.append(fn)
#             lst_projects.insert(tk.END, fn)
#             log(f'Added: {fn}')

# def start_render():
#     global process, is_rendering

#     if blend_app_filename is None:
#         log("Blender not defined!")
#         return

#     if not project_filenames:
#         log("No projects defined!")
#         return

#     projects = []

#     for project_filename in project_filenames:
#         line = f'blender --background "{join(project_filename)}" --scene "Scene" -E "CYCLES" -s "1" -e "1" --python-expr "import bpy; bpy.context.scene.render.use_overwrite = True;" -a'
#         projects.append(line)

#     BATCH = f"""
# @CHCP 65001 > NUL
# cd /d "{join(Path(blend_app_filename).parent)}"
# @echo ---START-RENDER
# {"\n@echo ---NEXT-RENDER\n".join(projects)}
# @echo ---END-RENDER
# """
#     FILE_BAT = join(WORKING_DIR, f'start_render.bat')
#     BATCH = BATCH.rstrip()

#     with open(FILE_BAT, 'w') as f:
#         f.write(BATCH)

#     process = subprocess.Popen([FILE_BAT],
#                                stderr=subprocess.STDOUT,
#                                stdout=subprocess.PIPE,
#                                stdin=subprocess.PIPE,
#                             #    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP, #DETACHED_PROCESS
#                             #    creationflags=subprocess.DETACHED_PROCESS, #DETACHED_PROCESS
#                             #    preexec_fn=os.setsid,
#                                shell=False
#                                )

#     t = threading.Thread(target=blender_console)
#     t.start()

#     is_rendering = True


# def blender_console():
#     """
#     Print info from Blender console.
#     """
#     global flag_stop_render

#     while process.poll() is None:

#         if flag_stop_render or process.stdout.closed:
#             break

#         try:
#             for line in io.TextIOWrapper(process.stdout, encoding="utf-8"):
#                 log(line)
#                 if flag_stop_render or process.stdout.closed:
#                     break

#             for line in io.TextIOWrapper(process.stdin, encoding="utf-8"):
#                 log(line)
#                 if flag_stop_render or process.stdin.closed:
#                     break
#         except:
#             break

#     if flag_stop_render or process.stdout.closed or process.stdin.closed:
#         log("Rendering stopped.")
#     else:
#         log("Rendering finished.")

#     flag_stop_render = False


# def stop_render():
#     """
#     Stop rendering process.
#     """
#     global process, flag_stop_render, is_rendering

#     if flag_stop_render:
#         return

#     log("Stopping rendering...")
#     flag_stop_render = True

#     for proc in psutil.Process(process.pid).children(recursive=True):
#         proc.kill()

#     process.kill()
#     is_rendering = False


# ################################################################################

# def main():
#     """
#     Main thread.
#     """
#     # [widget] Root
#     root.title(TITLE)
#     root.iconphoto(False, tk.PhotoImage(file=ROOT_ICON))
#     root.geometry(f"{ROOT_SIZE[0]}x{ROOT_SIZE[1]}")
#     root.resizable(False, False)
#     root.config(bg='white')

#     # [frame] Horizontal
#     frame = tk.Frame()
#     frame.grid(padx=10, pady=2, sticky='NSEW')

#     # [button] Locate Blender executable
#     btn_locate_blender = tk.Button(frame, text="Locate",
#                                    command=locate_blender_exe,
#                                    )
#     btn_locate_blender.grid(row=0, column=0)

#     # [label] Blender
#     global lbl_blender
#     lbl_blender = tk.Label(frame, text="Blender not selected!",
#                             bg="red",
#                             fg='black',
#                             font=('Arial', 10, 'normal'),
#                             anchor='w',
#                             padx=10,
#                             width=100
#                             #  width=20, height=10,
#                             #  anchor='e',
#                             #  relief=tk.RAISED, bd=10,
#                             #  justify=tk.CENTER
#                             )
#     lbl_blender.grid(row=0, column=1)

#     # # [list] Projects
#     # style = ttk.Style()
#     # style.theme_use('default')
#     # style.configure('Treeview',
#     #                 background="#D3D3D3",
#     #                 foreground="black",
#     #                 rowheight=25,
#     #                 fieldbackground="D3D3D3")

#     # style.map('Treeview',
#     #           background=[('selected', "#347083")])

#     # # [frame] Tree
#     # tree_frame = tk.Frame(root, width=550)
#     # tree_frame.grid(padx=200)

#     # # [scroll] Tree
#     # tree_scroll = tk.Scrollbar(tree_frame)
#     # tree_scroll.pack(side=tk.RIGHT,
#     #                  fill=tk.Y)

#     # # [treeview] Tree
#     # tree_projects = ttk.Treeview(tree_frame,
#     #                              yscrollcommand=tree_scroll.set,
#     #                              selectmode=tk.EXTENDED)
#     # tree_projects.pack(fill=tk.X)
#     # tree_scroll.config(command=tree_projects.yview)


#     # tree_projects['columns'] = ("Order", ".blend", "Output", "Camera")
#     # tree_projects.column("#0", width=30, minwidth=30)
#     # tree_projects.column("#1", width=120, minwidth=25)
#     # tree_projects.column("#2", width=120, minwidth=25)
#     # tree_projects.column("#3", width=120, minwidth=25)

#     # tree_projects.heading("#0", text="#", anchor='e')
#     # tree_projects.heading("#1", text="Project", anchor='w')
#     # tree_projects.heading("#2", text="Output", anchor='w')
#     # tree_projects.heading("#3", text="Camera", anchor='w')

#     # tree_projects.insert(parent='', index=tk.END, iid=0, text=0, values=("blender.exe", "C:/folder/", "Camera"))
#     # tree_projects.insert(parent='', index=tk.END, iid=1, text=1, values=("blender.exe", "C:/folder/", "Camera"))
#     # tree_projects.insert(parent='', index=tk.END, iid=2, text=2, values=("blender.exe", "C:/folder/", "Camera"))
#     # tree_projects.insert(parent='', index=tk.END, iid=3, text=3, values=("blender.exe", "C:/folder/", "Camera"))
#     # tree_projects.insert(parent='', index=tk.END, iid=4, text=0, values=("blender.exe", "C:/folder/", "Camera"))
#     # tree_projects.insert(parent='', index=tk.END, iid=5, text=0, values=("blender.exe", "C:/folder/", "Camera"))
#     # tree_projects.insert(parent='', index=tk.END, iid=6, text=0, values=("blender.exe", "C:/folder/", "Camera"))
#     # tree_projects.insert(parent='', index=tk.END, iid=7, text=0, values=("blender.exe", "C:/folder/", "Camera"))
#     # tree_projects.insert(parent='', index=tk.END, iid=8, text=0, values=("blender.exe", "C:/folder/", "Camera"))
#     # tree_projects.insert(parent='', index=tk.END, iid=9, text=0, values=("blender.exe", "C:/folder/", "Camera"))
#     # tree_projects.insert(parent='', index=tk.END, iid=10, text=0, values=("blender.exe", "C:/folder/", "Camera"))
#     # tree_projects.insert(parent='', index=tk.END, iid=11, text=0, values=("blender.exe", "C:/folder/", "Camera"))

#     # tree_projects.tag_configure('oddrow', background='white')
#     # tree_projects.tag_configure('evenrow', background='lightblue')


#     global lst_projects
#     lst_projects = tk.Listbox(root,
#                               width=150,
#                               fg='grey')
#     lst_projects.grid()

#     lst_projects.drop_target_register(DND_FILES)
#     lst_projects.dnd_bind('<<Drop>>', add_project)

#     # [label] Output
#     global lbl_output
#     lbl_output = tk.Label(root, text="...",
#                             bg="white",
#                             fg='grey',
#                             font=('Arial', 8, 'normal'),
#                             padx=10, pady=10,
#                             width=150,
#                             anchor='w',
#                             #  relief=tk.RAISED, bd=10,
#                             justify=tk.LEFT
#                             )
#     lbl_output.grid()

#     # [button] Start Render
#     btn_start_render = tk.Button(root, text="Render",
#                                 command=start_render,
#                                 bg="#c2c2c2"
#                                 )
#     btn_start_render.grid(stick='we')

#     # [button] Stop Render
#     btn_stop_render = tk.Button(root, text="Stop",
#                                 command=stop_render,
#                                 bg="#c2c2c2"
#                                 )
#     btn_stop_render.grid(stick='we')

#     # Run
#     root.mainloop()

# main()