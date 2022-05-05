#!/usr/bin/env python
from __future__ import print_function
import os
import sys
from decimal import Decimal
import decimal
import locale as lc

try:
    from tkinter import messagebox
    from tkinter import filedialog
    import tkinter as tk
    from tkinter import ttk
except ImportError:
    # Python 2
    import tkMessageBox as messagebox
    import tkFileDialog as filedialog
    import Tkinter as tk
    import ttk

import math

myPath = os.path.realpath(__file__)
myDir = os.path.dirname(myPath)
tryRepoDir = os.path.dirname(myDir)

tryInit = os.path.join(tryRepoDir, "anewcommit", "__init__.py")
if os.path.isfile(tryInit):
    # Ensure the repo version is used if running from the repo.
    sys.path.insert(0, tryRepoDir)

import anewcommit
from anewcommit import (
    ANCProject,
)

session = None
playerIndex = 0

'''
copypasta:
        self.bet_entry['state'] = tk.NORMAL
        self.stand_button['state'] = tk.DISABLED  # (Cagle, 2007)
        ttk.Label(self, text="Money:").grid(column=0, row=row, sticky=tk.E)
        ttk.Entry(self, width=25, textvariable=self.balance,
                  state="readonly").grid(column=1, columnspan=3,
                                         row=row, sticky=tk.W)
        self.stand_button['state'] = tk.DISABLED  # (Cagle, 2007)
        self.hit_button['state'] = tk.DISABLED  # (Cagle, 2007)
        for child in self.winfo_children():
            child.grid_configure(padx=6, pady=3)
        # (Urban & Murach, 2016, p. 515)
'''

class MainFrame(ttk.Frame):
    '''

    Private Properties:
    _project -- This is the currently loaded ANCProject instance.
    '''
    def __init__(self, parent):
        self._project = None
        self.parent = parent
        ttk.Frame.__init__(self, parent)
        self.text_vars = {}
        menu = tk.Menu(self.parent)
        self.menu = menu
        self.parent.config(menu=menu)

        fileMenu = tk.Menu(menu)
        fileMenu.add_command(label="Open", command=self.ask_open)
        fileMenu.add_command(label="Exit", command=self.exitProgram)
        menu.add_cascade(label="File", menu=fileMenu)

        self.pack(fill=tk.BOTH, expand=True)
        self.rows = 0

        self.wide_width = 30

    def ask_open(self):
        directory = filedialog.askdirectory()
        if directory is not None:
            self.add_versions_in(directory)

    def _add_transition_row(self, step):
        '''
        Sequential arguments:
        step -- The step must be any action other than 'get_version' in
            the case of this method, therefore the step dict must
            contain the keys as returned by the anewcommit.new_*
            functions other than new_version.
        '''
        # step keys: mode, action, commit
        # - where action is not 'get_version'
        if step.get('action') is None:
            raise ValueError("The action is None")
        elif step.get('action') == 'get_version':
            raise ValueError(
                "The action is get_version, but that is not valid for"
                "_add_transition_row."
            )
        elif step.get('action') not in anewcommit.ACTIONS:
            raise ValueError(
                "The action must be: {}"
                "".format(anewcommit.ACTIONS)
            )


    def _add_version_row(self, step):
        '''
        Sequential arguments:
        step -- The step must be a version in the case of this method,
            therefore the step dict must contain the keys as returned
            by the anewcommit.new_version function. The value for
            'action' must be 'get_version'
        '''
        # step keys: path, mode, action, commit
        # - where action is 'get_version'
        # - where mode is in MODES
        if step.get('action') is None:
            raise ValueError("The action is None")
        elif step.get('action') != 'get_version':
            raise ValueError(
                "The action is {}, but only get_version is valid for"
                "_add_version_row.".format(step.get('action'))
            )
        row = self.rows
        path = step.get('path')
        name = os.path.split(path)[1]
        # label = ttk.Label(self, text=name)
        # label.grid(column=0, row=row, sticky=tk.E)
        if path in self.text_vars:
            raise ValueError("The path already exists: {}"
                             "".format(path))
        self.text_vars[path] = tk.StringVar()
        entry = ttk.Entry(
            self,
            width=25,
            textvariable=self.text_vars[path],
            # state="readonly",
        )
        self.text_vars[path].set(name)
        entry.grid(column=2, columnspan=2, row=row, sticky=tk.W)
        '''
        entry = ttk.Entry(self, width=self.wide_width,
                          textvariable=self.text_vars[path],
                          state="readonly")
        entry.grid(column=1, columnspan=3, row=row, sticky=tk.W)
        '''
        button = ttk.Button(self, text="+",
                            command=lambda: self.add_before(path))
        button.grid(column=1, row=row, sticky=tk.W)
        # for child in self.winfo_children():
        #     child.grid_configure(padx=6, pady=3)
        # (Urban & Murach, 2016, p. 515)

        self.rows += 1

    def add_before(self, path):
        print("NotYetImplemented: add_before('{}')".format(path))

    def add_transition_and_source(self, path):
        transition_step = self._project.add_transition('no_op')
        try:
            self._add_transition_row(transition_step)
            version_step = self._project.add_version(path)
            try:
                self._add_version_row(version_step)
            except ValueError as ex2:
                messagebox.showerror("Error", str(ex2))
                return False
        except ValueError as ex:
            messagebox.showerror("Error", str(ex))
            return False
        return True

    def add_versions_in(self, path):
        if self._project is None:
            self._project = ANCProject()
            self._project.project_dir = path
        count = 0
        for sub in os.listdir(path):
            subPath = os.path.join(path, sub)
            if not os.path.isdir(subPath):
                continue
            result = self.add_transition_and_source(subPath)
            if not result:
                break
            count += 1
        print("Added {}".format(count))

    def exitProgram(self):
        root.destroy()


def main():
    # global session
    # session = Session()

    global root
    root = tk.Tk()
    root.geometry("1000x700")
    root.title("anewcommit")
    app = MainFrame(root)
    if len(sys.argv) > 1:
        app.add_versions_in(sys.argv[1])
    root.mainloop()
    # (Urban & Murach, 2016, p. 515)
    '''
    session.stop()
    if session.save():
        print("Save completed.")
    else:
        print("Save failed.")
    '''


if __name__ == "__main__":
    main()


# TODO (after handed in): The "Urban" line below causes the following
# error on python2:
# "SyntaxError: Non-ASCII character '\xe2' in file imageprocessorx.py on
# line " ... so the apostraphe must become a standard one (single quote)
# References
# Urban, M., & Murach, J. (2016). Murach's Python Programming
#     [VitalSource Bookshelf]. Retrieved from
#     https://bookshelf.vitalsource.com/#/books/9781943872152
# Cagle, J. R. (2007, February 12). Tkinter button "disable" ? [Reply].
#     Retrieved December 15, 2019, from DaniWeb website:
#     <https://www.daniweb.com/programming/software-development/threads/
#     69669/tkinter-button-disable>
