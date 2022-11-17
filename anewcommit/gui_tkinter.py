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
import subprocess
from datetime import (
    datetime,
    # timedelta,
)
from dateutil import tz
# tz.tzlocal()  # as per <https://stackoverflow.com/a/61124241/4541104>
# then as per <https://stackoverflow.com/a/7065242/4541104>:
# dt.replace(tzinfo=tz.tzlocal())
# but it says you can also do:
# import pytz
# dt2 = pytz.utc.localize(dt1)


if sys.version_info.major >= 3:
    from tkinter import messagebox
    from tkinter import filedialog
    from tkinter import simpledialog
    import tkinter as tk
    from tkinter import ttk
    # from tkinter import tix
else:
    # Python 2
    import tkMessageBox as messagebox
    import tkFileDialog as filedialog
    import tkSimpleDialog as simpledialog
    import Tkinter as tk
    import ttk
    # import Tix as tix

# import math

myPath = os.path.realpath(__file__)
myDir = os.path.dirname(myPath)
# staticDir = os.path.join(myDir, "static")
# imagesDir = os.path.join(staticDir, "images")
# ^ unused as of commit titled
#   "Clean up the interface by replacing per-row interaction ..."

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
    get_verbosity,
    set_verbosity,
    profile,
    substep_to_str,
    s2or3,
    newest_file_dt_in,
    parse_statement,
    statement_to_caption,
    open_file,
    split_root,
    split_subs,
)

echos = []
echos.append(echo0)
echos.append(echo1)
echos.append(echo2)

from anewcommit.scrollableframe import SFContainer

verbosity = get_verbosity()

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
transition_field_order = ['commit', 'date', 'verb', 'command']
version_field_order = ['commit', 'date', 'mode', 'name']

# See
# <docs.python.org/3/library/datetime.html#strftime-and-strptime-format-codes>
dt_format =  "%Y-%m-%d %H:%M:%S"
date_format =  "%Y-%m-%d"

default_field_widths = {}
selector_width = verb_width
if mode_width > selector_width:
    selector_width = mode_width
default_field_widths['verb'] = selector_width
default_field_widths['mode'] = selector_width
default_field_widths['date'] = len(datetime.now().strftime(date_format))
# default_field_widths['commit'] = 5

conditional_formatting = {
    'verb': {
        '=get_version': {
            'readonly': True,
        },
    },
}
# TODO: (?) Implement conditional_formatting (not necessary if using
#   separate version_template_fields below).

