#!/usr/bin/env python
"""
redact_gnu
----------
This script is part of <https://github.com/Poikilos/anewcommit>.

Redact private data using GNU tools (which are fast).

Requirements:
- file (part of GNU)
- dos2unix (command comes with package of same name)
- GNU sed (such as via `brew install gnu-sed` on macOS)


Instructions:
Run this in a directory to redact the data within (The current working
directory is used). You must provide a
list of private database connection strings in JSON format. The JSON
file goes in the parent directory of the current working directory, and
must be named the same as the directory except ending with
"-private.json".

Example:
1. If your project directory is ~/git/project1, place a file called
   "project1-private.json" in ~/git or ~.
   The JSON file must contain at least one database in the following
   format:

{
    "private": {
        "databases": [
            ["DB1", "localhost", "user", "password", "some_database"],
            ["DB2", "localhost", "other_user", "password", "other_database"]
        ],
        "comments": {
            "DB1": "The old database"
        }
    }
}
2. Make sure you have a config.php that is *not in a published folder*!
   The file should have at least the same data as above, such as:

return (object) array(
    'DB1' => (object) array(
        'dbhost'=>"localhost",
        'dbuser'=>"user",
        'dbpass'=>"password",
        'dbname'=>"some_database"
    ),
    'DB2' => (object) array(
        'dbhost'=>"localhost",
        'dbuser'=>"other_user",
        'dbpass'=>"password",
        'dbname'=>"other_database"
    )
);

3. Open a a terminal
  4. cd to git/project1.
  5. Run: python3 redact_gnu.py
6. The files should now *all* have "dbhost" replaced with
   $config->DB1->dbhost and so on within mysql and mysqli connection
   strings *only*. Quotes are removed where that is the cleanest
   solution (otherwise variable interpolation is used, such as in the
   case of PEAR connection strings).
7. Any remaining instances of private data will be shown on the screen!
8. You must manually include your config file within the correct scope
   of a php section (such as starting with "<?php") within your php file
   such as via:
   $redact = include("../redact.php");
   - If you use the auto-inserted global (occurs on <?php but not <?)
     then at the beginning of each function you must manually add:
     global $redact;
     - Or you can also use the include statement
       if it has the same number of ../ instances that were
       automatically inserted (or whatever is correct based on your
       redact.php location).
"""
import os
import sys
import subprocess
import shlex
import json
import re

def echo0(*args):
    print(*args, file=sys.stderr)



# Based on method from anewcommit/anewcommit/gui_tkinter.py
def run_or_showerror(command_parts, show_stdout=True, ignore_codes=[]):
    '''
    If we got this far (if binary/script exists) and it still
    returned an error code, the most likely issue is that
    the sunflower package isn't installed but the script is
    still in ~/.local/bin such as if Python was upgraded.

    Keyword arguments:
    show_stdout -- If True, write stdout of process to stdout.
        If False, return the stdout as lines.
    ignore_codes -- Ignore these error codes. For example, ignore 1 if
        grep, since error code 1 means no matches!
    '''
    results = None
    command = command_parts[0]
    # echo0("[sed] Running: {}".format(shlex.join(command_parts)))
    proc = subprocess.Popen(command_parts, stderr=subprocess.PIPE,
                            stdout=subprocess.PIPE)
    # echo0("done process: {}".format(proc))
    # ^ such as
    #   <Popen: returncode: None args: ['grep', '[redacted]', '-n', '-r']>
    # echo0("result: {}".format(result))
    out, err = proc.communicate()
    code = proc.returncode
    # module_not_found = False
    err_s = None
    if err is not None:
        # should always be non-None if stderr=subprocess.PIPE
        err_s = err.decode("utf-8")
        err_lines = err_s.strip().split("\n")
        if len(err_lines) > 1:
            # Reduce it down to something like:
            # "ImportError: No module named sunflower"
            err_s = err_lines[-1]
    if out is not None:
        out_s = out.decode('utf-8')
        if show_stdout:
            # echo0("\n\n{} result:".format(command))
            for line in out_s.split("\n"):
                print(line)
        else:
            if out_s.strip() == "":
                results = []
            else:
                results = out_s.strip().split("\n")
    if ((code != 0) and (code not in ignore_codes)):
        if err_s.strip() == "":
            err_s = None
        if err_s is not None:
            if (("ModuleNotFoundError" in err_s)
                    or ("ImportError" in err_s)):
                err_s = ("{} may not be installed correctly. It says:"
                          "\n\n".format(command)) + err_s
            echo0("[run_or_showerror] {} error {}:".format(command, code))
            echo0("'''")
            echo0(err_s)
            echo0("'''")
        else:
            echo0(
                "{} error {}".format(command, code),
                ("{} failed or wasn't installed correctly (no error message)."
                 "".format(command)),
            )
    return results


