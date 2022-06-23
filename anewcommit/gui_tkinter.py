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
# from decimal import Decimal
# import decimal
# import locale as lc
import json
import copy

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

"""
# region same as rotocanvas imageprocessorx
dephelp = '''sudo apt-get install python3-pil python3-pil.imagetk
# or in a virtualenv:
#   pip install Pillow
'''
enable_png = True
try:
    import PIL
    from PIL import Image
except ModuleNotFoundError as ex:
    print("{}".format(ex))
    print()
    print("You must install ImageTk such as via:")
    print(dephelp)
    print()
    enable_png = False
    # sys.exit(1)

try:
    from PIL import ImageTk  # Place this at the end (to avoid any conflicts/errors)
except ImportError as ex:
    print("{}".format(ex))
    print()
    print("You must install ImageTk such as via:")
    print(dephelp)
    print()
    enable_png = False
    # sys.exit(1)
# endregion same as rotocanvas imageprocessorx
"""
# import math

myPath = os.path.realpath(__file__)
myDir = os.path.dirname(myPath)
staticDir = os.path.join(myDir, "static")
imagesDir = os.path.join(staticDir, "images")
# downArrowPath = os.path.join(imagesDir, "arrow-down.png")
# upArrowPath = os.path.join(imagesDir, "arrow-up.png")
downArrowPath = os.path.join(imagesDir, "arrow-down.gif")
upArrowPath = os.path.join(imagesDir, "arrow-up.gif")
arrow_paths = [upArrowPath, downArrowPath]

tryRepoDir = os.path.dirname(myDir)

tryInit = os.path.join(tryRepoDir, "anewcommit", "__init__.py")

if os.path.isfile(tryInit):
    sys.stderr.write("The module will run from the repo: {}\n"
                     "".format(tryRepoDir))
    sys.stderr.flush()
    # Ensure the repo version is used if running from the repo.
    sys.path.insert(0, tryRepoDir)

import anewcommit
from anewcommit import (
    ANCProject,
    is_truthy,
    echo0,
    echo1,
    echo2,
    get_verbose,
    set_verbose,
    profile,
    substep_to_str,
    s2or3,
)

echos = []
echos.append(echo0)
echos.append(echo1)
echos.append(echo2)

from anewcommit.scrollableframe import SFContainer

verbose = get_verbose()

verb_width = 1
for verb in anewcommit.TRANSITION_VERBS:
    if len(verb) > verb_width:
        verb_width = len(verb)

mode_width = 1
for mode in anewcommit.MODES:
    if len(mode) > mode_width:
        mode_width = len(mode)

WIDGET_TYPES = ["Checkbutton", "OptionMenu", "Entry", "Label"]

actions_field_order = ['commit', 'verb', 'mode', 'name']
actions_captions = ['       ', ' ^    ', 'Action']
transition_field_order = ['commit', 'verb', 'command']
version_field_order = ['commit', 'mode', 'name']

field_widths = {}
selector_width = verb_width
if mode_width > selector_width:
    selector_width = mode_width
field_widths['verb'] = selector_width
field_widths['mode'] = selector_width
# field_widths['commit'] = 5

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
        'values': anewcommit.TRANSITION_VERBS,
    },
    'commit': {
        'caption': '',
    },
    'command': {
        'widget': 'Entry',
        'maxchars': 200,
    },
}

transition_template = {
    'fields': _transition_template_fields,
    'field_order': transition_field_order,
    'field_widths': field_widths,
}
# ^ modified later to include lambdas calling class methods.

version_template = {
    'fields': _version_template_fields,
    'field_order': version_field_order,
    'field_widths': field_widths,
}
# ^ modified later to include lambdas calling class methods.

_GUI_DUMP = []
_BACKEND_DUMP = []


def default_callback(*args, **kwargs):
    # sv.trace_add callback sends 3 sequential arguments:
    # - str such as "PY_VAR0" (var._name)
    # - str (blank for unknown reason)
    # - str such as "write" (or at end of program, "unset")
    echo0("NotYetImplemented: default_callback")

    for arg in args:
        echo0('- {} "{}"'.format(type(arg).__name__, arg))
    for pair in kwargs.items():
        # k, v = pair
        # echo0("  {}: {}".format(k, v))
        echo0("  {}".format(pair))


