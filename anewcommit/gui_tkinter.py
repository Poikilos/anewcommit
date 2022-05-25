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
    set_verbose,
    profile,
)
from anewcommit.scrollableframe import ScrollableFrame

verbose = get_verbose()
session = None
playerIndex = 0

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
transition_field_order = ['commit', 'verb', 'name']
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


def default_callback(*args, **kwargs):
    # sv.trace_add callback sends 3 sequential arguments:
    # - str such as "PY_VAR0" (var._name)
    # - str (blank for unknown reason)
    # - str such as "write" (or at end of program, "unset")
    error("NotYetImplemented: default_callback")

    for arg in args:
        error('- {} "{}"'.format(type(arg).__name__, arg))
    for pair in kwargs.items():
        # k, v = pair
        # error("  {}: {}".format(k, v))
        error("  {}".format(pair))


def dict_to_widgets(d, parent, template=None, no_warning_on_blank=False):
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
    no_warning_on_blank -- If a field in field_order isn't a key in d, add a
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
            if not no_warning_on_blank:
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
        if 'values' in spec:
            expected_v = spec['values']
            # ^ It must be a list (See OptionMenu case below).
            if widget_type is None:
                widget_type = 'OptionMenu'

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
        elif isinstance(width_v, str):
            pass
        else:
            error("Warning: While determining width,"
                  " the text for '{}' is an unknown type: "
                  " \"{}\" is a {}."
                  "".format(k, width_v, type(width_v).__name__))

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
            if (v is False) or (v == 0):
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