def grep_paths(criteria, root):
    '''
    In the specified path, run grep and return the list of paths.
    '''

    cmd_parts = ["grep", criteria, '-rl', root]
    # -l: print only the filename.
    return run_or_showerror(cmd_parts, show_stdout=False, ignore_codes=[1])


sed_once_files = {}

def sed(old, new, path, delimiter=None, once=False, only_if_new_missing=None):
    '''
    Replace old with new inside of the file designated by path.

    Keyword arguments:
    delimiter -- The sed command delimeter. This must be a character
        that is neither in old nor new.
    once -- Only change the first instance of old.
    only_if_new_missing -- Only do anything if new is *not in the file*.
        If None, reverts to the value of the "once" argument.
    '''
    if only_if_new_missing is None:
        only_if_new_missing = once
    if only_if_new_missing:
        parent = os.path.dirname(path)
        new_in_files = grep_paths(re.escape(new), parent)
        if path in new_in_files:
            # It already contains the new string.
            return
        '''
        else:
            echo0('[sed only_if_new_missing={}]'
                  ' path "{}" is not in detected matches: {}'
                  ''.format(only_if_new_missing, path, new_in_files))
        '''
    if once:
        pairs = sed_once_files.get(path)
        if pairs is not None:
            for pair in pairs:
                if pair[0] == old:
                    echo0('[sed once={}] skipped "{}" since the same criteria'
                          ' was replaced in a previous call that also used'
                          ' the "once" option.'
                          ''.format(once, path))
                    return
            sed_once_files[path].append((old, new))
        else:
            sed_once_files[path] = [(old, new)]

    sed_chars = "$.*[^"  # no '\' assumes it was included intentionally!
    if path is None:
        raise ValueError("Path is None.")
    if path.strip() == "":
        raise ValueError("Path is blank.")
    if os.path.isdir(path):
        raise ValueError('Path "{}" is a folder (should be a file).'
                         ''.format(path))
    if not os.path.isfile(path):
        raise ValueError('Path "{}" is not a file.'
                         ''.format(path))
    if os.path.basename(path).startswith(".gitignore"):
        raise ValueError("Operating on .gitignore is not expected."
                         " Please filter it out.")
    parent = os.path.dirname(path)
    parent_name = os.path.basename(parent)
    if os.path.basename(path) == ".git":
        raise ValueError("Operating on .git is not expected."
                         " Please filter it out.")
    try_chars = ["/", "|", "#", "~", "="]
    if delimiter is None:
        for try_char in try_chars:
            if (try_char not in old) and (try_char not in new):
                delimiter = try_char
                break
        if delimiter is None:
            raise ValueError(
                "There are no characters from default delimiter set {}"
                " not in old string \"{}\"."
                " Try specifying a delimiter that is not in the string."
                "".format(try_chars, old)
            )
    else:
        if delimiter in old:
            raise ValueError(
                "The specified delimiter '{}' is in old string \"{}\""
                "".format(delimiter, old)
            )
        elif delimiter in new:
            raise ValueError(
                "The specified delimiter '{}' is in new string \"{}\""
                "".format(delimiter, old)
            )
    for sed_char in sed_chars: # + [delimiter]: # delimiter fixed above
        old = old.replace(sed_char, "\\" + sed_char)
        new = new.replace(sed_char, "\\" + sed_char)
    if len(delimiter) != 1:
        raise ValueError(
            'The delimiter must be exactly 1 character but is "{}"'
            ''.format(delimiter)
        )
    num = 1
    dst = path + ".tmp"
    while os.path.isfile(dst):
        num += 1
        dst = path + ".tmp{}".format(num)
    # print("[sed] {}".format(path))
    sed_command = "s{d}{old}{d}{new}{d}".format(old=old, new=new, d=delimiter)
    if once:
        for bad_char in ["{", "}"]:
            if bad_char in sed_command:
                raise ValueError(
                    "'{}' cannot be in {} when using the once option."
                    "".format(bad_char, sed_command)
                )
        sub_command = "s{d}{d}{new}{d}".format(new=new, d=delimiter)
        # ^ same as sed_command except without redundant criteria.
        #   - 2 delimiters means use previous criteria (prepended below)
        sep = delimiter
        sed_command = "0,/" + old + "/{" + sub_command + "}"
        # ^ '/' since there *cannot* be a custom separator using this
        #   notation!  It is fine to have a custom delimiter after 's'
        #   in sub_command even though / is used in this part.
        echo0("Running: sed -i -e '{}' '{}'".format(sed_command, path))
        '''
        ^ such as `sed '0,/Apple/{s/Apple/Banana/}' input_filename`
          or `sed '0,/Apple/{s//Banana/}' input_filename`
          or `sed '0,/Apple/s//Banana/' input_filename`
          (works only with GNU sed)
          "start at line 0, continue until you match 'Apple', execute
          the substitution in curly brackets"
          as per <https://stackoverflow.com/a/9453461>.
        '''
    # with open(dst, 'w') as outs:
    cmd_parts = ["sed", "-i", "-e", sed_command, path]
    # echo0("Running: {}".format(shlex.join(cmd_parts)))  # WARNING: private
    subprocess.call(cmd_parts)
    # -e: Add the script to the commands to be executed
    # sed_command: usually this is in single quotes.
    # -i: edit in place. Make backup if suffix: -i[SUFFIX], --in-place[=SUFFIX]
    # stdout=outs
    # or if shell=True:
    # subprocess.call(["sed -i -e 's/hello/helloworld/g' www.txt"], shell=True)
    # (See <https://askubuntu.com/a/747452>)


