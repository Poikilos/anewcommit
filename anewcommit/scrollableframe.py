#!/usr/bin/env python
'''
by Jose Salvatierra (https://blog.teclado.com/tkinter-scrollable-frames/)
Oct 10, 2022

> Once you've done this, you can add elements to the scrollable_frame, and
> it'll work as you'd expect!
>
> Also, don't forget to use Pack or Grid to add the container, canvas, and
> scrollbar to the application window.

-Jose Salvatierra
'''
import sys

python_mr = sys.version_info[0]

if python_mr >= 3:
    from tkinter import messagebox
    from tkinter import filedialog
    import tkinter as tk
    from tkinter import ttk
    # from tkinter import tix
else:
    # Python 2
    import tkMessageBox as messagebox
    import tkFileDialog as filedialog
    import Tkinter as tk
    import ttk
    # import Tix as tix

class ScrollableFrame(ttk.Frame):
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        canvas = tk.Canvas(self)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )

        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
