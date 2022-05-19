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
__metaclass__ = type
# ^ Fix <https://stackoverflow.com/questions/1713038/super-fails-with-
#   error-typeerror-argument-1-must-be-type-not-classobj-when>
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
    # from tkinter import tix
except ImportError:
    # Python 2
    import tkMessageBox as messagebox
    import tkFileDialog as filedialog
    import Tkinter as tk
    import ttk
    # import Tix as tix

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
    debug,
    get_verbose,
)

session = None
playerIndex = 0

verb_width = 1
for verb in anewcommit.VERBS:
    if len(verb) > verb_width:
        verb_width = len(verb)

mode_width = 1
for mode in anewcommit.MODES:
    if len(mode) > mode_width:
        mode_width = len(mode)

WIDGET_TYPES = ["Checkbutton", "OptionMenu", "Entry", "Label"]

actions_field_order = ['commit', 'verb', 'mode', 'name']
actions_captions = ['       ', 'Commit   ', 'Action']
transition_field_order = ['commit', 'verb', 'name']
version_field_order = ['commit', 'mode', 'name']

field_widths = {}
selector_width = verb_width
if mode_width > selector_width:
    selector_width = mode_width
field_widths['verb'] = selector_width
field_widths['mode'] = selector_width
field_widths['commit'] = 5

conditional_formatting = {
    'verb': {
        '=get_version': {
            'readonly': True,
        },
    },
}
# TODO: (?) Implement conditional_formatting (not necessary if using
# separate version_template_fields below).

_version_template_fields = {
    'luid': {
        'hide': True,
    },
    'path': {
        'hide': True,
    },
    'verb': {
        'maxchars': verb_width,
        'widget': "Label",
    },
    'mode': {
        'maxchars': mode_width,
        'values': anewcommit.MODES,
    },
    'commit': {
        'caption': '',
        'default': True,
    },
}

_transition_template_fields = {
    'luid': {
        'hide': True,
    },
    'path': {
        'hide': True,
    },
    'verb': {
        'maxchars': verb_width,
        'values': anewcommit.VERBS,
    },
    'commit': {
        'caption': '',
        'default': False,
    },
}

transition_template = {
    'fields': _transition_template_fields,
    'field_order': transition_field_order,
    'field_widths': field_widths,
}

version_template = {
    'fields': _version_template_fields,
    'field_order': version_field_order,
    'field_widths': field_widths,
}