def splitall(path):
    '''
    Split every part of the path. See
    <https://www.oreilly.com/library/view/python-cookbook/0596001673/ch04s16.html>.
    '''
    allparts = []
    while True:
        parts = os.path.split(path)
        if parts[0] == path:  # sentinel for absolute paths
            allparts.insert(0, parts[0])
            break
        elif parts[1] == path: # sentinel for relative paths
            allparts.insert(0, parts[1])
            break
        else:
            path = parts[0]
            allparts.insert(0, parts[1])
    return allparts


ARG_NAMES = ['config_section', 'dbhost', 'dbuser', 'dbpass', 'dbname']
# ^ Should always match redact_mysql_statements, private_example, and
#   module's docstring.


def redact_mysql_statements(config_section, dbhost, dbuser, dbpass, dbname,
                            root=os.getcwd(), config_var="redact"):
    '''
    Replace private substrigs in mysqli, EyeMySQLAdap, and SQLC (Pear)
    lines.

    NOTICE: The spacing may matter here, so check the final result for
    additional instances of private strings!

    Keyword arguments:
    root -- (default: current working directory) The directory to
        redact.
    config_var -- The variable name to use as the config, such as
        "redact" (default) if you are adding
        `$redact = include("../redact.php");`
        to your PHP file. See redact documentation for more info.
        Using the variable "config" is *not* recommended since that is
        used by other web applications and frameworks.
    '''
    sec = config_section
    conf = config_var
    replacements = []
    # if None not in [dbhost, dbuser, dbpass]:
    if dbhost is not None:
        replacements += [
            ['mysqli_connect("{}", "{}", "{}")'.format(dbhost, dbuser, dbpass),
             ('mysqli_connect(${conf}->{sec}->dbhost, ${conf}->{sec}->dbuser, ${conf}->{sec}->dbpass)'
              ''.format(conf=config_var, sec=config_section)), False],
            ['mysql_connect("{}", "{}", "{}")'.format(dbhost, dbuser, dbpass),
             ('mysql_connect(${conf}->{sec}->dbhost, ${conf}->{sec}->dbuser, ${conf}->{sec}->dbpass)'
              ''.format(conf=config_var, sec=config_section)), False],
            ['mysqli_select_db($conn,"{}")'.format(dbname),
             'mysqli_select_db($conn,${}->{}->dbname)'.format(config_var, config_section), True],
            ['mysqli_select_db($conn, "{}")'.format(dbname),
             'mysqli_select_db($conn, ${}->{}->dbname)'.format(config_var, config_section), True],
            ['mysql_select_db("{}")'.format(dbname),
             'mysql_select_db(${}->{}->dbname)'.format(config_var, config_section), True],
            ['mysql_select_db("{}", $conn)'.format(dbname),
             'mysql_select_db(${}->{}->dbname, $conn)'.format(config_var, config_section), True],
            ['mysql_select_db("{}",$conn)'.format(dbname),
             'mysql_select_db(${}->{}->dbname,$conn)'.format(config_var, config_section), True],
            [("EyeMySQLAdap('{}', '{}', '{}', '{}')"
              "".format(dbhost, dbuser, dbpass, dbname)),
             ("EyeMySQLAdap(${conf}->{sec}->dbname, ${conf}->{sec}->dbuser, ${conf}->{sec}->dbpass, ${conf}->{sec}->dbname)"
              "".format(conf=config_var, sec=config_section)), False],
            [("define('SQLC', \"mysql://{}:{}@{}/{}\")"
              "".format(dbhost, dbuser, dbpass, dbname)),
             ("define('SQLC', \"mysql://{$"+conf+"->"+sec+"->dbuser}:{$"
              +conf+"->"+sec+"->dbpass}@{$"+conf+"->"+sec+"->dbhost}/{$"
              +conf+"->"+sec+"->dbname}\")"), False],
              # ^ such as in Resources/xajaxGrid/person.inc.php
              # ^ curly braces allow expressions (otherwise only 1-deep
              #   variable interpolation occurs in PHP!)
        ]
    else:
        replacements += [
            ["'{}' => '{}',".format(dbuser, dbpass),
             ("${conf}->{sec}->dbuser => ${conf}->{sec}->dbpass,"
              "".format(conf=config_var, sec=config_section)), False],
        ]

    # only_if_criteria = replacements[0][0]
    only_if_criteria = "mysql.*connect.*"+dbuser+".*"+dbpass
    real_root = os.path.realpath(root)
    del root
    paths = grep_paths(only_if_criteria, real_root)
    # print("Paths matching {} in {}:".format(only_if_criteria, root))
    ignore_names = ['.git', '.gitignore']

    for path in paths:
        for replacement in replacements:
            ignore = False
            for part in splitall(path):
                if part in ignore_names:
                    echo0('[redact_mysql_statements] ignoring "{}"'
                          ''.format(path))
                    ignore = True
                    continue
            if ignore:
                continue
            old, new, replace_if_old = replacement
            if replace_if_old:
                # Any path in "paths" is already known to contain old
                #   password, so replace old select_db command.
                sed(old, new, path)

    # FIXME: debug only:
    if config_section == "old":
        echo0("config_section: {}".format(config_section))
        problems = run_or_showerror(
            ['grep', 'mysql.*_select_db("{}");'.format(dbname), "-n", "-r",
             real_root],
            show_stdout=False,
            ignore_codes=[1],
        )
        if len(problems) > 0:
            for problem in problems:
                if "error_log:" not in problem:
                    raise RuntimeError(problem)

    for root, dirs, files in os.walk(real_root):
        for sub in files:
            path = os.path.join(root, sub)
            ignore = False
            for part in splitall(path):
                if part in ignore_names:
                    echo0('[redact_mysql_statements] ignoring "{}"'
                          ''.format(path))
                    ignore = True
                    continue
            if ignore:
                continue
            for replacement in replacements:
                old, new, replace_if_old = replacement
                if not replace_if_old:
                    sed(old, new, path)
                # else was already done if old was found
    old = '<?php';
    new = ('<?php\\n${conf} = include("../{conf}.php");\\n'
           ''.format(conf=config_var));
    # ^ The extra newlines are there because in some cases there is no
    #   newline after "<?php" and the whole thing could be one line.
    changed_paths = grep_paths('${}->'.format(config_var),real_root)
    for changed_path in changed_paths:
        if not changed_path.startswith(real_root):
            # This will never happen if logic in code is correct:
            raise RuntimeError("Can't revise path outside of root: {}"
                               "".format(real_root))
        offset = 1
        if real_root.endswith(os.path.sep):
            # A trailing slash is required if using a drive letter on
            #   Windows :(, and regardless, the caller may have provided
            #   a trailing slash.
            offset = 0
        sub = changed_path[len(real_root)+offset:]  # +offset to skip '/'
        sub_parts = splitall(sub)
        this_new = new
        if len(sub_parts) > 1:
            this_new = new.replace("../", "../"*len(sub_parts))
        sed(old, this_new, changed_path, once=True)
    return 0