_version_template_fields = {
    'luid': {
        'hide': True,
    },
    'path': {
        'hide': True,
    },
    'date': {
        'maxchars': default_field_widths['date'],
        'widget': 'Entry',
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
    'field_widths': default_field_widths,
}
# ^ modified later to include lambdas calling class methods.

version_template = {
    'fields': _version_template_fields,
    'field_order': version_field_order,
    'field_widths': default_field_widths,
}
# ^ modified later to include lambdas calling class methods.

_GUI_DUMP = []
_BACKEND_DUMP = []

def to_style_key(luid, prefix="Row", suffix=".TFrame"):
    return "{}{}{}".format(prefix, luid, suffix)


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
            if sys.version_info.major < 3:
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
    - global verbosity (usually 0)
    - See imports for more.

    Private Attributes:
    _project -- This is the currently loaded ANCProject instance.
    _frame_of_luid -- _frame_of_luid[luid] is the row, in the form of a
        frame, that represents the action (verb can be "get_version" or
        a transition verb) uniquely identified by a luid.
    _vars_of_luid -- _vars_of_luid[luid][key] is the widget of
        the action for the action uniquely identified by luid.
    '''
    def __init__(self, parent, settings=None):
        all_settings = copy.deepcopy(ANCProject.default_settings)
        self._added_title_row = False
        if settings is not None:
            # if is_truthy(settings.get('verbosity')):
            #     # self.settings['verbosity'] = 1
            #     verbosity = 1
            for k, v in settings.items():
                all_settings[k] = v
        self.settings = all_settings
        self.headings = []
        self.heading_captions = {}

        self._project = None
        self.parent = parent
        self.last_path = profile
        # from pathlib import Path
        # self.last_path = Path.home()
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
        # self.style.configure('MainFrame.TFrame', background='gray')
        # ^ See <https://www.pythontutorial.net/tkinter/ttk-style/>.
        #   The following didn't work:
        #   See <http://infohost.nmt.edu/tcc/help/pubs/tkinter/web/
        #   ttk-style-layer.html>
        #   via <https://stackoverflow.com/a/16639454>
        self._selected_luid = None
        self._vars_of_luid = {}
        self._frame_of_luid = {}
        self._key_of_name = {}
        self._luid_of_name = {}
        self._var_of_name = {}
        self.menu = tk.Menu(self.parent)
        self.parent.config(menu=self.menu)
        self.next_id = 0
        self._items = []
        self.selection_color = "black"
        self.bg_color = None
        self.prefill_date = None
        self.date_fmt = "%Y-%m-%d"

        self.fileMenu = tk.Menu(self.menu, tearoff=0)
        self.fileMenu.add_command(label="Add a source version...",
                                  command=self.ask_open)
        self.fileMenu.add_command(label="Add multiple source versions in...",
                                  command=self.ask_open_all)
        self.fileMenu.add_command(label="Add a statement (process a source)...",
                                  command=self.ask_statement)
        self.fileMenu.add_command(label="Mark maximum file date...",
                                  command=self.ask_mark_max_date_before)
        self.fileMenu.add_command(label="Show latest file",
                                  command=self.on_mc_show_latest_file)
        self.fileMenu.add_command(label="Exit", command=self.exitProgram)
        self.menu.add_cascade(label="File", menu=self.fileMenu)

        self.batchMenu = tk.Menu(self.menu, tearoff=0)
        self.batchMenu.add_command(label="Add a statement where applicable...",
                                   command=self.ask_statement_all_applicable)
        self.batchMenu.add_command(label="Mark maximum file date...",
                                  command=self.ask_mark_all_max_date_before)
        self.menu.add_cascade(label="Batch", menu=self.batchMenu)

        self.editMenu = tk.Menu(self.menu, tearoff=0)
        self.editMenu.add_command(label="Undo", command=self.undo)
        self.editMenu.add_command(label="Redo", command=self.redo)
        self.editMenu.add_command(label="Move Up", command=self.on_mc_move_up)
        self.editMenu.add_command(label="Move Down",
                                  command=self.on_mc_move_down)
        self.editMenu.add_command(label="Insert", command=self.on_mc_insert)
        self.editMenu.add_command(label="Remove", command=self.on_mc_remove)
        # ^ add_command returns None :(
        self.menu.add_cascade(label="Edit", menu=self.editMenu)
        self.editMenu.entryconfig("Undo", state=tk.DISABLED)
        self.editMenu.entryconfig("Redo", state=tk.DISABLED)

        self.viewMenu = tk.Menu(self.menu, tearoff=0)
        self.viewMenu.add_command(label="View step in Sunflower",
                                  command=self.on_mc_view_step)
        self.viewMenu.add_command(label="View changes in Sunflower",
                                  command=self.on_mc_view_changes_sunflower)
        self.viewMenu.add_command(label="View changes in Meld",
                                  command=self.on_mc_view_changes_meld)
        self.menu.add_cascade(label="View", menu=self.viewMenu)

        self.helpMenu = tk.Menu(self.menu, tearoff=0)
        self.helpMenu.add_command(label="Dump to console", command=self.dump0)
        self.menu.add_cascade(label="Help", menu=self.helpMenu)

        self.pack(fill=tk.BOTH, expand=True)
        # Doesn't work: padx=(10, 10), pady=(10, 10),
        # self.row_count = 0

        self.wide_width = 30

    def ask_open_all(self):
        directory = filedialog.askdirectory(
            initialdir=self.last_path,
        )
        if directory is None:
            return
        echo1()
        echo1("directory={}".format(directory))
        if len(directory) == 0:
            # can be `()` (emtpy tuple).
            return
        elif directory.strip() == "":
            return
        self.add_versions_in(directory)

    def ask_open(self):
        directory = filedialog.askdirectory(
            initialdir=self.last_path,
        )
        if directory is None:
            return
        echo1()
        echo1("directory={}".format(directory))
        if len(directory) == 0:
            # can be `()` (emtpy tuple).
            return
        elif directory.strip() == "":
            return

        if not self.append_source(directory):
            messagebox.showerror("Error", 'Adding the directory failed.')
        self.last_path = directory


    def ask_statement_applicable(self, do_all=False):
        default_str = ""
        selected_i = None
        if not do_all:
            if self._selected_luid is None:
                messagebox.showerror("Error", "Select a source first.")
                return
            selected_i = self._find('luid', self._selected_luid)
            if selected_i < 0:
                raise RuntimeError("selected luid {} doesn't exist."
                                   "".format(self._selected_luid))
        statement = simpledialog.askstring(
            "Add a statement",
            ('To use a folder such as "Primary Site" if present in the source,'
             ' enter a statement such as: use "Primary Site" as www'),
            initialvalue=default_str,
        )
        if len(statement.strip()) == 0:
            statement = None
        if statement is None:
            # Cancel button was pressed (or blank became None above)
            return
        try:
            self.mark_if_has_folder(statement, selected_i=selected_i)
        except ValueError as ex:
            messagebox.showerror("Error", str(ex))
            raise ex

    def ask_statement_all_applicable(self):
        self.ask_statement_applicable(do_all=True)

    def ask_statement(self):
        self.ask_statement_applicable(do_all=False)

    def ask_mark_all_max_date_before(self):
        self.ask_mark_max_date_before(do_all=True)

    def ask_mark_max_date_before(self, do_all=False):
        selected_i = None
        result_path = None
        result_date = None
        if not do_all:
            if self._selected_luid is not None:
                luid = self._selected_luid
                selected_i = self._project._find_where('luid', luid)
                if selected_i < 0:
                    raise ValueError("LUID {} was not found.".format(luid))
            else:
                messagebox.showerror("Error", "You must select a row first.")
                return

        max_date_str = simpledialog.askstring(
            "Mark with maximum date",
            "What date is too new (YYYY-MM-DD or leave blank)?"
        )
        if max_date_str is None:
            # The "Cancel" button was pressed.
            return
        try:
            result_path, result_date = self.mark_max_date_before(
                max_date_str,
                selected_i=selected_i,
            )
            if result_path is not None:
                yes = messagebox.askyesno(
                    "Newest file in range", 'Open "{}" from {}?'
                    ''.format(result_path, result_date)
                )
                if yes:
                    open_file(result_path)
        except ValueError as ex:
            self.prefill_date = max_date_str
            if "time data" in str(ex) or "unconverted data" in str(ex):
                messagebox.showerror("Error", str(ex))
                result_path, result_date = self.ask_mark_max_date_before(
                    do_all=do_all,
                )
            else:
                raise ex
        return result_path, result_date

    def mark_max_date_before(self, too_new_date_str, selected_i=None):
        if too_new_date_str is not None:
            if too_new_date_str.strip() == "":
                too_new_date_str = None
        too_new_dt = None
        result_path = None
        result_date = None
        if too_new_date_str is not None:
            too_new_dt = datetime.strptime(too_new_date_str, self.date_fmt)
            too_new_dt = too_new_dt.replace(tzinfo=tz.tzlocal())
        try:
            ranges = self._project.get_ranges()
        except Exception as ex:
            messagebox.showerror("Error", str(ex))
            raise ex
        if selected_i is not None:
            r = [selected_i]
            ranges = [r]
        echo0("Processing {} version(s)".format(len(ranges)))
        count = 0
        done = 0
        min_index = len(self._project._actions)
        if selected_i is not None:
            r = [selected_i]
            ranges = [r]
            echo0("selected_i={}".format(selected_i))
        elif self._selected_luid is not None:
            echo0("WARNING: self._selected_luid but no selected_i")
        for r in ranges:
            version_i, _ = self._project.get_affected(r[0])
            if selected_i is not None:
                if selected_i != version_i:
                    messagebox.showerror(
                        "Error",
                        "This operation only works on a source.",
                    )
                    return
            echo0("Processing version index {} in {}"
                  "".format(version_i, _))
            action = self._project._actions[version_i]
            parent = action['path']
            sources = []
            statements = action.get('statements')
            if statements is not None:
                echo1("len(statements)={}".format(len(statements)))
                for statement in statements:
                    command = parse_statement(statement)
                    if 'destination' not in command:
                        continue
                    source = command.get('source')
                    if source is None:
                        continue
                        # There is no source, so the whole thing is the source
                        # (there shouldn't be any other "use" statements in
                        # this case).
                    sources.append(os.path.join(parent, source))
                    echo1("source={}".format(source))
            if len(sources) == 0:
                # If there are no specified subprojects in the source,
                #   use the entire source:
                sources = [parent]
            echo1("len(sources)={}".format(len(sources)))

            newest_path = None
            newest_dt = None
            for source in sources:
                this_path, this_dt = newest_file_dt_in(
                    source,
                    too_new_dt=too_new_dt,
                )
                if this_dt is None:
                    continue
                if (newest_dt is None) or (this_dt > newest_dt):
                    newest_dt = this_dt
                    newest_path = this_path
            if newest_dt is not None:
                date_str = newest_dt.strftime(self.date_fmt)
                if len(date_str.strip()) == 0:
                    date_str = "(bad date)"
            else:
                date_str = "(no date in range)"

            if action.get('date') != date_str:
                if version_i < min_index:
                    min_index = version_i
            action['date'] = date_str
            action['newest_path'] = newest_path
            result_path = newest_path
            result_date = date_str
            done += 1

        if min_index < len(self._project._actions):
            self._project.save()
            self._reload_at(min_index, "mark date")

        if (count > 0) and  (done < count):
            messagebox.showinfo(
                "Info",
                "{}/{} already marked".format(count-done, count),
            )
        return result_path, result_date

    def mark_if_has_folder(self, statement, selected_i=None):
        '''
        Add a statement to the selection (or all if selected_i is None)
        only if the source contains the relative source in the given statement.
        '''
        command = None
        try:
            command = parse_statement(statement)
        except Exception as ex:
            messagebox.showerror("Error", str(ex))
            return

        ranges = self._project.get_ranges()
        count = 0
        done = 0
        relPath = command.get('source')
        if relPath is not None:
            if relPath.strip() == "":
                relPath = None
            if relPath is None:
                yes = messagebox.askyesno(
                    "Confirm Mark All",
                    'There is no source param. Mark all unconditionally?',
                )
                if not yes:
                    return
        # else it is a "use as <destination>" statement
        # so don't check for a folder, just use it as the
        # given destination.

        if selected_i is not None:
            r = [selected_i]
            ranges = [r]
            echo1("selected_i={}".format(selected_i))
        elif self._selected_luid is not None:
            echo0("WARNING: self._selected_luid but no selected_i")

        for r in ranges:
            version_i, _ = self._project.get_affected(r[0])
            if selected_i is not None:
                if selected_i != version_i:
                    messagebox.showerror(
                        "Error",
                        "This operation only works on a source.",
                    )
                    return
            action = self._project._actions[version_i]
            parent = action['path']
            subPath = None
            if relPath is not None:
                subPath = os.path.join(parent, relPath)
                if not os.path.isdir(subPath):
                    continue
            luid = action['luid']
            count += 1
            if not self._project.append_statement_where(luid, statement):
                continue
            done += 1
            widget = ttk.Label(
                self._items[version_i],
                text=statement_to_caption(command),
            )
            widget.pack(side=tk.LEFT)
            widget.bind(
                "<Button>",
                lambda e, l=luid, st=statement: self.on_click_sub(e, l, st),
            )
            # ^ also done in _append_row

        if (count > 0) and  (done < count):
            messagebox.showinfo(
                "Info",
                "{}/{} already marked".format(count-done, count),
            )

    def on_mc_show_latest_file(self):
        if self._selected_luid is None:
            messagebox.showerror("Error", "You must select a source first.")
            return
        selected_i = self._project._find_where('luid', self._selected_luid)
        version_i, _ = self._project.get_affected(selected_i)
        if version_i != selected_i:
            messagebox.showerror(
                "Error",
                "This operation only works on a source.",
            )
            return
        action = self._project._actions[version_i]
        newest_path = action.get('newest_path')
        if newest_path is None:
            messagebox.showerror(
                "Error",
                'You must first run "Mark maximum file date..."',
            )
            return
        answer = messagebox.askokcancel(
            "Show latest file",
            newest_path,
        )
        if answer is not True:
            return
        in_dir = os.path.dirname(newest_path)
        open_file(in_dir)


    def on_click_row(self, luid):
        self.select_luid(luid)

    def on_click_date(self, luid):
        self.on_click_row(luid)

    def on_right_click_sub(self, luid, statement):
        min_index = self._find('luid', luid)
        yes = messagebox.askyesno(
            "clicked directory",
            'Unmark {}?'.format(statement),
        )
        if yes:
            self._project.remove_statement_where(luid, statement)
            self._reload_at(min_index, "remove sub")
        self.on_click_row(luid)

    def on_click_sub(self, event, luid, statement):
        if event.num == 1:
            self.on_left_click_sub(luid, statement)
        else:
            self.on_right_click_sub(luid, statement)
        self.on_click_row(luid)

    def on_left_click_sub(self, luid, statement, skip_partial_count=0):
        '''
        Compare the sources from two "use" statements where
        their roots of their destinations match.

        If a destination includes a subfolder (len(split_subs(dst))>1),
        the matching code assumes that the subfolder is real on copies
        that do not include a subfolder. In other situations, the
        structure of the source isn't checked for either of the
        "use" statements.

        Keyword arguments:
        skip_partial_count -- Skip this many partial matches (such as
            matching primary/about to primary or vise versa). Normally this is
            only set if the user presses "No" to use a partial match.
        '''
        if not statement.startswith("use "):
            messagebox.showerror(
                "Nothing to do",
                'There is no "use" statement so there is nothing to open.'
            )
            return
        yes = messagebox.askyesno(
            "anewcommit",
            "Do you want to merge actions before comparing?"
        )
        compare_mode = "source"
        if yes is True:
            compare_mode = "destination"
        I_FROM = 0
        I_TO = 1
        cmp_cmds = [None, None]
        cmp_cmds[I_TO] = parse_statement(statement)
        if 'destination' not in cmp_cmds[I_TO]:
            messagebox.showerror(
                "Nothing to do",
                'There is no destination in the statement.'
            )
            return

        to_i = self._find('luid', luid)

        to_action = self._project._actions[to_i]
        cmp_paths = [None, None]
        cmp_paths[I_TO] = to_action['path']
        to_source = cmp_cmds[I_TO].get('source')
        # ^ RELATIVE, so added to 'path' later
        if to_source is not None:
            cmp_paths[I_TO] = os.path.join(cmp_paths[I_TO], to_source)
        cmp_src_lists = [None, None]
        cmp_src_lists[I_TO] = []
        if to_source is not None:
            cmp_src_lists[I_TO] = split_subs(to_source)
        cmp_dst_lists = [None, None]
        to_dst = cmp_cmds[I_TO]['destination']
        cmp_dst_lists[I_TO] = split_subs(to_dst)
        cmp_roots = [None, None]
        cmp_roots[I_TO] = cmp_dst_lists[I_TO][0]
        cmp_src_higher_lists = [None, None]
        cmp_src_higher_lists[I_TO] = split_subs(cmp_paths[I_TO])

        from_action = None
        cmp_paths[I_FROM] = None
        # from_i = None
        partial_count = 0
        SMALL_IDX = -1
        BIG_IDX = -1
        for try_i in reversed(range(0, to_i)):
            try_action = self._project._actions[try_i]
            try_statements = try_action.get('statements')
            if try_statements is None:
                continue
            for try_statement in try_statements:
                try_command = None
                try:
                    try_command = parse_statement(try_statement)
                except ValueError as ex:
                    echo0("'{}' failed since: {}".format(try_statement, ex))
                    continue
                from_dst = try_command.get('destination')
                if from_dst is None:
                    continue

                cmp_dst_lists[I_FROM] = split_subs(from_dst)
                # from_dst_sub
                # to_dst_sub
                cmp_roots[I_FROM] = cmp_dst_lists[I_FROM][0]
                min_len = len(cmp_dst_lists[I_FROM])
                to_dst_subs = []
                from_dst_subs = []
                if len(cmp_dst_lists[I_TO]) < min_len:
                    SMALL_IDX = I_TO
                    BIG_IDX = I_FROM
                    min_len = len(cmp_dst_lists[I_TO])
                    to_dst_subs = []
                    from_dst_subs = cmp_dst_lists[I_FROM][min_len:]
                elif len(cmp_dst_lists[I_TO]) > min_len:
                    SMALL_IDX = I_FROM
                    BIG_IDX = I_TO
                    to_dst_subs = cmp_dst_lists[I_TO][min_len:]
                    from_dst_subs = []
                from_src = try_command.get('source')
                # ^ RELATIVE, so added to 'path' later
                cmp_src_lists[I_FROM] = []
                if from_src is not None:
                    cmp_src_lists[I_FROM] = split_subs(from_src)

                if cmp_roots[I_TO] == cmp_roots[I_FROM]:
                    cmp_paths[I_FROM] = try_action['path']
                    if from_src is not None:
                        cmp_paths[I_FROM] = os.path.join(cmp_paths[I_FROM], from_src)
                    if to_dst_subs != from_dst_subs:
                        # both are not None: to_dst_subs, from_dst_subs
                        partial_count += 1
                        if skip_partial_count >= partial_count:
                            # The user said to look for an older copy.
                            continue

                        partial_msg = 'Do you want to use the partial copy'
                        if len(from_dst_subs) > len(to_dst_subs):
                            partial_msg = ('Do you want to compare the partial'
                                           ' copy to the full copy')
                        if skip_partial_count > 0:
                            partial_msg = ('No matching subdirectory'
                                           ' was available. ' + partial_msg)
                        yes = messagebox.askyesnocancel(
                            'Partial Copy Detected',
                            (partial_msg
                             + ' "{}" (press "No" to skip and look for copy with same scope)?'
                             ''.format(try_action['name']))
                        )
                        if yes is True:
                            pass
                            # fall through and use the match
                        elif yes is False:
                            return self.on_left_click_sub(
                                luid,
                                statement,
                                skip_partial_count=skip_partial_count+1,
                            )
                        elif yes is None:
                            # Cancel yields None
                            return
                        else:
                            raise RuntimeError("{} is an unknown response"
                                               "".format(yes))

                        # continue and consider it a match.
                        cmp_src_higher_lists[I_FROM] = split_subs(cmp_paths[I_FROM])
                        # if len(to_dst_subs) > 0:
                        if BIG_IDX > -1:
                            big_sub_path_parts = cmp_dst_lists[BIG_IDX][1:]
                            # Look for the deeper directory from big in small:
                            try_small_src_sub = big_sub_path_parts[0]
                            if len(big_sub_path_parts) > 1:
                                try_small_src_sub = os.path.join(
                                    # [cmp_paths[SMALL_IDX]]+cmp_src_lists[BIG_IDX][1:],
                                    *big_sub_path_parts
                                )
                            try_small_src_sub_path = os.path.join(
                                cmp_paths[SMALL_IDX],
                                try_small_src_sub
                            )
                            # ^ See "Reconstruct FROM on TO"
                            #   in projects/development.md
                            if not os.path.isdir(try_small_src_sub_path):
                                echo0('The deeper path doesn\'t exist'
                                      ' in the previous version:')
                            if ((not os.path.isdir(try_small_src_sub_path))
                                    or (get_verbosity()>1)):
                                echo0('- big_sub_path_parts="{}'.format(big_sub_path_parts))
                                echo0('- try_small_src_sub_path="{}"'.format(try_small_src_sub_path))
                                echo0('- try_small_src_sub="{}'.format(try_small_src_sub))
                                echo0('- cmp_src_lists[SMALL_IDX]="{}'.format(cmp_src_lists[SMALL_IDX]))
                                echo0('- cmp_src_lists[BIG_IDX]="{}'.format(cmp_src_lists[BIG_IDX]))
                                echo0('- cmp_dst_lists[SMALL_IDX]="{}'.format(cmp_dst_lists[SMALL_IDX]))
                                echo0('- cmp_dst_lists[BIG_IDX]="{}'.format(cmp_dst_lists[BIG_IDX]))
                                echo0('- cmp_paths[SMALL_IDX]="{}'.format(cmp_paths[SMALL_IDX]))
                            if not os.path.isdir(try_small_src_sub_path):
                                # It is not a match, so keep looking.
                                continue
                            cmp_paths[SMALL_IDX] = try_small_src_sub_path
                            # to_src_subs = cmp_src_higher_lists[BIG_IDX][]

                        # if cmp_roots[I_FROM] != from_dst:

                    from_action = try_action
                    # ^ Setting this ends the loop, but instead of using it,
                    #   cmp_paths will be used for compare_paths and cmp_paths
                    #   was truncated if the match was partial.
                    break
            if from_action is not None:
                break
        if from_action is None:
            messagebox.showinfo(
                "Info",
                ("{} is the 1st version of {} so there is nothing to compare."
                 "".format(to_action['name'], cmp_cmds[I_TO]['destination'])),
            )
            return
        if cmp_paths[I_FROM] is None:
            raise RuntimeError(
                "cmp_paths[I_FROM] is None, but the missing path case"
                " should have been handled further up."
            )
        if cmp_paths[I_TO] is None:
            raise RuntimeError(
                "cmp_paths[I_TO] is None, but the missing path case"
                " should have been handled further up."
            )

        if compare_mode == "destination":
            from_dst = self._project.generate_cache(from_action['luid'])
            to_dst = self._project.generate_cache(luid)
            self.compare_paths(from_dst, to_dst)
        elif compare_mode == "source":
            self.compare_paths(cmp_paths[I_FROM], cmp_paths[I_TO])
        else:
            raise ValueError(
                '"{}" is not a valid compare_mode'
                '(must be "source" or "destination")'
                ''.format(compare_mode)
            )

    def select_luid(self, luid):
        min_index = -1
        new_frame = None
        if luid is not None:
            min_index = self._find('luid', luid)
            if luid == self._selected_luid:
                # The row is already selected, so don't refresh.
                return
            elif min_index > -1:
                new_frame = self._items[min_index]
            else:
                raise IndexError("The new _selected_luid {} wasn't found."
                                 "".format(self._selected_luid))
        # else allow deselecting (only if luid is None)
        old_frame = None
        # old_luid = self._selected_luid
        if self._selected_luid is not None:
            old_frame_i = self._find('luid', self._selected_luid)
            if old_frame_i > -1:
                old_frame = self._items[old_frame_i]

        if new_frame is not None:
            self._selected_luid = luid
            if self.bg_color is None:
                self.bg_color = new_frame.cget("background")  # tk
                # self.bg_color = self.style.lookup("MainFrame.TFrame",
                #                                   "background")  # ttk
            new_frame.configure(background=self.selection_color)
            # self.style.configure(to_style_key(luid),
            #                      self.selection_color)  # ttk

        if old_frame is not None:
            old_frame.configure(background=self.bg_color)
            # self.style.configure(to_style_key(old_luid),
            #                      background=self.bg_color)

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
            raise ValueError(
                "on_var_changed doesn't account for the unknown key"
                " (self type is {}, luid={}, key={}, var.get()={})"
                "".format(type(self).__name__, json.dumps(luid),
                          json.dumps(key), json.dumps(var.get()))
            )
            # return False
        return self._project.save()

    def on_mc_remove(self):
        if self._selected_luid is None:
            messagebox.showerror("Error", "You must select a row first.")
            return
        self.remove_where(self._selected_luid)
        self._selected_luid = None

    def on_mc_insert(self):
        if self._selected_luid is None:
            if len(self._items) == 0:
                messagebox.showerror("Error", "First add at least one version.")
            else:
                messagebox.showerror("Error", "You must select a row first.")
            return
        self.insert_where(self._selected_luid)

    def on_mc_move_up(self):
        if self._selected_luid is None:
            messagebox.showerror("Error", "You must select a row first.")
            return
        self.move_up_where(self._selected_luid)

    def on_mc_move_down(self):
        if self._selected_luid is None:
            messagebox.showerror("Error", "You must select a row first.")
            return
        self.move_down_where(self._selected_luid)

    def on_mc_view_changes_meld(self):
        if self._selected_luid is None:
            messagebox.showerror("Error", "You must select a row first.")
            return
        click_i = self._project._find_where('luid', self._selected_luid)
        self.compare(click_i, -1, command="meld")

    def on_mc_view_changes_sunflower(self):
        if self._selected_luid is None:
            messagebox.showerror("Error", "You must select a row first.")
            return
        click_i = self._project._find_where('luid', self._selected_luid)
        self.compare(click_i, -1, command="sunflower")

    def on_mc_view_step(self):
        if self._selected_luid is None:
            messagebox.showerror("Error", "You must select a row first.")
            return
        click_i = self._project._find_where('luid', self._selected_luid)
        try:
            self.view_step(click_i, command="sunflower")
        except Exception as ex:
            messagebox.showerror("Error", str(ex))
            raise ex

    def view_step(self, click_i, command="sunflower"):
        from_i, from_range = self._project.get_affected(click_i)
        from_action = self._project._actions[from_i]
        action = self._project._actions[click_i]
        from_path = from_action['path']
        if from_i == click_i:
            to_path = from_path
            if not os.path.isdir(to_path):
                raise ValueError('"{}" does not exist.'.format(to_path))
        elif from_i > click_i:
            cmd = parse_statement(action['command'])
            to_path = os.path.join(from_path, cmd['source'])
            echo0("to_path={}".format(to_path))
            if not os.path.isdir(to_path):
                raise ValueError(
                    '"{}" does not exist.'
                    ' Change the step to use a subfolder of "{}".'
                    ''.format(to_path, from_path)
                )
        else:
            raise NotImplementedError(
                "A preview requiring post-processing is not implemented."
            )
        if command == "sunflower":
            c_args = [command, "-l", to_path, "-t"]
            # -l, --left-tab=DIRECTORY        Open new tab on the left notebook
            #   (still necessary even if loading one path)
            # -t, --no-load-tabs              Skip loading additional tabs
            #   (as long a sunflower is closed, remembered tabs won't load)
        else:
            c_args = [command, to_path]
        subprocess.Popen(c_args)

    def compare(self, start, direction, command="meld"):
        # ^ start may not be a version, so look for the related version below.
        if direction not in [-1, 1]:
            raise ValueError(
                "compare must recieve -1 or 1 for direction but got {}"
                "".format(direction)
            )

        from_i, from_range = self._project.get_affected(start)
        if from_i is None:
            messagebox.showerror("Error", "An affected version wasn't found.")
            return
        if from_range is None:
            messagebox.showerror("Error", "An affected row set wasn't found.")
            return
        to_near_i = None
        if direction == -1:
            to_near_i = from_range[0] - 1
            if to_near_i < 0:
                messagebox.showerror("Error", "There is no previous version.")
                return
        else:
            to_near_i = from_range[-1] + 1
            if to_near_i >= len(self._project._actions):
                messagebox.showerror("Error", "There is no next version.")
                return
        to_i, to_range = self._project.get_affected(to_near_i)
        from_path = self._project._actions[from_i]['path']
        to_path = self._project._actions[to_i]['path']
        echo1('compare: {} "{}" "{}"'
              ''.format(command, from_path, to_path))
        self.compare_paths(from_path, to_path, command=command)

    def compare_paths(self, from_path, to_path, command="meld"):
        if command == "sunflower":
            c_args = [command, "-l", from_path, "-r", to_path, "-t"]
            # -t, --no-load-tabs                 Skip loading additional tabs
            # (as long a sunflower is closed, remembered tabs won't load)
        else:
            c_args = [command, from_path, to_path]
        subprocess.Popen(c_args)

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
        else:
            raise ValueError(
                "The verb must be: {}"
                "".format(anewcommit.TRANSITION_VERBS
                          + anewcommit.VERSION_VERBS)
            )
        echo1("* adding row at {}".format(row))
        frame = tk.Frame(self.scrollable_frame)
        # ^ Using ttk.Frame for the row yields:
        #   'TclError: unknown option "-background"'
        #   so making a style for each luid would be necessary
        #   but it doesn't seem to work (even if select_luid is
        #   changed to affect the style):
        # style_key = to_style_key(luid)
        # self.style.configure(style_key, background='gray')
        # frame = ttk.Frame(self.scrollable_frame, style=style_key)

        frame.bind("<Button-1>", lambda e, l=luid: self.on_click_row(l))
        if self.bg_color is None:
            self.bg_color = frame.cget("background")  # tk
            # self.bg_color = self.style.lookup("MainFrame.TFrame",
            #                                   "background")  # ttk
        if luid == self._selected_luid:
            frame.configure(background=self.selection_color)  # tk
            # self.style.configure(style_key, background=self.selection_color)
            # ^ ttk
        frame.data = action
        self._frame_of_luid[luid] = frame
        self._vars_of_luid[luid] = {}

        results = dict_to_widgets(
            action,
            frame,
            template=this_template,
            warning_on_blank=get_verbosity(),
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
            if sys.version_info.major > 2:
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
                    Keyword argument defaults force early binding (they
                    come from the outer scope, not the call).

                    Sequential arguments:
                    tkVarID -- a string such as PY_VAR23
                    param -- unknown meaning, usually ''
                    event -- an event name (such as 'w' in Python2)

                    Keyword arguments:
                    luid -- Specify the luid of the version to affect.
                    k -- Specify the key of the value associated with
                        the Tk var.
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
            if sys.version_info.major >= 3:
                var.trace_add('write', on_this_var_changed)
            else:
                var.trace('wu', on_this_var_changed)
            # var.trace_add(['write', 'unset'], default_callback)
            # ^ In Python 2 it was trace('wu', ...)
        echo2("  - dict_to_widgets got {} widgets."
              "".format(len(results['widgets'])))
        for name, widget in results['widgets'].items():
            widget.bind("<Button-1>", lambda e, l=luid: self.on_click_row(l))
            widget.pack(side=tk.LEFT)
            var = results['vs'][name]
            self._vars_of_luid[luid][name] = var

        statements = action.get('statements')
        if statements is not None:
            for _st in statements:
                cmd = parse_statement(_st)
                text = statement_to_caption(cmd)
                widget = ttk.Label(frame, text=text)
                if cmd.get('command') is not None:
                    widget.bind(
                        "<Button>",
                        lambda e, l=luid, st=_st: self.on_click_sub(e, l, st),
                    )
                    # ^ also done in mark_if_has_folder
                else:
                    pass
                    # There is nothing to do. If invalid,
                    # parse_statement already raised an Exception.
                widget.pack(side=tk.LEFT)

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
            # offset = len(results['added']) - len(results['removed'])
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
        if min_index < 0:
            err = "The index {} is bad in _reload_at".format(min_index)
        else:
            old_len = len(self._items)
            # self.dump2()
            echo1("  len: {}".format(old_len))
            for index in reversed(range(min_index, old_len)):
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

    def path_of_index(self, index):
        if index < len(self._project._actions):
            path = self._project._actions[index].get('path')
        else:
            raise ValueError("Index {} is not in the project.".format(index))

    def _remove(self, index):
        '''
        Remove a row at the given index. This action is private since the item
        should also be removed from the backend list.
        '''
        self._items[index].pack_forget()
        del self._items[index]

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
            self._items[i].pack_forget()
            more_items.append(self._items[i])
        # self._items = self._items[:index]
        old_len = len(self._items)
        for i in reversed(range(index, old_len)):
            self._remove(i)
        self._append_row(action)
        # (Don't modify other entries since removed rows will be re-added
        # immediately below)
        # luid = action['luid']
        # echo1("* appended row {} luid {}".format(index, luid))
        for i in range(len(more_items)):
            item = more_items[i]
            path = item.data.get('path')
            row = len(self._items)
            item.pack(fill=tk.X)
            # echo1("* dequeued luid {}".format(more_items[i].data['luid']))
            self._items.append(item)

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
        # other_luid = self._project._actions[other_index]['luid']
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
        # other_luid = self._project._actions[other_index]['luid']
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
        '''
        Turn the commit option of the version or process off or on.
        '''
        self._project.set_commit(luid, on)

    def set_verb(self, luid, verb):
        self._project.set_verb(luid, verb)

    def append_transition(self):
        transition_action = self._project.add_transition('no_op')
        self.update_undo()
        self._append_row(transition_action)

    def append_source(self, path, do_save=True):
        try:
            raw_name = os.path.split(path)[1]
            name = raw_name
            if self._project._find_where('path', path) > -1:
                yes = messagebox.askyesno(
                    "Duplicate source",
                    ('If you add "{}" again, you will need to manually'
                     ' add a different "use" statement with no overlap.'
                     ' Do you want to continue adding the duplicate?'
                     ''.format(name))
                )
                if not yes:
                    return True
            new_number = 1
            while self._project._find_where('name', name) > -1:
                new_number += 1
                name = raw_name + " ({})".format(new_number)

            version_action = self._project.add_version(path, do_save=do_save,
                                                       name=name)
            self.update_undo()
            self._append_row(version_action)
        except (ValueError, TypeError) as ex:
            if verbosity:
                raise ex
            messagebox.showerror("Error", str(ex))
            return False
        return True

    def _init_title_row(self):
        if self._added_title_row:
            return
        self._added_title_row = True
        titleRowFrame = ttk.Frame(self.scrollable_frame)
        for caption in actions_captions:
            widget = ttk.Label(
                titleRowFrame,
                text=caption,
            )
            widget.pack(side=tk.LEFT)
        titleRowFrame.pack(fill=tk.X)

    def load_project(self, path):
        if os.path.getsize(path) == 0:
            os.remove(path)
            return False
        if os.path.isfile(path):
            self.last_path = os.path.dirname(path)
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
        '''
        Sequential arguments:
        level -- Set what level of verbosity this dump affects.
        '''
        global _GUI_DUMP
        global _BACKEND_DUMP
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
            echos[level]("  - path~={}".format(name))
            if path is not None:
                index = self._project._find_where('path', path)
                echos[level]("  - index {}".format(index))

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
            known_luid = None
            # TODO: ^ generate or deprecate known_luid
            i = self._project._find_where('path', path)
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
        if os.path.isdir(path):
            self.last_path = path
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
            result = self.append_source(subPath, do_save=False)
            if not result:
                failPaths.append(subPath)
                break
            count += 1
        self._project.save()
        echo1("Added {}".format(count))
        for failPath in failPaths:
            echo1('* failed to add {}'.format(failPath))
        self.dump1()

    def exitProgram(self):
        root.destroy()


def usage():
    echo0(__doc__)

root = None

def main():
    global root
    root = tk.Tk()
    root.geometry("800x600")
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
                set_verbosity(1)
            elif arg == "--debug":
                set_verbosity(2)
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
    global verbosity
    if is_truthy(settings.get('verbosity')):
        verbosity = 1
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
    if verbosity > 0:
        echo0("* available ttk themes: {}".format(style.theme_names()))
        echo0("* current theme: {}".format(style.theme_use()))

    app = MainFrame(root, settings=settings)
    if versions_path is not None:
        try_project = os.path.join(versions_path, "anewcommit.json")
        loaded = False
        if os.path.isfile(try_project):
            loaded = app.load_project(try_project)
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
            set_verbosity(True)
    main()


# References
# Urban, M., & Murach, J. (2016). Murach's Python Programming
#     [VitalSource Bookshelf]. Retrieved from
#     https://bookshelf.vitalsource.com/#/books/9781943872152