def dict_to_widgets(d, parent, template=None):
    '''
    Get a dict (results) where the key in results['widgets'][key] and
    in every other dict in the results dict is the corresponding key in
    dictionary d. The widgets will not be packed. The results also
    contains results['vs'] which has StringVar instances.

    Sequential arguments:
    d -- This dictionary defines the set of widgets to use.
    parent -- Set the frame that will contain the widget.
    template -- Describe the fields as they should appear in the UI in a
        platform-independent way. If the field isn't described, its type
        will determine its UI (such as Entry box for str and Checkbutton
        for bool).
        - If a field in field_order isn't a key in d, add a blank
          label and show a warning.
    '''
    if template is None:
        template = {}
    elif not hasattr(template, 'get'):
        raise TypeError("template should be a dict.")
    if template.get('fields') is None:
        template['fields'] = {}
    elif not hasattr(template['fields'], 'get'):
        raise TypeError("template['fields'] should be a dict.")
    fields = template['fields']
    '''
    if fields is None:
        fields_done = [False for key in field_order]
    '''
    field_order = template.get('field_order')
    field_widths = template.get('field_widths')
    if field_widths is None:
        field_widths = {}
    all_done = {}
    for key in d.keys():
        all_done[key] = False
    fields_done = all_done
    if field_order is None:
        field_order = d.keys()
        fields_done = {}
        for key in field_order:
            fields_done[key] = False

    results = {}
    results['widgets'] = {}
    results['vs'] = {}
    # for k, v in d.items():
    for k in field_order:
        widget_type = None
        if k not in d:
            error(
                "Warning: The key '{}' is missing but is in field_order"
                " (action={}). A blank label will be added for spacing."
                "".format(k, d)
            )
            v = ""
            widget_type = "Label"
        else:
            v = d[k]
        spec = fields.get(k)
        if spec is None:
            spec = {}
        widget = None
        expected_v = v
        if widget_type is None:
            widget_type = spec.get('widget')
        default_v = None
        if 'default' in spec:
            expected_v = spec['default']
            default_v = spec['default']
        if 'values' in spec:
            expected_v = spec['values']
            # ^ It must be a list (See OptionMenu case below).
            if widget_type is None:
                widget_type = 'OptionMenu'
            if default_v is None:
                default_v = expected_v[0]

        debug("  - {} widget_type: {}"
              "".format(k, widget_type))
        specified_widget = widget_type
        if widget_type is None:
            if (expected_v is None) or (isinstance(expected_v, str)):
                widget_type = "Entry"
            elif isinstance(expected_v, list):
                widget_type = "OptionMenu"
            elif isinstance(expected_v, bool):
                widget_type = "Checkbutton"
            else:
                debug("- Choosing a widget for {} (value {} type {},"
                      " expected a value like {} type {})"
                      " is not automated."
                      "".format(k, v, type(v).__name__,
                                expected_v, type(expected_v).__name__))
        if specified_widget != widget_type:
            debug("    - detected widget_type: {}"
                  "".format(widget_type))

        caption = spec.get('caption')
        width_v = v
        if caption is None:
            caption = k
        else:
            width_v = caption
        if width_v is None:
            width_v = ""
        if isinstance(width_v, int):
            width_v = str(width_v)
        elif isinstance(width_v, float):
            width_v = str(width_v)
        elif isinstance(width_v, bool):
            width_v = len(caption)
        elif not isinstance(width_v, str):
            width_v = str(width_v)
        else:
            error("Warning: While determining width,"
                  " the text for '{}' is an unknown type: "
                  " \"{}\" is a {}."
                  "".format(k, v, type(v).__name__))

        width = field_widths.get(k)
        if width is None:
            width = len(width_v)
            if width < 1:
                width = 1
        # OptionMenuAdditionalW = 4
        # width += OptionMenuAdditionalW
        if widget_type == "Entry":
            if v is None:
                v = ""
            results['vs'][k] = tk.StringVar()
            widget = ttk.Entry(
                parent,
                width=width,
                textvariable=results['vs'][k],
                # state="readonly",
            )
            results['vs'][k].set(v)
        elif widget_type == "Label":
            if v is None:
                v = ""
            results['vs'][k] = tk.StringVar()
            widget = ttk.Label(
                parent,
                width=width,
                textvariable=results['vs'][k],
                # state="readonly",
            )
            results['vs'][k].set(v)
        elif widget_type == "OptionMenu":
            # width -= OptionMenuAdditionalW
            results['vs'][k] = tk.StringVar()
            if v is None:
                v = ""
            widget = ttk.OptionMenu(
                parent,
                results['vs'][k],
                default_v,
                *expected_v
            )
            widget.configure(
                width=width,
            )
            # ^ Comma can't be after *x in python2.
            # command=option_changed,
            results['vs'][k].set(v)
        elif widget_type == "Checkbutton":
            results['vs'][k] = tk.IntVar()
            widget = ttk.Checkbutton(
                parent,
                text=caption,
                width=width,
                variable=results['vs'][k],
                onvalue=1,
                offvalue=0,
            )
            # indicatoron: If False, you must set your own visual
            #     instead of a check mark in the box.
            results['vs'][k].set(1)
            if (default_v is False) or (default_v == 0):
                results['vs'][k].set(0)
        else:
            if widget_type is None:
                raise ValueError(
                    "A widget for '{}'"
                    " (type is {}, specified widget={})"
                    " is not implemented. Try setting"
                    " template['fields']['{}']['widget']"
                    " to any appropriate widget type in: {}"
                    "".format(k, type(v).__name__, widget_type, k,
                              WIDGET_TYPES)
                )
            else:
                raise ValueError(
                    " template['fields']['{}']['widget']"
                    " is {} but should be one of: {}"
                    "".format(k, widget_type, WIDGET_TYPES)
                )
        results['widgets'][k] = widget

    return results


verbose = get_verbose()


