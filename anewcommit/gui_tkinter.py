#!/usr/bin/env python
'''
Open and organize multiple versions to prepare them to be added to
version control. Either make the new folder replace (delete all then
add) or merge with the previous version. Add transitions to ensure that
commit diffs are clean, such as by adding a separate commit that
renames folder(s) or file(s).

Options:
--verbose        Show more debug output.

Examples:
anewcommit .  # find versions in the current working directory.
'''

from __future__ import print_function
import os
import sys
from decimal import Decimal
import decimal
import locale as lc
import copy

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
    error,
    is_truthy,
)

session = None
playerIndex = 0


def dict_to_widgets(d, parent, options=None):
    '''
    Get a dict (results) where the key in results['widgets'][key] and
    in every other dict in the results dict is the corresponding key in
    dictionary d. The widgets will not be packed. The results also
    contains results['vs'] which has StringVar instances.

    Sequential arguments:
    d -- This dictionary defines the set of widgets to use.
    parent -- Set the frame that will contain the widget.
    options -- This can either be None or a dict which contains lists,
        where the key is a key in d. For example, if options['mode'] is
        ['delete_then_add', 'overlay'] then the widget for d['mode']
        will be a drop-down box with those two choices.
    '''
    if options is None:
        options = {}
    if not hasattr(options, 'get'):
        raise TypeError("options should be a dict.")
    results = {}
    results['widgets'] = {}
    results['vs'] = {}
    for k, v in d.items():
        widget = None
        expected_v = v
        try_v = options.get(k)
        if k in options:
            try_v = options[k]
        if (expected_v is None) or (isinstance(expected_v, str)):
            if v is None:
                v = ""
            results['vs'][k] = tk.StringVar()
            widget = ttk.Entry(
                parent,
                # width=25,
                textvariable=results['vs'][k],
                # state="readonly",
            )
            results['vs'][k].set(v)
        elif isinstance(expected_v, list):
            results['vs'][k] = tk.StringVar()
            if v is None:
                v = ""
            widget = ttk.OptionMenu(
                parent,
                results['vs'][k],
                expected_v[0],
                *expected_v,
                # command=option_changed,
            )
            results['vs'][k].set(v)
        elif isinstance(expected_v, bool):
            results['vs'][k] = tk.IntVar()
            widget = ttk.Checkbutton(
                parent,
                text=k,
                variable=results['vs'][k],
                onvalue=1,
                offvalue=0,
            )
            # indicatoron: If False, you must set your own visual
            #     instead of a check mark in the box.
            results['vs'][k].set(1)
        else:
            raise ValueError("A widget for {} is not implemented."
                             "".format(type(v).__name__))
        results['widgets'][k] = widget

    return results


verbose = False

