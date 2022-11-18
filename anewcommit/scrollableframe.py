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
from __future__ import print_function
import sys

if sys.version_info.major >= 3:
    # from tkinter import messagebox
    # from tkinter import filedialog
    import tkinter as tk
    from tkinter import ttk
    # from tkinter import tix
else:
    __metaclass__ = type
    # Python 2
    # import tkMessageBox as messagebox
    # import tkFileDialog as filedialog
    import Tkinter as tk
    import ttk
    # import Tix as tix

def echo0(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)
    # ^ This shows a syntax error in python2, so there is no way to fix
    # kwargs['file'] = sys.stderr
    # print(args, kwargs)


class SFContainer(ttk.Frame):
    # if sys.version_info.major < 3:
    #     __metaclass__ = type
    #     # ^ causes: "a new-style class can't have only classic bases"
    def __init__(self, container, *args, **kwargs):
        if sys.version_info.major > 2:
            try:
                super().__init__(container, *args, **kwargs)
                '''
                ^ same as
                  ttk.Frame.__init__(self, container, *args, **kwargs)
                  according to
                  <https://stackoverflow.com/a/51872298/4541104> ("Since
                  there's a hidden self in the super's parameters") yet
                  produces: "TypeError: super(type, obj): obj must be an
                  instance or subtype of type" if not a subtype of this
                  type.
                '''
            except TypeError as ex:
                if "obj must be an instance or subtype of type" in str(ex):
                    raise TypeError(
                        "You tried to call SFContainer.__init__ from an"
                        " object that is not of a SFContainer subclass."
                    )
                else:
                    raise ex
        else:

            # The exception is more clear in Python 2 than 3, but doesn't
            # happen here--it happens in the SFContainer.__init__ call higher
            # up:
            '''
            TypeError: unbound method __init__() must be called with
            SFContainer instance as first argument (got MainFrame
            instance instead)
            '''
            # super(ttk.Frame, self).__init__(container, *args, **kwargs)
            # ^ causes a different problem due to waning Python 2 support:
            #   "TypeError: super() argument 1 must be type, not classobj"
            #   so:
            ttk.Frame.__init__(self, container, *args, **kwargs)

        # ttk.Frame.__init__(self, container, *args, **kwargs)
        canvas = tk.Canvas(self)
        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )

        canvas.create_window((0, 0), window=self.scrollable_frame,
                             anchor=tk.NW)

        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=tk.YES)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    '''
    The scrollable_frame must become the parent of all sub-widgets, but
    overriding the properties won't work, since the frame (not the
    scrollable_frame) must be added to the parent.

    @property
    def _last_child_ids(self):
        return self.scrollable_frame._last_child_ids

    @_last_child_ids.setter
    def _last_child_ids(self, value):
        self.scrollable_frame._last_child_ids = value

    @property
    def children(self):
        return self.scrollable_frame.children

    @children.setter
    def children(self, value):
        self.scrollable_frame.children = value

    @property
    def tk(self):
        return self.scrollable_frame.tk

    @tk.setter
    def tk(self, value):
        self.scrollable_frame.tk = value
    '''



def main():
    root = None
    echo0("The scrollableframe module is running. This is for testing"
          " only and should not happen in a release.")
    try:
        root = tk.Tk()
    except tk.TclError:
        # "_tkinter.TclError: no display name and no $DISPLAY
        # environment variable"
        echo0("FATAL ERROR: Cannot use tkinter from terminal")
        sys.exit(1)
    root.wm_title("SFContainer Test")
    app = SFContainer(root)
    app.pack(side="top", fill="both", expand=True)
    msg = ("This is a test window. You should make your own subclass of"
           " SFContainer instead.")
    for text in msg.split():
        label = tk.Label(app.scrollable_frame, text=text)
        label.pack()
    # root.after(500, app.start_refresh)
    root.mainloop()


if __name__ == "__main__":
    main()
