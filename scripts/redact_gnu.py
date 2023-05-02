#!/usr/bin/env python
"""
redact_gnu
----------
This script is part of <https://github.com/Poikilos/anewcommit>.

Redact private data using GNU tools (which are fast).

Run this in a directory to redact the data within (The current working
directory is used). You must provide a
list of private database connection strings in JSON format. The JSON
file goes in the parent directory of the current working directory, and
must be named the same as the directory except ending with
"-private.json".

Example:
1. If your project directory is git/project1, place a file called
   "project1-private.json" in git.
   The JSON file must contain at least one database in the following
   format:

{
    "private": {
        "databases": [
            ["DB1", "dbhost", "dbuser", "dbpass", "dbname"],
            ["DB2", "db2host", "db2user", "db2pass", "db2name"]
        ],
        "comments": {
            "DB1": "The old database"
        }
    }
}

2. Open a a terminal
  3. cd to git/project1.
  4. Run: python3 redact_gnu.py
5. The files should now *all* have "dbhost" replaced with
   $config->DB1->dbhost and so on within mysql and mysqli connection
   strings *only*. Quotes are removed where that is the cleanest
   solution (otherwise variable interpolation is used, such as in the
   case of PEAR connection strings).
6. Any remaining instances of private data will be shown on the screen!
"""
import os
import sys
import subprocess
import shlex
import json


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


def sed(old, new, path, delimiter=None):
    '''
    Replace old with new inside of the file designated by path.

    Keyword arguments:
    delimiter -- The sed command delimeter. This must be a character
        that is neither in old nor new.
    '''
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
    print("[sed] {}".format(path))
    sed_command = "s{d}{old}{d}{new}{d}".format(old=old, new=new, d=delimiter)
    # with open(dst, 'w') as outs:
    cmd_parts = ["sed", "-i", "-e", sed_command, path]
    echo0("Running: {}".format(shlex.join(cmd_parts)))  # WARNING: private maybe
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
                            root=os.getcwd()):
    '''
    Replace private substrigs in mysqli, EyeMySQLAdap, and SQLC (Pear)
    lines.

    NOTICE: The spacing may matter here, so check the final result for
    additional instances of private strings!
    '''
    replacements = [
        ['mysqli_connect("{}", "{}", "{}");'.format(dbhost, dbuser, dbpass),
         ('mysqli_connect($config->{sec}->dbhost, $config->{sec}->dbuser, $config->{sec}->dbpass);'
          ''.format(sec=config_section)), False],
        ['mysql_connect("{}", "{}", "{}");'.format(dbhost, dbuser, dbpass),
         ('mysql_connect($config->{sec}->dbhost, $config->{sec}->dbuser, $config->{sec}->dbpass);'
          ''.format(sec=config_section)), False],
        ['mysqli_select_db($conn,"{}");'.format(dbname),
         'mysqli_select_db($conn,$config->{}->dbname);'.format(config_section), True],
        ['mysqli_select_db($conn, "{}");'.format(dbname),
         'mysqli_select_db($conn, $config->{}->dbname);'.format(config_section), True],
        ['mysql_select_db("{}");'.format(dbname),
         'mysql_select_db($config->{}->dbname);'.format(config_section), True],
        ['mysql_select_db("{}", $conn);'.format(dbname),
         'mysql_select_db($config->{}->dbname, $conn);'.format(config_section), True],
        ['mysql_select_db("{}",$conn);'.format(dbname),
         'mysql_select_db($config->{}->dbname,$conn);'.format(config_section), True],
        [("EyeMySQLAdap('{}', '{}', '{}', '{}');"
          "".format(dbhost, dbuser, dbpass, dbname)),
         ("EyeMySQLAdap($config->{sec}->dbname, $config->{sec}->dbuser, $config->{sec}->dbpass, $config->{sec}->dbname);"
          "".format(sec=config_section)), False],
        [("define('SQLC', \"mysql://{}:{}@{}/{}\");"
          "".format(dbhost, dbuser, dbpass, dbname)),
         ("define('SQLC', \"mysql://$config->{sec}->dbuser:$config->{sec}->dbpass@$config->{sec}->dbhost/$config->{sec}->dbname\");"
          "".format(sec=config_section)), False],
          # ^ such as in Resources/xajaxGrid/person.inc.php
    ]

    # only_if_criteria = replacements[0][0]
    only_if_criteria = "mysql.*connect.*"+dbuser+".*"+dbpass
    real_root = os.path.realpath(root)
    paths = grep_paths(only_if_criteria, real_root)
    # print("Paths matching {} in {}:".format(only_if_criteria, root))
    ignore_names = ['.git', '.gitignore']

    # FIXME: debug only:
    '''
    if config_section == "old":
        flag_path = "/home/owner/git/tcstc/public/TimeClockServer.php"
        if flag_path not in paths:
            raise RuntimeError(
                '`{}` did not produce "{}", only {}'
                ''.format(only_if_criteria, flag_path, paths)
            )
    '''
    # FIXME: ^ doesn't raise exception, but mysql_select_db not replaced
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
        problems = run_or_showerror(['grep', 'mysql.*_select_db("{}");'.format(dbname), "-n", "-r"], show_stdout=False, ignore_codes=[1])
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
    echo0('The file "{}" should be JSON structured like the example above.')
    # echo0(private_example)


def main():
    this_dir_name = os.path.basename(os.getcwd())
    meta_name = "{}-private.json".format(this_dir_name)
    meta_path = os.path.join(os.path.dirname(os.getcwd()), meta_name)
    if not os.path.isfile(meta_path):
        private_usage(meta_path)
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
        redact_mysql_statements(*site)

    # return 0
    print("Any remaining instances will appear below.")
    for site in replacements:
        results = []
        for argi in range(1, len(ARG_NAMES)):
            lines = run_or_showerror(['grep', site[argi], "-n", "-r"], show_stdout=False, ignore_codes=[1])
            good_line_count = 0
            good_lines = []
            for line in lines:
                if "error_log:" not in line:
                    good_lines.append(line)
            if len(good_lines) > 0:
                results.append("[redact_gnu main]  {}:".format(ARG_NAMES[argi]))
                results += good_lines
            # ^ ignore 1 (means not found)
        if len(results) > 0:
            echo0("[redact_gnu main] {} database:".format(site[0]))
            for result in results:
                echo0(result)


if __name__ == "__main__":
    sys.exit(main())