def dict_to_widgets(d, parent, template=None, warning_on_blank=True):
    '''
    Get a dict (results) where the key in results['widgets'][key] and
    in every other dict in the results dict is the corresponding key in
    dictionary d. The widgets will not be packed. The results also
    contains results['vs'] which has StringVar instances.

    This method does NOT handle defaults. The data comes directly from d.

    Sequential arguments:
    d -- This dictionary defines the set of widgets to use.
    parent -- Set the frame that will contain the widget.
    template -- Describe the fields as they should appear in the UI in a
        platform-independent way. If the field isn't described, its type
        will determine its UI (such as Entry box for str and Checkbutton
        for bool).
    warning_on_blank -- If a field in field_order isn't a key in d, add a
        blank label and show a warning unless no_warning_on_blank is True.
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
    # ^ If not present, [k]['maxchars'] can be used.
    if field_widths is None:
        field_widths = {}
    all_done = {}
    for key in d.keys():
        all_done[key] = False
    del key
    fields_done = all_done
    if field_order is None:
        field_order = d.keys()
        fields_done = {}
        for key in field_order:
            fields_done[key] = False
        del key

    results = {}
    results['widgets'] = {}
    results['vs'] = {}
    # for k, v in d.items():

    for k in field_order:
        widget_type = None
        if k not in d:
            if warning_on_blank:
                echo0(
                    "Warning: The key '{}' is missing but is in field_order"
                    " (action={}). A blank label will be added for spacing."
                    "".format(k, d)
                )
            v = ""
            widget_type = "Label"
        else:
            v = s2or3(d[k])
        spec = fields.get(k)
        if spec is None:
            echo1("  - {} has no spec. Deciding on a widget...".format(k))
            spec = {}
        widget = None
        expected_v = v
        if widget_type is None:
            widget_type = s2or3(spec.get('widget'))
        if 'values' in spec:
            expected_v = s2or3(spec['values'])
            # ^ It must be a list (See OptionMenu case below).
            if python_mr < 3:
                for evI in range(len(expected_v)):
                    expected_v[evI] = s2or3(expected_v[evI])
            if widget_type is None:
                widget_type = 'OptionMenu'

        echo2("  - {} widget_type: {} {}"  # such as commit widget_type: None
              "".format(k, type(widget_type).__name__,
                        json.dumps(widget_type)))
        specified_widget = widget_type
        if widget_type is None:
            if (expected_v is None) or (isinstance(expected_v, str)):
                widget_type = "Entry"
            elif isinstance(expected_v, list):
                widget_type = "OptionMenu"
            elif isinstance(expected_v, bool):
                widget_type = "Checkbutton"
            else:
                echo1("- Choosing a widget for {} ({} {},"
                      " expected a value like {} {})"
                      " is not automated."
                      "".format(k, type(v).__name__, json.dumps(v),
                                type(expected_v).__name__,
                                json.dumps(expected_v)))
        if specified_widget != widget_type:
            echo2("    - detected widget_type: {}"
                  "".format(widget_type))

        caption = s2or3(spec.get('caption'))
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
        elif isinstance(width_v, str):
            pass
        else:
            echo0("Warning: While determining width,"
                  " the text for '{}' is an unknown type: "
                  " \"{}\" is a {}."
                  "".format(k, width_v, type(width_v).__name__))

        width = field_widths.get(k)
        if width is None:
            width = spec.get('maxchars')
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
                v,  # N/A: See .set below instead.
                *expected_v
            )
            widget.configure(
                width=width,
            )
            # ^ Comma can't be after *x in python2.
            # command=option_changed,
            results['vs'][k].set(v)
        elif widget_type == "Checkbutton":
            on_value = True
            off_value = False
            if (v is None) or (v is False) or (v is True):
                results['vs'][k] = tk.BooleanVar()
            elif isinstance(v, int):
                results['vs'][k] = tk.IntVar()
                if v != 0:
                    on_value = v
                    off_value = 0
                else:
                    on_value = 1
                    off_value = 0
            elif isinstance(v, str):
                results['vs'][k] = tk.StringVar()
                if v != "":
                    on_value = v
                    off_value = 0
                else:
                    on_value = "checked"
                    off_value = ""
            else:
                raise ValueError("Checkbutton var type {} isn't implemented."
                                 "".format(type(v).__name__))
            hard_default = off_value
            widget = ttk.Checkbutton(
                parent,
                text=caption,
                width=width,
                variable=results['vs'][k],
                onvalue=on_value,
                offvalue=off_value,
            )
            # indicatoron: If False, you must set your own visual
            #     instead of a check mark in the box.
            results['vs'][k].set(hard_default)
            if v is None:
                results['vs'][k].set(False)
            elif v is False:
                results['vs'][k].set(False)
            elif v is True:
                results['vs'][k].set(True)
            else:
                results['vs'][k].set(v)
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
                    " is {} {} but should be a str matching: {}"
                    "".format(k, type(widget_type).__name__,
                              widget_type, WIDGET_TYPES)
                )
        results['widgets'][k] = widget

    return results


class MainFrame(SFContainer):
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
        self._added_title_row = False
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
        SFContainer.__init__(self, parent, style='MainFrame.TFrame')
        # ttk.Frame.__init__(self, parent, style='MainFrame.TFrame')
        # ^ There seems to be no way to make a Frame scrollable.
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
        self._index_of_path = {}
        self._vars_of_luid = {}
        self._frame_of_luid = {}
        self._key_of_name = {}
        self._luid_of_name = {}
        self._var_of_name = {}
        self.menu = tk.Menu(self.parent)
        self.parent.config(menu=self.menu)
        self.next_id = 0
        self._items = []

        self.fileMenu = tk.Menu(self.menu, tearoff=0)
        self.fileMenu.add_command(label="Open", command=self.ask_open)
        self.fileMenu.add_command(label="Exit", command=self.exitProgram)
        self.menu.add_cascade(label="File", menu=self.fileMenu)

        self.editMenu = tk.Menu(self.menu, tearoff=0)
        self.editMenu.add_command(label="Undo", command=self.undo)
        self.editMenu.add_command(label="Redo", command=self.redo)
        # ^ add_command returns None :(
        self.menu.add_cascade(label="Edit", menu=self.editMenu)
        self.editMenu.entryconfig("Undo", state=tk.DISABLED)
        self.editMenu.entryconfig("Redo", state=tk.DISABLED)

        self.helpMenu = tk.Menu(self.menu, tearoff=0)
        self.helpMenu.add_command(label="Dump to console", command=self.dump0)
        self.menu.add_cascade(label="File", menu=self.helpMenu)

        self.pack(fill=tk.BOTH, expand=True)
        # Doesn't work: padx=(10, 10), pady=(10, 10),
        # self.row_count = 0

        self.wide_width = 30

        self.arrow_images = []
        for arrow_path in arrow_paths:
            if not os.path.isfile(arrow_path):
                raise FileNotFoundError(arrow_path)
            else:
                print("loading {}".format(arrow_path))
            # See <https://www.pythontutorial.net/tkinter/tkinter-label/>
            arrow_image = tk.PhotoImage(file=arrow_path)
            # ^ doesn't work for png, so (based on rotocanvas):
            # arrow_image = ImageTk.PhotoImage(Image.open(arrow_path))
            self.arrow_images.append(arrow_image)

    def ask_open(self):
        directory = filedialog.askdirectory()
        if directory is not None:
            self.add_versions_in(directory)

    def on_var_changed(self, luid, key, var):
        echo1("on_var_changed: {}'s {} = {}"
              "".format(luid, key, json.dumps(var.get())))
        dat_i = self._project._find_where('luid', luid)
        if dat_i < 0:
            raise RuntimeError(
                "The data and project are out of sync:"
                " There is no action with luid {}."
                "".format(luid)
            )
        action = self._project._actions[dat_i]
        new_v = var.get()
        old_v = action[key]
        if old_v is not None:
            if type(old_v).__name__ != type(new_v).__name__:
                raise TypeError(
                    "key {} of luid {} was formerly {} {}"
                    " but the new value is {} {}."
                    "".format(key, luid,
                              type(old_v).__name__, json.dumps(old_v),
                              type(new_v).__name__, json.dumps(new_v))
                )
        if key in action:
            action[key] = new_v
            # TODO: Add an undo step but not for every character typed.
        else:
            ValueError(
                "on_var_changed doesn't account for the unknown key"
                " (self type is {}, luid={}, key={}, var.get()={})"
                "".format(type(self).__name__, json.dumps(luid),
                          json.dumps(key), json.dumps(var.get()))
            )
            # return False
        return self._project.save()

    def _append_row(self, action):
        '''
        Add an action to the end of the list view. The reason
        this method is private is that the action must also
        exist in self._project._actions at the same index so
        that the GUI and backend data match.

        The custom ".data" attribute of the row widget is set to
        "action".

        Sequential arguments:
        action -- If the action is a version
            (action['verb'] is in anewcommit.VERSION_VERBS),
            the action dict must contain the keys as
            returned by the anewcommit.new_version function.
            If the action is a version
            (action['verb'] is in anewcommit.TRANSITION_VERBS),
            the action dict must
            contain the keys as returned by the anewcommit.new_*
            functions other than new_version.
        '''
        # version action keys: path, mode, verb, commit
        # - where verb is in anewcommit.VERSION_VERBS
        # - where mode is in anewcommit.MODES
        # transition action keys: verb, commit
        # - where verb is in anewcommit.TRANSITION_VERBS
        luid = action['luid']
        this_template = None
        options = {}
        path = None
        name = None
        row = len(self._items)
        if action.get('verb') is None:
            raise ValueError("The verb is None")
        elif action.get('verb') in anewcommit.TRANSITION_VERBS:
            this_template = transition_template
            options['verb'] = anewcommit.TRANSITION_VERBS
            echo1("- transition: {}".format(action))
        elif action.get('verb') in anewcommit.VERSION_VERBS:
            this_template = version_template
            options['mode'] = anewcommit.MODES
            echo1("- version: {}".format(action))
            path = action.get('path')
            # name = None
            # if path is not None:
            name = os.path.split(path)[1]
            if path in self._id_of_path:
                raise ValueError(
                    "Path [{}] already exists at {}: {}"
                    "".format(row, self._index_of_path[path], path)
                )
            self._id_of_path[path] = luid
            self._index_of_path[path] = row
        else:
            raise ValueError(
                "The verb must be: {}"
                "".format(anewcommit.TRANSITION_VERBS
                          + anewcommit.VERSION_VERBS)
            )
        echo1("* adding row at {}".format(row))
        frame = tk.Frame(self.scrollable_frame)
        frame.data = action
        self._frame_of_luid[luid] = frame
        self._vars_of_luid[luid] = {}
        arrows_frame = ttk.Frame(
            frame,
        )
        arrows_frame.pack(side=tk.LEFT)
        arrow_c = "^"
        # arrow_f = self.move_up_where
        direction = -1
        for arrow_image in self.arrow_images:
            arrow_label = ttk.Label(
                arrows_frame,
                image=arrow_image,
                # command=lambda: arrow_f(luid),
                # compound='image',
                # text=arrow_c,
            )
            # arrow_label.bind("<Button-1>", lambda e: arrow_f(e, luid))
            arrow_label.bind(
                "<Button-1>",
                lambda e, y=direction: self.move_1(luid, y),
            )
            # ^ recieve event, but only send luid!
            # ^ y=direction forces early binding (otherwise always sends 1)
            # arrow_label['image'] = arrow_image
            arrow_label.pack(side=tk.TOP)
            arrow_c = "v"
            # arrow_f = self.move_down_where
            # ^ doesn't work due to late binding (both buttons go down),
            #   so use move_1 instead
            direction = 1

        button = ttk.Button(
            frame,
            text="+",
            width=2,
            command=lambda: self.insert_where(luid),
        )
        # button.grid(column=1, row=row, sticky=tk.W)
        button.pack(side=tk.LEFT, padx=(10, 0))
        button = ttk.Button(
            frame,
            text="-",
            width=2,
            command=lambda: self.remove_where(luid),
        )
        # button.grid(column=1, row=row, sticky=tk.W)
        button.pack(side=tk.LEFT, padx=(10, 0))

        results = dict_to_widgets(
            action,
            frame,
            template=this_template,
            warning_on_blank=get_verbose(),
        )
        for k, var in results['vs'].items():
            # self._key_of_name[var._name] = k
            # self._luid_of_name[var._name] = luid
            # self._var_of_name[var._name] = var
            # var.trace_add('write', lambda *args: self.on_var_changed(luid, k, results['vs'][k]))
            # ^ always has same k due to late binding
            #   (See <https://stackoverflow.com/questions/3431676/
            #   creating-functions-in-a-loop>)
            #   So force early binding:
            if python_mr > 2:
                # def on_this_var_changed(*args): #, luid=luid, k=k):
                def on_this_var_changed(tkVarID, param, event, luid=luid, k=k):
                    # ^ params force early binding (they come from
                    #   the outer scope, not the call)
                    # echo2("on_this_var_changed({},...)".format(args))
                    echo2("on_this_var_changed({},{},{},luid={},k={})"
                          "".format(tkVarID, param, event, luid, k))
                    try:
                        self.on_var_changed(luid, k, results['vs'][k])
                    except TypeError as ex:
                        messagebox.showerror("var_changed TypeError",
                                             str(ex))
                        # NOTE: type(ex).__name__ is always "Error"
                        raise ex
                    except ValueError as ex:
                        messagebox.showerror("var_changed ValueError",
                                             str(ex))
                        # NOTE: type(ex).__name__ is always "Error"
                        raise ex
            else:
                # def on_this_var_changed(*args, luid=luid, k=k):
                # ^ invalid syntax on Python 2 (See
                #   <https://stackoverflow.com/a/22436114/4541104>.
                #   Only Python 3 can put explicit keywords after `*args`).
                def on_this_var_changed(tkVarID, param, event, luid=luid, k=k):
                    '''
                    Params force early binding (they come from
                    the outer scope, not the call).

                    Sequential arguments:
                    tkVarID -- a string such as PY_VAR23
                    param -- unknown meaning, usually ''
                    event -- an event name (such as 'w' in Python2)
                    '''
                    # echo2("on_this_var_changed({},...)".format(args))
                    echo2("on_this_var_changed({},{},{},luid={},k={})"
                          "".format(tkVarID, param, event, luid, k))
                    try:
                        self.on_var_changed(luid, k, results['vs'][k])
                    except TypeError as ex:
                        messagebox.showerror("var_changed TypeError", str(ex))
                        raise ex
                    except ValueError as ex:
                        messagebox.showerror("var_changed ValueError", str(ex))
                        raise ex
            if python_mr >= 3:
                var.trace_add('write', on_this_var_changed)
            else:
                var.trace('wu', on_this_var_changed)
            # var.trace_add(['write', 'unset'], default_callback)
            # ^ In Python 2 it was trace('wu', ...)
        echo2("  - dict_to_widgets got {} widgets."
              "".format(len(results['widgets'])))
        for name, widget in results['widgets'].items():
            widget.pack(side=tk.LEFT)
            var = results['vs'][name]
            self._vars_of_luid[luid][name] = var
        frame.pack(fill=tk.X)
        # ^ must match the pack call in insert so layout is consistent
        # ^ expand=True: makes the row taller so rows fill the window
        self._items.append(frame)  # self.row_count += 1

    def update_undo(self):
        if self._project.has_undo():
            self.editMenu.entryconfig("Undo", state=tk.NORMAL)
        else:
            echo1("no undo (step_i={}, len={})"
                  "".format(self._project._undo_step_i,
                            len(self._project._undo_steps)))
            self.editMenu.entryconfig("Undo", state=tk.DISABLED)

        if self._project.has_redo():
            self.editMenu.entryconfig("Redo", state=tk.NORMAL)
        else:
            echo1("no redo (step_i={}, len={})"
                  "".format(self._project._undo_step_i,
                            len(self._project._undo_steps)))
            self.editMenu.entryconfig("Redo", state=tk.DISABLED)

    def undo(self):
        try:
            self._undo()
        except ValueError as ex:
            msg = str(ex)
            messagebox.showerror("Error", msg)

    def redo(self):
        try:
            self._undo(redo=True)
        except ValueError as ex:
            msg = str(ex)
            messagebox.showerror("Error", msg)

    def _undo(self, redo=False):
        echo1()
        echo1()
        echo1()
        do_s = "undo"
        if redo:
            do_s = "redo"
        echo1("_undo_step_i: {}".format(self._project._undo_step_i))
        echo1("_undo_steps:")
        for step in self._project._undo_steps:
            echo1("-")
            for ss in step:
                name = substep_to_str(ss)
                echo1("  - {}".format(name))
        results = None
        err = None
        echo1("* calling _project.undo")
        results, err = self._project.undo(redo=redo)
        title = "Warning"
        if results is None:
            title = "Error"
        else:
            offset = len(results['added']) - len(results['removed'])
            indices = results['added'] + results['removed']
            indices += results['swapped']
            indices += results['swapped_luids']
            if len(indices) < 1:
                if err is not None:
                    messagebox.showwarning("Warning (no rows affected)", err)
                else:
                    messagebox.showwarning("Warning", "No rows were affected.")
                return
            min_index = len(self._items) - 1
            for index in indices:
                if index < min_index:
                    min_index = index
            # start_index = min_index - offset

            result, err = self._reload_at(min_index, do_s)
        if err is not None:
            messagebox.showerror(title, err)

    def _reload_at(self, min_index, do_s):
        '''
        Reload a subset of GUI rows from the underlying data.

        Sequential arguments:
        min_index -- Start reloading at this index in the GUI which corresponds
            to an index in self._project.
        do_s -- Provide a string describing what is being done (such as "undo"
            or "redo") for debugging purposes.
        '''
        err = None
        title = "Warning"
        if min_index < 0:
            err = "The index {} is bad in _reload_at".format(min_index)
            title = "Error"
        else:
            old_len = len(self._items)
            # self.dump2()
            echo1("  len: {}".format(old_len))
            for index in reversed(range(min_index, old_len)):
                path = self.path_of_index(index)
                echo2("  * removing [{}] {} after {}".format(index, path, do_s))
                self._remove(index)
            # self.dump2()

            for index in range(min_index, len(self._project._actions)):
                echo2("  * re-adding [{}] after {}".format(index, do_s))
                self._append_row(self._project._actions[index])

        if err is not None:
            return None, err
        self.update_undo()
        return None, None

    def _clear(self):
        '''
        Remove all rows. This action is private since the items must also be
        removed from the backend data.
        '''
        for i in range(len(self._items)):
            self._items[i].pack_forget()
        del self._items[:]
        self._id_of_path = {}
        self._index_of_path = {}

    def path_of_index(self, index):
        for path, tryIndex in self._index_of_path.items():
            if tryIndex == index:
                return path
        return None

    def _remove(self, index):
        '''
        Remove a row at the given index. This action is private since the item
        should also be removed from the backend list.
        '''
        path = self.path_of_index(index)
        if path is None:
            echo1("  * index {} has no path record in the GUI (ok if not version)."
                  "".format(index))
        else:
            del self._id_of_path[path]
            del self._index_of_path[path]
        self._items[index].pack_forget()
        del self._items[index]
        # Remember to change _index_of_path starting at index
        # even if this one doesn't have a path:
        for i in range(index, len(self._items)):
            path = self._items[i].data.get('path')
            if path is not None:
                self._index_of_path[path] = i

    def remove_where(self, luid):
        index = self._project._find_where('luid', luid)
        i = self._find('luid', luid)
        echo1("* removing [{}] luid {} at {}".format(i, luid, index))
        if i != index:
            raise RuntimeError(
                "The visual data and backend project are out of sync:"
                " (actions[{}]['luid']={}, _items[{}].data['luid']={})"
                "".format(index, luid, i, luid)
            )
        path = self._items[i].data.get('path')
        if path is not None:
            old_luid = self._id_of_path[path]
            if old_luid != luid:
                raise RuntimeError(
                    "The visual row data & row button are out of sync:"
                    " (actions[{}]['luid']={},"
                    " _items[{}].data['luid']={})"
                    "".format(index, luid, i, luid)
                )
        self._project.remove(index)
        self.update_undo()
        self._remove(i)

    def _insert(self, index, action):
        '''
        Generate a new panel and insert it at the given index. This
        method is private since the action must already exist at the
        same index in the self._project._actions list so that both
        lists match.

        Sequential arguments:
        index -- Insert the item here in the list view.
        action -- Insert this action dictionary.
        '''
        more_items = []
        count = 0
        for i in range(index, len(self._items)):
            count += 1
            # path = self.path_of_index(i)
            self._items[i].pack_forget()
            more_items.append(self._items[i])
        # self._items = self._items[:index]
        old_len = len(self._items)
        tmp_id_of_path = {}
        for i in reversed(range(index, old_len)):
            # Do them individually so _index_of_path and _id_of_path update.
            path = self.path_of_index(i)
            if path is not None:
                luid = self._id_of_path[path]
                tmp_id_of_path[path] = luid
            self._remove(i)
        self._append_row(action)
        # ^ handles: self._id_of_path[path], self._index_of_path[path]
        #   (Don't modify other entries since removed rows will be re-added
        #   immediately below)
        # luid = action['luid']
        # echo1("* appended row {} luid {}".format(index, luid))
        tmp_index_of_path = {}
        for i in range(len(more_items)):
            item = more_items[i]
            path = item.data.get('path')
            row = len(self._items)
            if path is not None:
                tmp_index_of_path[path] = row
            item.pack(fill=tk.X)
            # echo1("* dequeued luid {}".format(more_items[i].data['luid']))
            self._items.append(item)
        for path, luid in tmp_id_of_path.items():
            # name = os.path.split(path)[1]
            row = tmp_index_of_path[path]
            if path in self._id_of_path:
                raise ValueError("Path [{}] already exists for id {}: {}"
                                 "".format(row, self._id_of_path[path],
                                           path))
            if path in self._index_of_path:
                raise ValueError("Path [{}] already exists at {}: {}"
                                 "".format(row, self._index_of_path[path],
                                           path))
            self._id_of_path[path] = luid
            self._index_of_path[path] = row
            old_luid = self._items[row].data['luid']
            if old_luid != luid:
                raise ValueError("Path [{}] luid {} should be {}"
                                 "".format(row, luid, old_luid))

    def swap(self, index, other_index):
        # luid = self._items[index]['luid']
        # other_luid = self._items[other_index]['luid']
        # self._project.swap(luid, other_luid)
        self._project.swap(index, other_index)
        min_index = index
        if other_index < min_index:
            min_index = other_index
        title = "Swap Rows Error"
        result, err = self._reload_at(min_index, "swap")
        if err is not None:
            err = "Swapping at {} and {}\n\n".format(index, other_index) + err
            messagebox.showerror(title, err)

    def move_1(self, luid, direction):
        if direction == -1:
            self.move_up_where(luid)
        elif direction == 1:
            self.move_down_where(luid)
        else:
            raise ValueError(
                "move_1 must recieve -1 or 1 for direction but got {}"
                "".format(direction)
            )

    def move_up_where(self, luid):
        index = self._find('luid', luid)
        if index < 0:
            messagebox.showerror("Error", "id {} doesn't exist.".format(luid))
            return
        other_index = index - 1
        if other_index < 0:
            echo0("Can't move first element up.")
            return
        other_luid = self._project._actions[other_index]['luid']
        self.swap(index, other_index)

    def move_down_where(self, luid):
        index = self._find('luid', luid)
        if index < 0:
            messagebox.showerror("Error", "id {} doesn't exist.".format(luid))
            return
        other_index = index + 1
        if other_index >= len(self._items):
            echo0("Can't move last element down.")
            return
        other_luid = self._project._actions[other_index]['luid']
        self.swap(index, other_index)

    def _find(self, name, value):
        for i in range(len(self._items)):
            item = self._items[i]
            # if item.data.get(name) == value:
            if item.data[name] == value:
                return i
        return -1

    def insert_where(self, luid):
        '''
        Insert an action into the backend data and the UI at the index where
        luid matches. Set action['commit'] to True.
        '''
        index = self._project._find_where('luid', luid)
        if index < 0:
            msg = ("There is no luid {} in actions."
                   "".format(luid))
            messagebox.showerror("Error", msg)
            raise ValueError(msg)
        item_i = self._find('luid', luid)
        if item_i < 0:
            msg = ("There is no luid {} in items."
                   "".format(luid))
            messagebox.showerror("Error", msg)
            raise ValueError(msg)
        if item_i != index:
            msg = ("The data and project are out of sync:"
                   " (actions[{}]['luid']={}, _items[{}].data['luid']={})"
                   "".format(index, luid, item_i, luid))
            messagebox.showerror("Error", msg)
            raise RuntimeError(msg)
        action = None
        # next_action = self._project.get_action(luid)
        next_action = self._project._actions[index]
        next_is_ver = next_action['verb'] in anewcommit.VERSION_VERBS
        '''
        prev_is_ver = False
        if index > 0:
            prev_action = self._project._actions[index-1]
            prev_is_ver = prev_action['verb'] in anewcommit.VERSION_VERBS
        '''
        if next_is_ver or (item_i == 0):
            action = anewcommit.new_pre_process()
        else:
            action = anewcommit.new_post_process()
        try:
            self._project.insert(index, action)
            self.update_undo()
            self._insert(item_i, action)
        except ValueError as ex:
            messagebox.showerror("Error", str(ex))

    def set_commit(self, luid, on):
        self._project.set_commit(luid, on)

    def set_verb(self, luid, verb):
        self._project.set_verb(luid, verb)

    def append_transition(self):
        transition_action = self._project.add_transition('no_op')
        self.update_undo()
        self._append_row(transition_action)

    def append_source(self, path):
        try:
            version_action = self._project.add_version(path)
            self.update_undo()
            self._append_row(version_action)
        except (ValueError, TypeError) as ex:
            if verbose:
                raise ex
            messagebox.showerror("Error", str(ex))
            return False
        return True

    def _init_title_row(self):
        if self._added_title_row:
            return
        self._added_title_row = True
        frame = tk.Frame(self.scrollable_frame)
        for caption in actions_captions:
            widget = ttk.Label(
                frame,
                text=caption,
            )
            widget.pack(side=tk.LEFT)
        frame.pack(fill=tk.X)

    def append_version(self, path):
        return self.append_source(path)

    def load_project(self, path):
        if os.path.getsize(path) == 0:
            os.remove(path)
            return False
        self._init_title_row()
        self._clear()
        self._project = ANCProject()
        result, err = self._project.load(path)
        if result:
            self.update_undo()
            if err is not None:
                # result is ok, but the file must have been repaired if msg
                # is not None.
                self._project.save()
                messagebox.showerror(
                    "Error",
                    'The project file "{}" was incorrectly formatted'
                    ' and repairs were attempted: \n{}'
                    ''.format(self._project.path, err)
                )
            for action in self._project._actions:
                try:
                    self._append_row(action)
                except (ValueError, TypeError) as ex:
                    msg = str(ex)
                    echo0("action: {}".format(action))
                    messagebox.showerror("Error", msg)
            self.dump1()
            return True
        else:
            messagebox.showerror(
                "Error",
                'The project file "{}" is incorrectly formatted and will be'
                ' overwritten on the next change due to the following error:'
                ' {}'.format(path, err)
            )
        return False

    def dump(self, level):
        global _GUI_DUMP
        global _BACKEND_DUMP
        '''
        Sequential arguments:
        level -- Set what level of verbosity this dump affects.
        '''
        echos[level]("DUMP len: {}".format(len(self._items)))
        _GUI_DUMP = []
        for i in range(len(self._items)):
            path = self._items[i].data.get('path')
            _GUI_DUMP.append(self._items[i].data.get('luid'))
            name = path
            if path is not None:
                name = os.path.split(path)[1]
            echos[level]("- data of widget [{}]: path~={}"
                         "".format(i, name))
            path = self.path_of_index(i)
            name = path
            if path is not None:
                name = os.path.split(path)[1]
            echos[level]("  - path~={}".format(name))
            if path is not None:
                index = self._index_of_path[path]
                echos[level]("  - index {}".format(index))

        for path, index in self._index_of_path.items():
            name = path
            if path is not None:
                name = os.path.split(path)[1]
            echos[level]("* index [{}] = {}"
                  "".format(name, index))
        for path, luid in self._id_of_path.items():
            name = path
            if path is not None:
                name = os.path.split(path)[1]
            echos[level]("* luid for [{}] = {}"
                  "".format(name, luid))

        echos[level](
            "BACKEND data len: {}"
            "".format(len(self._project._actions))
        )
        _BACKEND_DUMP = []
        for index in range(0, len(self._project._actions)):
            path = self._project._actions[index].get('path')
            name = path
            luid = self._project._actions[index].get('luid')
            _BACKEND_DUMP.append(luid)
            known_luid = self._id_of_path.get(path)
            i = self._index_of_path.get(path)
            if path is not None:
                name = os.path.split(path)[1]
            echos[level]("* item for [{}] id {} (known as {}) at {} = {}"
                         "".format(index, luid, known_luid, i, name))

    def dump0(self):
        self.dump(0)

    def dump1(self):
        self.dump(1)

    def dump2(self):
        self.dump(2)

    def add_versions_in(self, path):
        if self._project is None:
            self._project = ANCProject()
        else:
            self._project.clear()
            self.update_undo()
        self._project.project_dir = path
        count = 0
        self._init_title_row()
        failPaths = []
        for sub in os.listdir(path):
            subPath = os.path.join(path, sub)
            if not os.path.isdir(subPath):
                continue
            result = self.append_version(subPath)
            if not result:
                failPaths.append(subPath)
                break
            count += 1
        echo1("Added {}".format(count))
        for failPath in failPaths:
            echo1('* failed to add {}'.format(failPath))
        self.dump1()

    def exitProgram(self):
        root.destroy()


def usage():
    echo0(__doc__)


def main():
    global root
    root = tk.Tk()
    root.geometry("500x600")
    root.minsize(200, 100)
    root.title("anewcommit")
    versions_path = None
    bool_names = ['--verbose']
    settings = {}
    for argi in range(1, len(sys.argv)):
        arg = sys.argv[argi]
        if arg.startswith("--"):
            option_name = arg[2:]
            if arg == "--verbose":
                set_verbose(1)
            elif arg == "--debug":
                set_verbose(2)
            elif arg in bool_names:
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
        echo0("* enabled verbose logging to standard error")
    echo1("versions_path: {}".format(versions_path))
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
        echo0("* available ttk themes: {}".format(style.theme_names()))
        echo0("* current theme: {}".format(style.theme_use()))

    app = MainFrame(root, settings=settings)
    if versions_path is not None:
        tryProject = os.path.join(versions_path, "anewcommit.json")
        loaded = False
        if os.path.isfile(tryProject):
            loaded = app.load_project(tryProject)
        if not loaded:
            app.add_versions_in(versions_path)

    root.mainloop()
    # (Urban & Murach, 2016, p. 515)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        test_case_dir = os.path.join(profile, "www.etc", "TCS", "VERSIONS")
        # test_case_dir = os.path.join(profile, "tmp")
        if os.path.isdir(test_case_dir):
            sys.argv.append(test_case_dir)
            set_verbose(True)
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