class MainFrame(ScrollableFrame):
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
        ScrollableFrame.__init__(self, parent, style='MainFrame.TFrame')
        # ttk.Frame.__init__(self, parent, style='MainFrame.TFrame')
        # ^ There seems to be no way to make it scrollable.
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
        self._key_of_name = {}
        self._luid_of_name = {}
        self._var_of_name = {}
        menu = tk.Menu(self.parent)
        self.menu = menu
        self.parent.config(menu=menu)
        self.next_id = 0
        self._items = []

        fileMenu = tk.Menu(menu, tearoff=0)
        fileMenu.add_command(label="Open", command=self.ask_open)
        fileMenu.add_command(label="Exit", command=self.exitProgram)
        menu.add_cascade(label="File", menu=fileMenu)

        self.pack(fill=tk.BOTH, expand=True)
        # Doesn't work: padx=(10, 10), pady=(10, 10),
        # self.row_count = 0

        self.wide_width = 30

    def ask_open(self):
        directory = filedialog.askdirectory()
        if directory is not None:
            self.add_versions_in(directory)

    def on_var_changed(self, luid, key, var):
        error("Warning: A callback wasn't specified to dict_to_widgets"
              " (self type is {}, luid=\"{}\", key='{}', var.get()={})"
              "".format(type(self).__name__, luid, key, var.get()))

    def _append_row(self, action):
        '''
        Add an action to the end of the list view. The reason
        this method is private is that the action must also
        exist in self._project.actions at the same index so
        that the GUI and backend data match.
        
        The custom ".data" attribute of the row widget is set to "action".
        
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
        if action.get('verb') is None:
            raise ValueError("The verb is None")
        elif action.get('verb') in anewcommit.TRANSITION_VERBS:
            this_template = transition_template
            options['verb'] = anewcommit.TRANSITION_VERBS
            debug("- transition: {}".format(action))
        elif action.get('verb') in anewcommit.VERSION_VERBS:
            this_template = version_template
            options['mode'] = anewcommit.MODES
            debug("- version: {}".format(action))
            path = action.get('path')
            # name = None
            # if path is not None:
            name = os.path.split(path)[1]
            if path in self._id_of_path:
                raise ValueError("The path already exists: {}"
                                 "".format(path))
            self._id_of_path[path] = luid
        else:
            raise ValueError(
                "The verb must be: {}"
                "".format(anewcommit.TRANSITION_VERBS
                          + anewcommit.VERSION_VERBS)
            )
        row = len(self._items)
        debug("* adding row at {}".format(row))
        frame = tk.Frame(self.scrollable_frame)
        frame.data = action
        self._frame_of_luid[luid] = frame
        self._vars_of_luid[luid] = {}
        button = ttk.Button(
            frame,
            text="+",
            width=2,
            command=lambda: self.insert_where(luid),
        )
        # button.grid(column=1, row=row, sticky=tk.W)
        button.pack(side=tk.LEFT, padx=(10, 0))

        results = dict_to_widgets(
            action,
            frame,
            template=this_template,
            no_warning_on_blank=True,
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
            def on_this_var_changed(*args, luid=luid, k=k):
                # ^ params force early binding
                debug("on_this_var_changed({},...)".format(args))
                self.on_var_changed(luid, k, results['vs'][k])
            var.trace_add('write', on_this_var_changed)
            # var.trace_add(['write', 'unset'], default_callback)
            # ^ In Python 2 it was trace('wu', ...)
        debug("  - dict_to_widgets got {} widgets."
              "".format(len(results['widgets'])))
        for name, widget in results['widgets'].items():
            widget.pack(side=tk.LEFT)
            var = results['vs'][name]
            self._vars_of_luid[luid][name] = var
        frame.pack(fill=tk.X)
        # ^ must match the pack call in insert so layout is consistent
        # ^ expand=True: makes the row taller so rows fill the window
        self._items.append(frame)  # self.row_count += 1
    
    def _remove(self, index):
        '''
        Remove a panel at the given index. This action is private since the
        item should also be removed from the backend list.
        '''
        self._items[index].pack_forget()
        del self._items[index]

    def remove_where(self, luid):
        action = None
        index = self._project._find_where('luid', luid)
        i = self._find('luid', luid)
        if i != index:
            raise RuntimeError(
                "The data and project are out of sync:"
                " (actions[{}]['luid']={}, _items[{}].data['luid']={})"
                "".format(index, luid, i, luid)
            )
        del self._projects.actions[index]
        self._items[i].pack_forget()
        del self._items[i]

    def _insert(self, index, action):
        '''
        Generate a new panel and insert it at the given index. This method
        is private since the action must already exist at the same index in
        the self._project.actions list so that both lists match.
        
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
        self._items = self._items[:index]
        self._append_row(action)
        # luid = action['luid']
        # debug("* appended row {} luid {}".format(index, luid))
        for i in range(len(more_items)):
            item = more_items[i]
            item.pack(fill=tk.X)
            # debug("* dequeued luid {}".format(more_items[i].data['luid']))
            self._items.append(item)
            
    
    def _find(self, name, value):
        for i in range(len(self._items)):
            item = self._items[i]
            # if item.data.get(name) == value:
            if item.data[name] == value:
                return i
        return -1

    def insert_where(self, luid):
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
        next_action = self._project.actions[index]
        next_is_ver = next_action['verb'] in anewcommit.VERSION_VERBS
        '''
        prev_is_ver = False
        if index > 0:
            prev_action = self._projects.actions[index-1]
            prev_is_ver = prev_action['verb'] in anewcommit.VERSION_VERBS
        '''
        if next_is_ver or (item_i == 0):
            action = anewcommit.new_pre_process()
        else:
            action = anewcommit.new_post_process()
        try:
            luid = self._project.insert(index, action)
            self._insert(item_i, action)
        except ValueError as ex:
            messagebox.showerror("Error", str(ex))

    def set_commit(self, luid, on):
        self._project.set_commit(luid, on)

    def set_verb(self, luid, verb):
        self._project.set_verb(luid, verb)

    def add_transition_and_source(self, path):
        try:
            version_action = self._project.add_version(path)
            try:
                self._append_row(version_action)
            except (ValueError, TypeError) as ex2:
                if verbose:
                    raise ex2
                messagebox.showerror("Error", str(ex2))
                return False
            transition_action = self._project.add_transition('no_op')
            self._append_row(transition_action)
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

        frame = tk.Frame(self.scrollable_frame)
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
        debug("Added {}".format(count))

    def exitProgram(self):
        root.destroy()


def usage():
    error(__doc__)


def main():
    # global session
    # session = Session()

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