class MainFrame(ttk.Frame):
    '''
    MainFrame loads, generates, or edits an anewcommit project.

    Requires:
    - global verbose (usually False)
    - See imports for more.

    Private Attributes:
    _project -- This is the currently loaded ANCProject instance.
    _frame_of_luid -- _frame_of_luid[luid] is the row, in the form of a
        frame, that represents the action (verb can be "get_version" or
        a transition verb) uniquely identified by a luid.
    _id_of_path -- _id_of_path[path] is the luid of the path. The path
        must appear only one time in the project (Theoretically it
        could appear more than once but either the commit would be a
        reversion or there would have to be some other operation that
        modifies it before a commit).
    _vars_of_luid -- _vars_of_luid[luid][key] is the widget of
        the action for the action uniquely identified by luid.
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
        # tix.ScrolledWindow.__init__(self, parent)
        # ^ _tkinter.TclError: invalid command name "tixScrolledWindow"
        #   if inherits from tix.ScrolledWindow (Python 2 or 3)
        # super(MainFrame, self).__init__(parent)
        # List of tk style templates:
        #     <https://www.pythontutorial.net/tkinter/ttk-style/>
        self.style = ttk.Style(self)
        self.style.configure('MainFrame.TFrame', background='gray')
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

    def _add_transition_row(self, action):
        '''
        Sequential arguments:
        action -- The action must be any action other than 'get_version'
            in the case of this method, therefore the action dict must
            contain the keys as returned by the anewcommit.new_*
            functions other than new_version.
        '''
        # action keys: mode, verb, commit
        # - where verb is not 'get_version'
        if action.get('verb') is None:
            raise ValueError("The verb is None")
        elif action.get('verb') == 'get_version':
            raise ValueError(
                "The verb is get_version, but that is not valid for"
                "_add_transition_row."
            )
        elif action.get('verb') not in anewcommit.VERBS:
            raise ValueError(
                "The verb must be: {}"
                "".format(anewcommit.VERBS)
            )
        frame = tk.Frame(self)
        luid = action['luid']
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
        options['verb'] = anewcommit.VERBS
        debug("- transition: {}".format(action))
        results = dict_to_widgets(
            action,
            frame,
            template=transition_template,
        )
        debug("  - dict_to_widgets got {} widgets."
              "".format(len(results['widgets'])))
        for name, widget in results['widgets'].items():
            widget.pack(side=tk.LEFT)
            var = results['vs'][name]
            self._vars_of_luid[luid][name] = var
        frame.pack(fill=tk.X)

    def _add_version_row(self, action):
        '''
        Sequential arguments:
        action -- The action must be a version in the case of this
            method, therefore the action dict must contain the keys as
            returned by the anewcommit.new_version function. The value
            for 'verb' must be 'get_version'
        '''
        # action keys: path, mode, verb, commit
        # - where verb is 'get_version'
        # - where mode is in MODES
        if action.get('verb') is None:
            raise ValueError("The verb is None")
        elif action.get('verb') != 'get_version':
            raise ValueError(
                "The verb is {}, but only get_version is valid for"
                "_add_version_row.".format(action.get('verb'))
            )
        row = self.rows
        path = action.get('path')
        name = os.path.split(path)[1]
        frame = tk.Frame(self)
        # label = ttk.Label(frame, text=name)
        # label.grid(column=0, row=row, sticky=tk.E)
        if path in self._id_of_path:
            raise ValueError("The path already exists: {}"
                             "".format(path))
        luid = action['luid']
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
        debug("- version: {}".format(action))
        results = dict_to_widgets(
            action,
            frame,
            template=version_template,
        )
        debug("  - dict_to_widgets got {} widgets."
              "".format(len(results['widgets'])))
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
        transition_action = self._project.add_transition('no_op')
        try:
            self._add_transition_row(transition_action)
            version_action = self._project.add_version(path)
            try:
                self._add_version_row(version_action)
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

        frame = tk.Frame(self)
        for caption in actions_captions:
            widget = ttk.Label(
                frame,
                text=caption,
            )
            widget.pack(side=tk.LEFT)
        frame.pack(fill=tk.X)

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
    debug("versions_path: {}".format(versions_path))
    style = ttk.Style(root)
    preferred_themes = ['winnative', 'aqua', 'alt']
    # aqua: Darwin
    # alt: Use checkboxes not shading for Checkbutton such as on KDE.
    # list of styles (included and available elsewhere):
    #     <https://wiki.tcl-lang.org/page/List+of+ttk+Themes>
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