private_example = '''
{
    "private": {
        "databases": [
            ["DB1", "dbhost", "dbuser", "dbpass", "dbname"],
            ["DB2", "dbhost", "dbuser", "dbpass", "dbname"]
        ],
        "comments": {
            "DB1": "The old database"
        }
    }
}
'''

def usage():
    echo0(__doc__)


def private_usage(meta_path):
    usage()
    echo0('The file "{}" should be JSON structured like the example above.'
          ''.format(meta_path))
    # echo0(private_example)


def main():
    PASSWORD_COL = ARG_NAMES.index('dbpass')
    real_root = os.path.realpath(os.getcwd())
    this_dir_name = os.path.basename(os.getcwd())
    meta_name = "{}-private.json".format(this_dir_name)
    meta_path = os.path.join(os.path.dirname(os.getcwd()), meta_name)
    parent_dir = os.path.dirname(os.getcwd())
    try_path = os.path.join(os.path.dirname(parent_dir), meta_name)
    tried_path = meta_path
    if os.path.isfile(try_path):
        meta_path = try_path
    if not os.path.isfile(meta_path):
        private_usage(meta_path)
        echo0("The file does not exist.")
        if tried_path != meta_path:
            echo0('- also tried "{}"'.format(tried_path))
        elif try_path != meta_path:
            echo0('- also tried "{}"'.format(try_path))
        return 1
    try:
        with open(meta_path, 'r') as ins:
            meta = json.load(ins)
    except json.decoder.JSONDecodeError as ex:
        private_usage(meta_path)
        opener = "Expecting property name enclosed in double quotes:"
        opener_i = str(ex).find(opener)
        if opener_i > -1:
            location = str(ex)[opener_i+len(opener):]
            echo0("Maybe you left a dangling comma"
                  " (allowed in Python, not JSON) near {}"
                  "".format(location.strip()))
        raise
    private = meta.get('private')
    if private is None:
        private_usage(meta_path)
        return 1
    replacements = private.get('databases')
    if replacements is None:
        private_usage(meta_path)
        return 1
    site_n = 0
    for site in replacements:
        site_n += 1  # Start at 1.
        if not isinstance(site, list):
            private_usage()
            echo0("Error: There must be a 5-argument list"
                  " but site {} was a {}."
                  "".format(site_n, type(site).__name__))
            return 1
        if len(site) != 5:
            private_usage()
            echo0("Error: There must be 5 arguments"
                  " but there were {} for site {}."
                  "".format(len(site), site_n))
            return 1
    del site_n

    for site in replacements:
        redact_mysql_statements(*site, root=real_root)

    # return 0
    print("Any remaining instances will appear below.")

    done_values = []
    for site in replacements:
        results = []
        is_db = site[1] is not None
        for argi in range(1, len(ARG_NAMES)):
            if site[argi] is None:
                # Such as user-pass combo with no database such as custom php
                continue
            if (not is_db) and (argi != PASSWORD_COL):
                # Only the password matters in this case,
                #   such as user-pass combo with no database such as custom php.
                continue
            if site[argi] in done_values:
                # Only show instances once.
                continue
            else:
                done_values.append(site[argi])
            lines = run_or_showerror(['grep', site[argi], "-n", "-r", real_root], show_stdout=False, ignore_codes=[1])
            good_line_count = 0
            good_lines = []
            for line in lines:
                if "error_log:" not in line:
                    good_lines.append(line)
            if len(good_lines) > 0:
                results.append("[redact_gnu main]  {}={}:"
                               "".format(ARG_NAMES[argi], site[argi]))
                results += good_lines
            # ^ ignore 1 (means not found)
        if len(results) > 0:
            echo0("[redact_gnu main] {} database:".format(site[0]))
            for result in results:
                echo0(result)


if __name__ == "__main__":
    sys.exit(main())