class MainFrame(ttk.Frame):
    '''
    MainFrame loads, generates, or edits an anewcommit project.

    Requires:
    - global verbose (usually False)
    - See imports for more.

    Private Attributes:
    _project -- This is the currently loaded ANCProject instance.
    _frame_of_luid -- _frame_of_luid[luid] is the row, in the form of a
        frame, that represents the action (version or transition)
        uniquely identified by a luid.
    _id_of_path -- _id_of_path[path] is the luid of the path. The path
        must appear only one time in the project (Theoretically it
        could appear more than once but either the commit would be a
        reversion or there would have to be some other operation that
        modifies it before a commit).
    _vars_of_luid -- _vars_of_luid[luid][key] is the widget of
        the step key for the step uniquely identified by luid.
    '''
    def __init__(self, parent, settings=None):
        all_settings = copy.deepcopy(ANCProject.default_settings)
        if settings is not None:
            # if is_truthy(settings.get('verbose')):
            #     # self.settings['verbose'] = True
            #     verbose = True
            for k, v in settings.items():
                all_settings[k] = v
        self.settings = all_settings
        self.headings = []
        self.heading_captions = {}

        self._project = None
        self.parent = parent
        ttk.Frame.__init__(self, parent, style='MainFrame.TFrame')
        self.style = ttk.Style(self)
        # self.style.configure('MainFrame.TFrame', background='gray')
        # ^ See <https://www.pythontutorial.net/tkinter/ttk-style/>.
        #   The following didn't work:
        #   See <http://infohost.nmt.edu/tcc/help/pubs/tkinter/web/
        #   ttk-style-layer.html>
        #   via <https://stackoverflow.com/a/16639454>

        self._id_of_path = {}
        self._vars_of_luid = {}
        self._frame_of_luid = {}
        menu = tk.Menu(self.parent)
        self.menu = menu
        self.parent.config(menu=menu)
        self.next_id = 0
        self.panels = []

        fileMenu = tk.Menu(menu, tearoff=0)
        fileMenu.add_command(label="Open", command=self.ask_open)
        fileMenu.add_command(label="Exit", command=self.exitProgram)
        menu.add_cascade(label="File", menu=fileMenu)

        self.pack(fill=tk.BOTH, expand=True)
        # Doesn't work: padx=(10, 10), pady=(10, 10),
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
        frame = tk.Frame(self)
        luid = step['luid']
        self._frame_of_luid[luid] = frame
        self._vars_of_luid[luid] = {}
        button = ttk.Button(
            frame,
            text="+",
            width=2,
            command=lambda: self.add_before(luid),
        )
        # button.grid(column=1, row=row, sticky=tk.W)
        button.pack(side=tk.LEFT, padx=(10, 0))

        options = {}
        options['action'] = anewcommit.ACTIONS
        results = dict_to_widgets(step, frame, options=options)
        for name, widget in results['widgets'].items():
            widget.pack(side=tk.LEFT)
            var = results['vs'][name]
            self._vars_of_luid[luid][name] = var
        frame.pack(fill=tk.X)

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
        frame = tk.Frame(self)
        # label = ttk.Label(frame, text=name)
        # label.grid(column=0, row=row, sticky=tk.E)
        if path in self._id_of_path:
            raise ValueError("The path already exists: {}"
                             "".format(path))
        luid = step['luid']
        self._frame_of_luid[luid] = frame
        self._vars_of_luid[luid] = {}
        self._id_of_path[path] = luid
        button = ttk.Button(
            frame,
            text="+",
            width=2,
            command=lambda: self.add_before(luid),
        )
        # button.grid(column=1, row=row, sticky=tk.W)
        button.pack(side=tk.LEFT, padx=(10, 0))
        # remainingW = 1
        # relx = 0
        # relwidth = .5
        # button.place(relx=relx, relwidth=relwidth, in_=frame, anchor=tk.W, relheight=1.0)
        # relx += relwidth
        # remainingW -= relwidth

        options = {}
        options['mode'] = anewcommit.MODES
        results = dict_to_widgets(step, frame, options=options)
        for name, widget in results['widgets'].items():
            widget.pack(side=tk.LEFT)
            # widget.place(relx=relx, relwidth=relwidth, anchor=tk.W, relheight=.5, in_=frame)
            # relx += relwidth
            var = results['vs'][name]
            self._vars_of_luid[luid][name] = var
        frame.pack(fill=tk.X)
        # expand=True: makes the row taller so rows fill the window
        self.rows += 1

    def add_before(self, path):
        error("NotYetImplemented: add_before('{}')".format(path))

    def add_transition_and_source(self, path):
        transition_step = self._project.add_transition('no_op')
        try:
            self._add_transition_row(transition_step)
            version_step = self._project.add_version(path)
            try:
                self._add_version_row(version_step)
            except (ValueError, TypeError) as ex2:
                if verbose:
                    raise ex2
                messagebox.showerror("Error", str(ex2))
                return False
        except (ValueError, TypeError) as ex:
            if verbose:
                raise ex
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
        error("Added {}".format(count))

    def exitProgram(self):
        root.destroy()


def usage():
    error(__doc__)


def main():
    # global session
    # session = Session()

    global root
    root = tk.Tk()
    root.geometry("1000x600")
    root.minsize(600, 400)
    root.title("anewcommit")
    versions_path = None
    bool_names = ['--verbose']
    settings = {}
    for argi in range(1, len(sys.argv)):
        arg = sys.argv[argi]
        if arg.startswith("--"):
            option_name = arg[2:]
            if arg in bool_names:
                settings[option_name] = True
            else:
                usage()
                raise ValueError("{} is not a valid argument."
                                 "".format(arg))
        else:
            if versions_path is None:
                versions_path = arg
            else:
                usage()
                raise ValueError("There was an extra argument: {}"
                                 "".format(arg))
    global verbose
    if is_truthy(settings.get('verbose')):
        verbose = True
        error("* enabled verbose logging to standard error")
    style = ttk.Style(root)
    preferred_themes = ['winnative', 'aqua', 'alt']
    # aqua: Darwin
    # alt: Use checkboxes not shading for Checkbutton such as on KDE.
    for prefer_theme in preferred_themes:
        if prefer_theme in style.theme_names():
            style.theme_use(prefer_theme)
            break
    if verbose:
        error("* available ttk themes: {}".format(style.theme_names()))
        error("* current theme: {}".format(style.theme_use()))

    app = MainFrame(root, settings=settings)
    if versions_path is not None:
        app.add_versions_in(sys.argv[1])

    root.mainloop()
    # (Urban & Murach, 2016, p. 515)
    '''
    session.stop()
    if session.save():
        error("Save completed.")
    else:
        error("Save failed.")
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
