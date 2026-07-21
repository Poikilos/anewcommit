#!/usr/bin/env python
from __future__ import print_function

from collections import OrderedDict
import copy
import csv
import json
import shlex
import shutil
import sys
import os
import platform
import subprocess
import pathlib
import urllib
import warnings

from datetime import datetime, timezone
from io import StringIO
# from .find_pycodetool import pycodetool

from pycodetool.parsing import (
    find_unquoted_not_commented,
    explode_unquoted,
)

# from .find_hierosoft import hierosoft

from hierosoft.ggrep import (
    gitignore_to_rsync_pair,
)

from hierosoft.morelogging import (
    echo0,
    echo1,
    echo2,
    set_verbosity,
    get_verbosity,
)

from hierosoft import (
    s2or3,
    is_truthy,
)

from hierosoft.logging2 import getLogger

logger = getLogger(__name__)


profile = os.environ.get('HOME')
if platform.system() == "Windows":
    profile = os.environ.get('USERPROFILE')

DB_LINE_FORMATS = [
    {
        'starter': 'EyeMySQLAdap(',
        'ender': ')',
        # 'args': ["dbhost", "dbuser", "dbpass", "dbname"]
        'args': ["host", "user", "password", "db"]
    },
    {
        'starter': "define(",
        'ender': ")",
        'args': ["'SQLC'", "formatted_string"],
        # ^ Only process define if using this literal (first arg)
        'string_format': "mysql://{user}:{password}@{host}/{db}",
        # NOTE: ^ the arg is quoted!
    },
    {
        'starter': "define(",
        'ender': ")",
        'args': ['"SQLC"', "formatted_string"],
        # ^ Only process define if using this literal (first arg)
        'string_format': "mysql://{user}:{password}@{host}/{db}",
        # NOTE: ^ the arg is quoted!
    },
    {
        'starter': "mysql_select_db(",
        'ender': ")",
        'args': ['db'],
    },
    {
        'starter': "mysql_select_db(",
        'ender': ")",
        'args': ["db", "$conn"],
        # $conn is the variable holding the return of
        # mysql_connect
        # - "If the link identifier is not specified, the last
        #   link opened by mysql_connect() is assumed" (See
        #   single-arg pattern above)
        #
    },
    {
        'starter': "mysqli_select_db(",
        'ender': ")",
        'args': ["$conn", "db"],
        # conn is required in the case of mysqli
        # $conn is the variable holding the return of mysql_connect
        # NOTE: mysql_connect also has optional 4th arg for
        #   default db, so mysqli_select_db may not be
        #   present.
    },
    {
        'starter': "mysqli_connect(",
        'ender': ")",
        'args': ["host", "user", "password"],
    },
    {
        'starter': "mysqli_connect(",
        'ender': ")",
        'args': ["host", "user", "password", "db"],
    },
    {
        'starter': "mysqli_connect(",
        'ender': ")",
        'args': ["host", "user", "password", "db", "port"],
    },
    {
        'starter': "mysqli_connect(",
        'ender': ")",
        'args': ["host", "user", "password", "db", "port", "socket"],
    },
    {
        'starter': "mysql_connect(",
        'ender': ")",
        'args': ["host", "user", "password"],
    },
    {
        'starter': "mysql_connect(",
        'ender': ")",
        'args': ["host", "user", "password", "new_link"],
        # ^ new_link is bool
    },
    {
        'starter': "mysql_connect(",
        'ender': ")",
        'args': ["host", "user", "password", "new_link", "client_flags"],
        # ^ client_flags is int
    },
]

REDACTION_REQUIRES = b"""
if (file_exists("../redact.php")) {
    $redact = include("../redact.php");
} elseif (file_exists("../../redact.php")) {
    $redact = include("../../redact.php");
} elseif (file_exists("../../redact.php")) {
    $redact = include("../../../redact.php");
} else {
    $redact = include("../../../../redact.php");
}
"""


def emit_cast(value):
    if value is None:
        return "None"
    elif value is False:
        return "False"
    elif value is True:
        return "True"
    return "{}({})".format(type(value).__name__, repr(value))


def formatted_ex(ex):
    if str(ex):
        return "{}: {}".format(type(ex).__name__, ex)
    return "{}".format(type(ex).__name__)


def safe_encode(bs):
    s = bs
    try:
        s = bs.decode()
    except UnicodeDecodeError:
        pass
    if isinstance(bs, bytearray):
        # remove `bytearray(b'` and `')`
        return str(bs)[12:-2]
    return str(bs)[2:-1]


def partial_format(fmt, d):
    """Fully or partially format the Python format string fmt
    (str, bytes, or bytearray) by collecting keys from dict d
    that are present in the string in curly braces.
    """
    if not isinstance(fmt, str):
        assert isinstance(fmt, (bytes, bytearray))
    assert isinstance(d, (dict, OrderedDict))
    partialD = {}
    for key, value in d.items():
        assert isinstance(key, str), \
            ("Key should be str regardless of value type, but got {}"
             .format(repr(key)))
        if isinstance(fmt, str):
            if ("{%s}" % key) in fmt:
                partialD[key] = value
        else:
            needle = b"{" + key.encode() + b"}"
            if needle in fmt:
                # partialD[key] = value
                fmt = fmt.replace(needle, value)
    if isinstance(fmt, str):
        return fmt.format(**partialD)
    return fmt

def split_format_chunks(fmt, enclosure=["{", "}"]):
    """Get fmt as list of strings, still enclosed if were enclosed.
    Args:
        fmt (str): A Python string format, or other
            format if enclosure is set.
        enclosure (str): enclosures for variable names
            (or lack thereof such as "{}" allowed in fmt).
            - auto-converted to bytearray if fmt is bytes or bytearray.
    """
    if isinstance(fmt, str):
        for part in enclosure:
            assert isinstance(part, str)
    else:
        assert isinstance(fmt, (bytes, bytearray))
        enclosureB = bytearray()
        # # ^ Change to bytearray so int compare works below!
        for s in enclosure:
            enclosureB += s.encode()
        enclosure = enclosureB
        assert isinstance(enclosure, bytearray)
        assert isinstance(enclosure[0], int)

    i = -1
    chunks = []
    literalI = 0
    while i + 1 < len(fmt):
        i += 1
        if fmt[i] == enclosure[0]:
            if literalI != i:
                chunks.append(fmt[literalI:i])
            end = fmt.find(enclosure[1], i)
            literalI = end + 1
            if end < 0:
                raise ValueError("Start %s without %s in %s"
                                 % (repr(enclosure[0]), repr(enclosure[1]),
                                    repr(fmt)))
            # key = fmt[i+1:end]
            interpolator = fmt[i:end+1]
            chunks.append(interpolator)
            i = end
    if literalI < len(fmt):
        chunks.append(fmt[literalI:])
    return chunks


def unformat(formatted, fmt, enclosure=["{", "}"]):
    # type: (str, str, list[str]) -> OrderedDict
    """Disassemble a string into a dict using a Python format string"""
    separators = ""
    if isinstance(formatted, str):
        assert isinstance(fmt, str)
    else:
        assert isinstance(formatted, (bytes, bytearray))
        assert isinstance(fmt, (bytes, bytearray))
        separators = bytearray()
        enclosureB = []
        # # ^ Change to bytearray so int compare works below!
        for s in enclosure:
            enclosureB.append(s.encode())
        enclosure = enclosureB
        assert isinstance(enclosure, list)
        assert isinstance(enclosure[0], (bytes, bytearray))
        assert isinstance(enclosure[0][0], int)

    d = OrderedDict()
    # keys = get_format_keys(fmt)
    chunks = split_format_chunks(fmt)
    start = 0
    end = 0
    for chunkI, chunk in enumerate(chunks):
        if isinstance(formatted, str):
            assert isinstance(chunk, str)
        else:
            assert isinstance(chunk, (bytes, bytearray))
        if chunk.startswith(enclosure[0]):
            key = chunk[1:-1]
            if chunkI + 1 < len(chunks):
                if not chunks[chunkI+1].startswith(enclosure[0]):
                    end = formatted.find(chunks[chunkI+1], start)
                    if end < 0:
                        raise ValueError(
                            "{} does not match format {} (missing {} at {})"
                            .format(repr(formatted), repr(fmt),
                                    repr(chunks[chunkI+1]), start))
                else:
                    raise NotImplementedError(
                        "Chunk not followed by delimiter is not supported"
                        " (unsupported format={})".format(repr(fmt)))
            else:
                # There are no more chunks, capture the rest of the
                #   input.
                end = len(formatted)
            if isinstance(key, str):
                d[key] = formatted[start:end]
            else:
                d[key.decode()] = formatted[start:end]
            start = end
        else:
            delimiterI = formatted.find(chunk, start)
            if delimiterI < 0:
                raise ValueError("{} is missing delimiter {} at/after {}"
                                 .format(repr(formatted), repr(chunk), start))
            start = delimiterI + len(chunk)

    return d


def get_format_keys(fmt, enclosure=["{", "}"]):
    keys = []
    if isinstance(fmt, (bytes, bytearray)):
        enclosureB = bytearray()
        # # ^ Change to bytearray so int compare works below!
        for s in enclosure:
            enclosureB += s.encode()
        enclosure = enclosureB
        assert isinstance(enclosure, bytearray)
        assert isinstance(enclosure[0], int)
    else:
        assert isinstance(fmt, str)
    i = -1
    while i + 1 < len(fmt):
        i += 1
        if fmt[i] == enclosure[0]:
            end = fmt.find(enclosure[1], i)
            if end < 0:
                raise ValueError("Start %s without %s in %s"
                                 % (repr(enclosure[0]), repr(enclosure[1]),
                                    repr(fmt)))
            keys.append(fmt[i+1:end])
            i = end
    return keys


def split_subs(path):
    '''
    Convert "a/b/c" to tuple ("a", "b", "c")
    or "/a/b/c" to tuple ("/a", "b", "c").
    '''
    parts = path.split(os.path.sep)
    if len(parts[0]) == 0:
        parts = ["/" + parts[1]] + parts[2:]
    return parts


def split_root(path):
    '''
    Convert "a/b/c" to tuple ("a", "b/c") or "/a/b/c" to tuple ("/a", "b/c").
    '''
    raw_path = path
    prev_path = None
    while True:
        path = os.path.dirname(path)
        if (len(path) == 0) or (path == "/"):
            path = prev_path
            break
        elif path == prev_path:
            break
        prev_path = path
    sub = ""
    if path is None:
        path = raw_path
    else:
        sub = raw_path[len(path)+1:]
    return [path, sub]


def extract(src_file, new_parent_dir, auto_sub=True,
            auto_sub_name=None):
    '''
    Extract any known archive file type to a specified directory.

    Args:
        src_file (str): Extract this archive file.
        new_parent_dir (str): Place the extracted files into this
            directory (after temp directory).
        auto_sub (bool, optional): Automatically create a subdirectory
            only if there is more than one item directly under the root
            of the archive. If False, extract as-is to new_parent_dir
            (even if that results in a subdirectory that is the name of
            the original directory).
        auto_sub_name (str, optional): If auto_sub is true, rename the
            extracted or created directory to the value of this string.
    '''
    raise NotImplementedError("There is nothing implemented here yet.")


default_ignores = ["Thumbs.db", ".DS_Store", "error_log", "temp"]


def newest_file_dt_in(parent, too_new_dt=None, level=0,
                      ignores=default_ignores):
    '''
    Get the datetime of the latest file in parent recursively.

    Args:
        too_new_dt (datetime): skip files with a datetime >= too_new_dt
            if not None.
        level (int): Determine the directory depth for debugging use
            only (doesn't affect results).

    Returns:
        tuple(str, datetime): a tuple (path, datetime)
    '''
    if too_new_dt is not None:
        if too_new_dt.tzinfo is None:
            raise ValueError("The datetime is timezone-naive.")
    path = None
    newest_dt = None
    for sub in os.listdir(parent):
        subPath = os.path.join(parent, sub)
        if os.path.islink(subPath):
            continue
        if sub in ignores:
            continue
        if subPath in ignores:
            continue
        mdt = None
        m_path = None
        if os.path.isfile(subPath):
            # mtime = os.path.getmtime(subPath)
            mtime = pathlib.Path(subPath).stat().st_mtime
            # ^ pathlib stat best cross-platform way according to
            #   <pynative.com/python-file-creation-modification-datetime/>
            m_path = subPath
            mdt = datetime.fromtimestamp(mtime, tz=timezone.utc)
        elif os.path.isdir(subPath):
            m_path, mdt = newest_file_dt_in(
                subPath,
                too_new_dt=too_new_dt,
                level=level+1,
                ignores=ignores,
            )
        if mdt is None:
            # It must be an empty directory, or file dates are >= too_new_dt
            continue
        if (too_new_dt is None) or (mdt < too_new_dt):
            if (newest_dt is None) or (mdt > newest_dt):
                newest_dt = mdt
                path = m_path
    if newest_dt is None:
        if level == 0:
            echo0("- no date < {} could be found in {}"
                  "".format(too_new_dt, subPath))
    return path, newest_dt


def open_file(path):
    # based on <https://stackoverflow.com/a/16204023/4541104>:
    if platform.system() == "Windows":
        os.startfile(path)  # only exists on Windows
    elif platform.system() == "Darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])


def split_statement(statement):
    '''
    Split a string of multiple arguments (respecting quotes) into a list.
    '''
    isinstance(statement, str)
    ins = StringIO(statement)
    reader = csv.reader(ins, delimiter=" ")
    parts = None
    for row in reader:
        if parts is not None:
            RuntimeError("The statement must be only one line: '''\n{}\n'''"
                         "".format(statement))
        parts = row
    for i in range(len(parts)):
        if parts[i].startswith('"') and parts[i].endswith('"'):
            parts[i] = parts[i][1:-1]
        elif parts[i].startswith("'") and parts[i].endswith("'"):
            parts[i] = parts[i][1:-1]
    return parts


def parse_statement(statement):
    result = {}
    assert isinstance(statement, str)
    parts = split_statement(statement)
    if len(parts) > 0:
        result['keyword'] = parts[0]
    else:
        raise ValueError('The keyword "{}" is blank'.format(statement))
    if parts[0] == "sub":
        warnings.warn("'sub' keyword is deprecated")
        if len(parts) != 2:
            raise ValueError(
                "The {} keyword has {} argument(s) but should have 1:"
                " (source)"
                "".format(statement, len(parts)-1)
            )
        result['source'] = parts[1]
    elif parts[0] == "use":
        if (len(parts) == 4) and (parts[2] == "as"):
            # use <source> as <destination>
            result['source'] = parts[1]
            result['destination'] = parts[3]
        elif (len(parts) == 3) and (parts[1] == "as"):
            # The whole thing is the source in a "use as" statement like
            # use as <destination>
            result['destination'] = parts[2]
        else:
            raise ValueError(
                'The {} keyword has {} argument(s) but should have 2 or 3:'
                ' (source, "as", destination)'
                ' or ("as", destination)'
                ''.format(statement, len(parts)-1)
            )
    elif parts[0] == "remove_blank_lines":
        if len(parts) > 0:
            raise ValueError("Unexpected argument(s) after keyword: {}"
                             .format(parts))
    else:
        raise ValueError(
            'The keyword {} is unknown in statement {}'
            .format(repr(parts[0]), repr(statement))
        )
    return result


def d_quote(value):
    if value is None:
        return None
    elif value is False:
        return False
    elif value is True:
        return False
    elif isinstance(value, (bytes, bytearray)):
        return hex(value)
    elif not isinstance(value, str):
        return str(value)
    return '"{}"'.format(value.replace('"', '\\"'))


def statement_to_str(statement_d):
    assert isinstance(statement_d, (dict, OrderedDict))
    parts = [statement_d['keyword']]
    if 'source' in statement_d:
        assert statement_d['source'].strip()
        parts.append(d_quote(statement_d['source']))
    if 'destination' in statement_d:
        parts.append("as")
        assert statement_d['destination'].strip()
        parts.append(d_quote(statement_d['destination']))
    if 'preprocess' in statement_d:
        parts.append("preprocess")
        parts += statement_d['preprocess']
    return " ".join(parts)


def statement_to_caption(statement_d):
    if not isinstance(statement_d, (dict, OrderedDict)):
        raise ValueError(
            "You must provide the statement dict"
            " such as from anewcommit.json or"
            " parse_statement(). Got {}"
            .format(emit_cast(statement_d))
        )
    text = statement_d.get('destination')
    if text is None:
        text = statement_d.get('source')
    if text is None:
        text = statement_d.get('keyword')
    return text


MODES = [
    'delete_then_add',
    'overlay',
]

last_luid_i = -1
used_luids = set()


def use_luid(luid):
    global last_luid_i
    used_luids.add(luid)
    luid_i = int(luid)  # saved as string, so convert to int
    if luid_i > last_luid_i:
        last_luid_i = luid_i


def gen_luid():
    global last_luid_i
    last_luid_i += 1
    new_luid = str(last_luid_i)
    used_luids.add(new_luid)
    return new_luid



# Source - https://stackoverflow.com/a/7392391
# Posted by jfs, modified by community. See post 'Timeline' for change history
# Retrieved 2026-07-17, License - CC BY-SA 3.0
TEXT_CHARS = bytearray({7,8,9,10,12,13,27} | set(range(0x20, 0x100)) - {0x7f})
def is_binary_string(bytes):
    return bool(bytes.translate(None, TEXT_CHARS))


def is_binary_file(path, size=1024):
    with open(path, "rb") as stream:
        return is_binary_string(stream.read(size))


TEXT_DOT_EXTS = [".txt", ".md", ".rst", ".php", ".c", ".h", ".cxx", ".cpp",
                 ".hxx", ".py", ".workspace", ".json", ".xml", ".htm", ".html",
                 ".css", ".js", ".yml", ".yaml", ".tex", ".inc", ".jsx"]

def read_binary_lines(path):
    lines = []
    start = 0
    end = 0
    data = b""
    with open(path, "rb") as ins:
        data = ins.readlines()
    return data


def redact_file(path, destPath=None, max_blank=0,
                remove_whitespace=False, redact=None,
                extensions=[".php", ".htm", ".html", ".js", ".inc"],
                tmpPath=None, originalPath=None):
    dotExtLower = os.path.splitext(path)[1].lower()
    pathMsg = path
    if originalPath:
        pathMsg = originalPath
    # Make paths with spaces clickable in VS Code:
    # pathMsg = 'File: "{}"'.format(pathMsg)  # Doesn't help
    pathMsg = f'file://{urllib.parse.quote(pathMsg)}'

    pathSub = os.path.split(path)[1]
    if pathSub in redact['exclude']:
        logger.warning("{}: Skipping excluded file.".format(pathMsg))
        return

    assert 'mysql' in redact, '"mysql" required in "redact" anewcommit.json'
    mysqlD = redact['mysql']
    if extensions:
        if dotExtLower not in extensions:
            # Not a PHP file, so can't redact.
            return
    elif is_binary_file(path):
        dotExtLower = os.path.splitext(path)[1].lower()
        if dotExtLower in TEXT_DOT_EXTS:
            logger.warning("* [redact_all] using binary file as"
                            " text is due to text due to extension: {}"
                            .format(repr(path)))
        else:
            logger.warning("* [redact_all] skipping binary: {}"
                            .format(repr(path)))
            return
    if destPath is None:
        destPath = path
    if tmpPath is None:
        tmpPath = destPath + ".tmp"
    # if os.path.realpath(destPath) == os.path.realpath(path):
    blanks = 0
    # Deprecates redact_mysql_statements from redact_gnu

    added_requires = False
    replaced_count = 0
    with open(tmpPath, "wb") as outs:
        lineN = 0
        persistentArgD = {}
        lines = None
        with open(path, "rb") as ins:
            lines = ins.readlines()
        for line in lines:
            lineN += 1  # start at 1
            processedLine = line
            if remove_whitespace:
                processedLine = line.strip()
            if not processedLine:
                blanks += 1
                if (max_blank is not None) and (blanks > max_blank):
                    # Skip more than this many blank lines
                    #   (0 to skip any blank lines)
                    continue
            else:
                blanks = 0
            if mysqlD:
                for f_i, s_call_format in enumerate(DB_LINE_FORMATS):
                    call_format = {}
                    for cKey, cValue in s_call_format.items():
                        # Convert to bytes
                        if isinstance(cValue, list):
                            call_format[cKey] = []
                            for item in cValue:
                                call_format[cKey].append(item.encode())
                            continue
                        call_format[cKey] = cValue.encode()
                    startI = line.find(call_format['starter'])
                    if startI < 0:
                        continue
                    argsI = startI + len(call_format['starter'])
                    endI = line.find(
                        call_format['ender'],
                        argsI)

                    # Preliminary split in case of multiline:
                    argsB = line[argsI:-1]
                    secrets = argsB.split(b",")
                    for i, secret in enumerate(secrets):
                        secrets[i] = secret.strip()

                    if endI < 0:
                        if s_call_format['starter'] in ("define(", "define ("):
                            sensitive_var = None
                            sensitive_vars = []
                            for tryFormat in DB_LINE_FORMATS:
                                if tryFormat['starter'] not in ("define(", "define ("):
                                    continue
                                sensitive_vars.append(tryFormat['args'][0])
                                if secrets[0] == tryFormat['args'][0]:
                                    sensitive_var = secrets[0]
                            if sensitive_var is None:
                                logger.warning(
                                    "{}, {}: Not redacting line since {}"
                                    " is not known to be a sensitive var"
                                    " (only will redact {})"
                                    .format(pathMsg, lineN, secrets[0],
                                            sensitive_vars))
                                break
                        raise NotImplementedError(
                            "{}, line {}: Multiline SQL is not implemented: {}"
                            .format(pathMsg, lineN, line))
                    argsB = line[argsI:endI]
                    secrets = argsB.split(b",")
                    secretsD = OrderedDict()
                    for i, secret in enumerate(secrets):
                        secrets[i] = secret.strip()

                    # Unless a certain literal is required
                    #   (such as define('SQLC...):
                    if s_call_format['args'][0][0] in "\"'":
                        if call_format['args'][0] not in secrets[0]:
                            # A literal was specified in the
                            #   format but not found in line.
                            continue

                    if len(secrets) != len(call_format['args']):
                        # If there isn't another function call
                        #   pattern that has a different # of args,
                        #   then raise (secrets cannot be replaced).
                        other_format = None
                        counts = [len(call_format['args'])]
                        for other in DB_LINE_FORMATS[f_i+1:]:
                            if other['starter'].encode() == call_format['starter']:
                                counts.append(len(other['args']))
                                if len(other['args']) == len(secrets):
                                    other_format = other
                        if other_format is None:
                            if not argsB.strip():
                                logger.warning(
                                    "{}, line {}: Not redacting line"
                                    " due to no args: {}"
                                    .format(pathMsg, lineN, line))
                                break
                            raise NotImplementedError(
                                "{}, line {}: Not modifying line due"
                                " to {} args"
                                " (no matching function in db_line_formats,"
                                " known arg counts for {} are {}): {}"
                                .format(pathMsg, lineN, len(secrets),
                                        call_format['starter'], counts,
                                        line))
                        continue  # match later is guaranteed in this case
                    for i, secret in enumerate(secrets):
                        keyStr = s_call_format['args'][i]
                        # *Only* clear *before* not during line
                        #    (otherwise earlier args would be lost!).
                        if keyStr == 'user':
                        #     # Switching user but *not* db should forget
                        #     #   credentials (db can be selected later).
                            persistentArgD = {}
                    hasLiterals = False
                    for i, secret in enumerate(secrets):
                        if secret.startswith(b"'"):
                            secret = secret[1:-1].replace(b"\'", b"'")
                            secrets[i] = secret
                            hasLiterals = True
                        elif secret.startswith(b'"'):
                            secret = secret[1:-1].replace(b"\\\"", b"\"")
                            secrets[i] = secret
                            if not secret.startswith(b"$"):
                                hasLiterals = True
                        else:
                            if not secret.startswith(b"$"):
                                hasLiterals = True
                        keyStr = s_call_format['args'][i]
                        secretsD[keyStr] = secrets[i]
                        assert isinstance(keyStr, str)
                        persistentArgD[keyStr] = secret
                        if keyStr == "formatted_string":
                            # Split the string into keyed values
                            #   using the call format.
                            assert 'string_format' in call_format, \
                                "'string_format' required for formatted_string"
                            assert s_call_format['args'][i] == "formatted_string", \
                                "{} != 'formatted_string'".format(repr(s_call_format['args'][i]))
                            persistentArgD.update(
                                unformat(secret, call_format['string_format'])
                            )
                    if not hasLiterals:
                        logger.warning(
                            "{}, line {}: Not redacting line"
                            " since no arguments are literals: {}"
                            .format(pathMsg, lineN, line))
                        break
                    newArgs = []
                    alias = None  # type: str|None
                    matchKey = 'user'
                    if 'user' not in persistentArgD:
                        if 'db' in persistentArgD:
                            matchKey = 'db'
                        else:
                            matchKey = None
                    # if b'user' in call_format['args']:
                    if matchKey and (matchKey in persistentArgD):
                        for redactI, tryRedact in enumerate(mysqlD):
                            # keys: alias, db, host, user, password
                            if (tryRedact[matchKey].encode()
                                    == persistentArgD[matchKey]):
                                if 'host' not in persistentArgD:
                                    logger.warning(
                                        "{}, line {}: host not detected in {} for line: {}"
                                        .format(pathMsg, lineN, persistentArgD, line))
                                    continue
                                elif (tryRedact['host'].encode()
                                      == persistentArgD['host']):
                                    alias = tryRedact['alias']
                                    break
                                elif persistentArgD['host'] == b"localhost":
                                    alias = tryRedact['alias']
                                    logger.warning(
                                        "{}, line {}: Assuming alias {} but host {} != {}"
                                        .format(pathMsg, lineN,
                                                tryRedact['alias'],
                                                tryRedact['host'],
                                                persistentArgD['host'])
                                    )
                                    break
                                else:
                                    alias = tryRedact['alias']
                                    logger.warning(
                                        "Assuming alias {} but host {} != {}"
                                        .format(tryRedact['alias'],
                                                tryRedact['host'],
                                                persistentArgD['host'])
                                    )
                                    break
                            else:
                                logger.warning(
                                    "{} != {}"
                                    .format(tryRedact[matchKey],
                                            persistentArgD[matchKey])
                                )
                        # if alias is None:
                        #     raise NotImplementedError(
                        #         "{}, line {}: db and {}"
                        #         " did not appear in: {}"
                        #         .format(pathMsg, lineN, matchKey, line))
                    if alias is None:
                        alias = persistentArgD.get('alias')
                    else:
                        persistentArgD['alias'] = alias
                    if alias is None:
                        if persistentArgD['user'] == b"User":
                            if persistentArgD['password'] == b"Password":
                                # It is just the example from
                                #   xajaxGrid/INSTALL file, so ignore it
                                #   (There is nothing to hide).
                                break  # Keep the line intact
                        raise NotImplementedError(
                            "{}, line {}: db or user (tried {}, found {})"
                            " did not appear before or in: {}"
                            .format(pathMsg, lineN, matchKey, persistentArgD,
                                    line))
                    for i, argName in enumerate(call_format['args']):
                        oldValue = secrets[i]
                        if (argName.startswith(b"'")
                                or argName.startswith(b'"')
                                or argName.startswith(b"$")):
                            newArgs.append(oldValue)
                        elif argName == b"formatted_string":
                            varNames = get_format_keys(
                                s_call_format['string_format'])
                            # formatted = partial_format(
                            #     call_format['string_format'],
                            #     redact)
                            phpVars = {}
                            for _key in varNames:
                                phpVars[_key] = \
                                    (b"{$redact->"+alias.encode()+b"->"+_key.encode()
                                     +b"}")
                            formatted = partial_format(
                                call_format['string_format'],
                                phpVars)
                            newArgs.append(
                                b'"' + formatted.replace(b"'", b"\\'") + b"'")
                        else:
                            if alias is None:
                                findArgI = None
                                for _i, _a in enumerate(call_format['args']):
                                    assert isinstance(_a, bytes)
                                    if _a == b'db':
                                        findArgI = _i
                                        break
                                if findArgI:
                                    for rI, rDict in enumerate(mysqlD):
                                        assert isinstance(rDict['db'], bytes)
                                        assert isinstance(secrets[findArgI],
                                                          bytes)
                                        if rDict['db'] == secrets[findArgI]:
                                            alias = rDict['alias']
                                            break
                            if alias is None:
                                raise NotImplementedError(
                                    "{}, line {}: Database name wasn't defined"
                                    " before using it: {}...{}"
                                    .format(pathMsg, lineN,
                                            safe_encode(line[:argsI]),
                                            safe_encode(line[endI:])))
                            newArgs.append(
                                b"{$redact->"+alias.encode()+b"->"+argName
                                +b"}")
                    oldLine = line
                    line = (line[:argsI] + b", ".join(newArgs)
                            + line[endI:])
                    print("REPLACED\n  {} with\n  {}"
                          .format(oldLine, line))
                    replaced_count += 1
                    break  # NOTE: break: redact only 1 statement/line
                for redaction in mysqlD:
                    if redaction['password'].encode() in line:
                        error = (
                            "{}, line {}: password {} was not removed!: {}"
                            .format(pathMsg, lineN,
                                    repr(redaction['password']), line))
                        if redaction['user'].encode() in line:
                            raise NotImplementedError(error)
                        else:
                            # Maybe the password was too generic,
                            #   and was found in some other context.
                            logger.warning(error)
            if (b"<?php" in line) and (b"?>" not in line):
                if not added_requires:
                    outs.write(REDACTION_REQUIRES)
                    added_requires = True
            outs.write(line)
    if os.path.isfile(destPath):
        os.remove(destPath)
    shutil.move(tmpPath, destPath)
    if replaced_count > 0 and not added_requires:
        logger.warning(
            "{}: Didn't add require statements since no multiline"
            " `<?php` block."
            .format(pathMsg))


def redact_all(path, recursive=True, destPath=None, max_blank=0,
               remove_whitespace=False, redact=None,
               extensions=[".php", ".htm", ".html", ".js", ".inc"],
               originalPath=None):
    """Remove extra newlines from text file(s).
    If binary, as determined by non-text characters present
    (unless extension is in TEXT_DOT_EXTS), is not processed.

    Args:
        path (str): File or directory to read.
        recursive (bool, optional): Whether to look in subfolders.
            Defaults to True.
        destPath (str, optional): Where to write result. Only valid if
            path is a file! Defaults to path for each file recursively.
        max_blank (int, optional): How many blank lines are allowed in a
            row. Set to None to not remove blank lines. Defaults to 0.
        remove_whitespace (bool, optional): Consider lines with
            whitespace as blank lines. Defaults to False.
        extensions (list[str]): Only redact these extensions.
            NOTE: Redaction code will be PHP in any case.
    """
    if max_blank is not None:
        assert max_blank >= 0
    if os.path.islink(path):
        logger.warning("* [redact_all] not traversing symlink: {}"
                       .format(repr(path)))
        return
    if destPath:
        if not os.path.isfile(path):
            raise ValueError(
                "You cannot specify a destPath since source is not a file: {}."
                .format(repr(path)))
    if os.path.isfile(path):
        try:
            tmpPath = path + ".tmp"
            redact_file(path, destPath=destPath, max_blank=max_blank,
                        remove_whitespace=remove_whitespace, redact=redact,
                        extensions=extensions, tmpPath=tmpPath,
                        originalPath=originalPath)
        except UnicodeDecodeError:
            logger.error("Not a unicode file: {}".format(repr(path)))
            if os.path.isfile(tmpPath):
                os.remove(tmpPath)
            raise
        return
    if not recursive:
        return
    for sub in os.listdir(path):
        subPath = os.path.join(path, sub)
        # Do *not* forward destPath argument (raises
        #   exception for a non-file above anyway).
        originalSubPath = None
        if originalPath:
            originalSubPath = os.path.join(originalPath, sub)
        redact_all(
            subPath,
            recursive=recursive,
            max_blank=max_blank,
            remove_whitespace=remove_whitespace,
            redact=redact,
            extensions=extensions,
            originalPath=originalSubPath,
        )


def find_param(haystack, needle, min_param=0, max_param=-1, fs=",",
               quotes="\"'", inline_comment_marks=["//", "#"]):
    '''
    Find the param in a function call.

    This function requires find_unquoted_not_commented and
    explode_unquoted from the parsing submodule of Poikilos' pycodetool.

    Args:
        fs (str, optional): field separator
        quotes (str, optional): what quotes are allowed
    '''
    paren1_i = find_unquoted_not_commented(haystack, "(")
    if paren1_i < 0:
        return paren1_i
    start = paren1_i + 1
    paren2_i = find_unquoted_not_commented(haystack, ")", start=start)

    return -1


def _new_process(luid=None):
    '''
    Args:
        luid (str, optional): If None, generate a LUID (a locally-unique
            ID). The value must be a node ID that is unique within the
            scope of the project file, for any use such as by gui
            component dictionaries. There is one luid for each action,
            so there may be multiple named widgets in the group. If a
            unique id is necessary for every widget in your widget
            system, you can use `luid + "." + key` for the key where key
            is the key in the action dictionary.
    '''
    if luid is None:
        luid = gen_luid()
    result = OrderedDict()
    result['luid'] = luid
    result['verb'] = "no_op"
    result['commit'] = False
    # formerly "command": "" (replaced my more types of 'statements')
    return result


VERSION_VERBS = [
    'get_version',
]
DEFAULT_VERSION_VERB = VERSION_VERBS[0]

ALL_VERBS = copy.deepcopy(VERSION_VERBS)

# TRANSITION_VERBS = [
#     'pre_process',
#     'post_process',
#     'no_op',
# ]
# ^ Deprecated.
#   - also deprecates transition_field_order,
#     _transition_template_fields, transition_template
#   - Example deprecated anewcommit.json step
#     (replaced by "functions": [list(function_name)+list(args)] in
#     VERSION_VERBS step):
# ALL_VERBS += TRANSITION_VERBS
"""
    {
      "command": "remove_blank_lines",
      "commit": true,
      "luid": "35",
      "verb": "pre_process"
    },

"""

# The special verb is get_version, and is added via add_version.

VERBS_HELP = {
    'pre_process': 'Make changes to the next version before a commit.',
    'post_process': 'Make changes to the previous version.',
    'no_op': 'Do not modify the previous version.',
}


def new_version(path, mode='delete_then_add', luid=None, name=None):
    '''
    Args:
        luid (str, optional): If None, generate a LUID. See _new_process
            for more info.
        name (str, optional): Set the visible name (Used as commit
            summary if this source is committed). If None, the name will
            be generated as the leaf of the path.
    '''
    action = _new_process(luid=luid)
    if mode not in MODES:
        raise ValueError("Mode must be one of: {}".format(MODES))

    action['path'] = path
    action['mode'] = mode  # The mode only applies to 'get_version'.
    action['verb'] = DEFAULT_VERSION_VERB
    action['commit'] = True
    if name is None:
        action['name'] = os.path.split(path)[1]
    else:
        action['name'] = name
    return action


def new_pre_process(luid=None):
    '''
    A pre-process verb affects the next version in the list of _actions.

    Args:
        luid (str, optional): If None, generate a LUID. See _new_process
            for more info.
    '''
    action = _new_process()
    action['verb'] = 'pre_process'
    action['commit'] = True
    if luid is None:
        luid = gen_luid()
    return action


def new_post_process(luid=None):
    '''
    A post-process action affects the previous version in the list of
    _actions. For example, renaming directories or files as a separate
    commit may make committing the next version more clean.

    Args:
        luid (str, optional) If None, generate a LUID. See _new_process
            for more info.
    '''
    action = _new_process()
    action['verb'] = 'post_process'
    action['commit'] = True
    return action


def join_action_path(action, statement, key, path=None):
    '''
    Args:
        action (Union[dict, OrderedDict]): This must be a statement dict
            that has the given key.
        path (str, optional): Use this as the base path. If None
            action['path'] will be used.
    '''
    # formerly first arg was action dict such as created by
    #   new_version
    assert isinstance(action, (dict, OrderedDict))
    assert isinstance(statement, (dict, OrderedDict))
    assert isinstance(key, str)
    good_keys = ['source', 'destination']
    # if action['verb'] not in VERSION_VERBS:
    #     raise ValueError(
    #         'verb is \"{}\" but should be one of the following: {}'
    #         ''.format(action['verb'], VERSION_VERBS)
    #     )
    if key not in good_keys:
        return ValueError(
            'key is \"{}\" but should be one of the following: {}'
            ''.format(key, good_keys)
        )
    if path is None:
        path = action['path']
    dst = path
    dst_sub = statement.get(key)
    if dst_sub is not None:
        if len(dst_sub.strip()) == 0:
            dst_sub = None
    if dst_sub is None:
        echo1('There is no sub path to join (luid={},'
              ' statement={}).'
              .format(action['luid'], statement))
        # raise ValueError('action["{}"] is blank.'.format(key))
    else:
        dst = os.path.join(dst, dst_sub)
    if dst.endswith(os.path.sep):
        dst = dst[:-1]
    if ".." in dst:
        raise ValueError(
            'paths must not contain ".." (luid={}, path={}, {}="{}")'
            ''.format(action['luid'], path, key, dst_sub)
        )
    return dst


def substep_to_str(ss):
    name = None
    if (len(ss) > 2) and (len(ss) < 3) and isinstance(ss[1], int):
        name = ss[2].get('path')
    else:
        # If len(ss) is 3, it is a swap operation (2 luid params)
        name = str(ss)
    if name is not None:
        name = os.path.split(name)[1]
    return name


class ANCProject:
    '''Manage a list of version directories.

    Attributes:
        project_dir (str): The metadata for the various version
            directories will be stored here.
        path (str): This is the explicit path to a project file, usually
            "anewcommit.json" in project_dir.
        _actions (list): This is a list of _actions to take, such as
            pre-processing or post-processing a version.
    '''
    default_settings = {}

    def __init__(self):
        self.path = None
        self.project_dir = None
        self.remove_redo = False  # Remove redo after undo.
        self.clear_undo()
        self.data = None
        self._actions = None
        self._complete_settings()
        self.auto_save = True

    def _complete_settings(self):
        if self.data is None:
            self.data = OrderedDict()
        if 'actions' not in self.data:
            self._actions = []
            self.data['actions'] = self._actions
        else:
            assert isinstance(self.data['actions'], list)
            self._actions = self.data['actions']

        if 'redact' not in self.data:
            self.data['redact'] = OrderedDict()
        else:
            assert isinstance(self.data['redact'], OrderedDict)

        for list_name in ('exclude', 'mysql', 'select_as_root'):
            if list_name not in self.data['redact']:
                self.data['redact'][list_name] = []
            else:
                assert isinstance(self.data['redact'][list_name], list)

    def clear_undo(self):
        self._undo_steps = []
        self._undo_step_i = -1

    def clear(self):
        self.clear_undo()
        del self._actions[:]
        # self.data['actions'] = self._actions
        # TODO: if self.auto_save: self.save()

    def has_undo(self):
        if len(self._undo_steps) < 1:
            return False
        return self._undo_step_i >= 0

    def has_redo(self):
        return self._undo_step_i+1 < len(self._undo_steps)

    def _add_undo_step(self, step):
        '''
        Add a dictionary that describes how to undo what was just done.
        '''
        step_i = self._undo_step_i
        if self.remove_redo:
            if len(self._undo_steps) > (self._undo_step_i+1):
                self._undo_steps = self._undo_steps[:self._undo_step_i+1]
        if self._undo_step_i == (len(self._undo_steps)-1):
            self._undo_steps.append(step)
            self._undo_step_i += 1
        elif self._undo_step_i < (len(self._undo_steps)-1):
            self._undo_steps.insert(self._undo_step_i+1, step)
            self._undo_step_i += 1
        else:
            return False, ("The undo step[{}]={} is not within range (len={})"
                           "".format(self._undo_step_i,
                                     self._undo_steps[self._undo_step_i],
                                     len(self._undo_steps)))
        echo1("* _add_undo_step({}) at {}".format(step, step_i))
        msg = None
        if not self.has_undo():
            msg = ("There is no undo after adding an undo step at {}"
                   "".format(step_i))
            echo0("  * "+msg)
        return True, msg

    def undo(self, redo=False):
        '''
        A substep is a command in the form of a list, and a step is a
        list of lists (commands).

        Returns:
            tuple (list, str): A tuple of list of luids that were
                affected, and error (or None) as 2nd element.
        '''
        results = {}
        results['added'] = []
        results['removed'] = []
        results['swapped'] = []
        results['swapped_luids'] = []
        do_s = "redo" if redo else "undo"
        step_i = self._undo_step_i
        if redo:
            step_i += 1
            if step_i >= len(self._undo_steps):
                return None, "There is nothing to {}.".format(do_s)
        if step_i < 0:
            return None, "There is nothing to {}.".format(do_s)
        step = self._undo_steps[step_i]
        echo1("  * {} step: {}".format(do_s, step))
        redo_step = []
        for ss in step:
            redo_ss = None
            if ss[0] == "remove":
                redo_ss = self.remove(ss[1], add_undo_step=False)
                results['removed'].append(ss[1])
            elif ss[0] == "insert":
                redo_ss = self.insert(ss[1], ss[2], add_undo_step=False)
                results['added'].append(ss[1])
            elif ss[0] == "swap":
                redo_ss = self.swap(ss[1], ss[2], add_undo_step=False)
                results['swapped'].append(ss[1])
                results['swapped'].append(ss[2])
            elif ss[0] == "swap_where_luid":
                redo_ss = self.swap(ss[1], ss[2], add_undo_step=False)
                results['swapped_luids'].append(ss[1])
                results['swapped_luids'].append(ss[2])
            else:
                return results, ("Error: {} {} isn't implemented."
                                 "".format(do_s, ss))
            if redo_ss is not None:
                redo_step.append(redo_ss)
        if redo:
            self._undo_steps[self._undo_step_i] = redo_step
            self._undo_step_i += 1
        else:
            self._undo_steps[self._undo_step_i] = redo_step
            echo1("- Added redo_step:")
            for ss in redo_step:
                echo1("  - {}".format(substep_to_str(ss)))
            # ^ Add a redo step only during undo.
            self._undo_step_i -= 1
        return results, None

    def append_action(self, action, do_save=True):
        self._actions.append(action)
        self._add_undo_step([
            ['remove', len(self._actions)-1],
        ])
        if do_save:
            self.save()

    def add_mysql_redaction(self, alias, host, user, password, db):
        # type: (str, str, str, str, str) -> None
        """Add multiline-capable redaction for every mysql_ & mysqli_
        separate from the JSON.
        - mysql*_select_db may be used later (db not on same line)

        Args:
            alias (str): Name for the PHP associative array storing
                the parameters for connecting to this database+user
                pairing (This associative array will be under the
                'redact' associative array).
        """
        assert alias
        assert not alias[0].isnumeric()  # PHP variable can't start with #
        for c in alias:
            if (not c.isalnum()) and (c not in ('_',)):
                raise AssertionError(
                    "Alias (PHP variable name) may only contain letters,"
                    " numbers, or underscores, but got {} in {}."
                    .format(repr(c), repr(alias)))
        assert host
        assert host == host.strip()
        assert user
        assert user == user.strip()
        assert password  # no strip assertion: may have space anywhere
        assert db
        assert db == db.strip()
        if self._find_redact_mysql(alias) >= 0:
            raise KeyError("Alias {} is already used"
                           .format(repr(alias)))  # prevent dup alias
        new = OrderedDict()
        new['alias'] = alias
        new['host'] = host
        new['user'] = user
        new['db'] = db
        new['password'] = password
        self.data['redact']['mysql'].append(new)

    def _find_redact_mysql(self, alias):
        for i, item in enumerate(self.data['redact']['mysql']):
            if item['alias'] == alias:
                return i
        return -1

    def add_transition(self, verb, do_save=True):
        '''
        Args:
            verb (str): Set operation string from the OPS table to
                decide what to do between versions.
        '''
        action = None
        if verb == "pre_process":
            action = new_pre_process()
        elif verb == "post_process":
            action = new_post_process()
        elif verb == "no_op":
            action = _new_process()
        else:
            raise ValueError(
                "The verb is unknown: {}"
                "".format(verb)
            )
        self.append_action(action, do_save=do_save)
        return action

    def add_version(self, path, mode='delete_then_add', do_save=True,
                    name=None):
        '''
        Args:
            path (str): This is a path to a version.
            mode (optional, str): Specify how to add the data to the
                repo.
            do_save (optional, bool): Save immediately.
            name (optional, str): Set the name (See new_version
                documentation).
        '''
        action = new_version(path, mode=mode, name=name)
        # ^ new_version raises ValueError if the mode is invalid.
        self.append_action(action, do_save=do_save)
        return action

    def insert_statement_where(self, luid, statement, direction=-1):
        '''Convert a statement to an action and insert it at the luid.

        Args:
            direction (optional, int): if -1, to pre_process, if 1,
                post_process.
        '''
        action = _new_process()
        if direction == -1:
            raise DeprecationWarning("pre_process")
            action['verb'] = 'pre_process'
        elif direction == -1:
            raise DeprecationWarning("post_process")
            action['verb'] = 'post_process'
        else:
            raise ValueError("The direction must be -1 or 1.")

        # if action['verb'] not in TRANSITION_VERBS:
        #     raise ValueError("The verb must be one of {} not {}"
        #                      "".format(TRANSITION_VERBS, action['verb']))

        # return self.insert_where('luid', luid, action,
        #                          direction=direction)

    def append_statement_where(self, luid, statement, force=False):
        '''
        Args:
            force (optional, bool): Add it even it is already in the
                list (not yet implemented).

        Returns:
            bool: True if added, otherwise false.
        '''
        statement_d = parse_statement(statement)  # raises if fails
        i = self._find_where('luid', luid)
        if self._actions[i].get('statements') is None:
            self._actions[i]['statements'] = []
        if statement_d not in self._actions[i]['statements']:
            self._actions[i]['statements'].append(statement_d)
            self.save()
            return True
        return False

    def remove_statement_where(self, luid, statement, force=False):
        '''
        Returns:
            bool: True if removed, otherwise False.
        '''
        # args = split_statement(statement)
        # if len(args) < 2:
        #     raise ValueError(
        #         'The statement "{}" does not resolve to >=2 parts: {}'
        #         ''.format(statement, args)
        #     )
        statement_d = parse_statement(statement)
        i = self._find_where('luid', luid)
        if self._actions[i].get('statements') is None:
            self._actions[i]['statements'] = []
        if statement_d in self._actions[i]['statements']:
            self._actions[i]['statements'].remove(statement_d)
            self.save()
            return True
        return False

    def _find_where(self, name, value):
        for i in range(len(self._actions)):
            if self._actions[i].get(name) == value:
                return i
        return -1

    def get_affected(self, near_index):
        '''
        Get a tuple (version index, range), where *version index* is near_index
        or the index of the version it affects, and *range* is the entire range
        of indices affecting the version that the index represents or affects.
        '''
        # prev_luid = None
        # version_luid = None  # The luid of the affected version.
        # next_luid = None
        # prev_i = None
        # next_i = None
        version_i = None  # The index of the affected version.
        near_action = self._actions[near_index]
        if near_action['verb'] in VERSION_VERBS:
            version_i = near_index
        ranges = self.get_ranges()
        # affected_range_i = None
        affected_range = None
        for range_i in range(len(ranges)):
            r = ranges[range_i]
            if near_index in r:
                # affected_range_i = range_i
                affected_range = r
        if version_i is None:
            for i in affected_range:
                if self._actions[i]['verb'] in VERSION_VERBS:
                    version_i = i
                    break
        return version_i, affected_range

    def get_ranges(self):
        '''
        Get each group of actions by version.
        '''
        ranges = []
        this_range = []
        ENDERS = VERSION_VERBS + ['pre_process']
        version_i = None
        for i in range(0, len(self._actions)):
            action = self._actions[i]
            if version_i is None:
                if action['verb'] in VERSION_VERBS:
                    version_i = i
                elif action['verb'] == 'post_process':
                    raise ValueError(
                        "{} occurs before a version"
                        "".format(action['verb'])
                    )
            else:
                if action['verb'] in ENDERS:
                    if len(this_range) > 0:
                        ranges.append(this_range)
                        this_range = []
                        version_i = None
                        if action['verb'] in VERSION_VERBS:
                            version_i = i
            this_range.append(i)

        if len(this_range) > 0:
            ranges.append(this_range)

        totals = {}
        for rI in range(len(ranges)):
            for i in ranges[rI]:
                key = str(rI)
                count = totals.get(key)
                if count is None:
                    count = 0
                if self._actions[i]['verb'] in VERSION_VERBS:
                    count += 1
                totals[key] = count
                if count > 1:
                    echo0("ENDERS={}".format(ENDERS))
                    echo0("ranges={}".format(ranges))
                    raise RuntimeError(
                        "The data wasn't grouped correctly. The action set has"
                        " more than one version."
                    )

        return ranges

    def get_action(self, luid):
        i = self._find_where('luid', luid)
        if i > -1:
            return self._actions[i]
        return None

    def _use_all_luids(self):
        bad_indices = []
        for i in range(len(self._actions)):
            action = self._actions[i]
            if action['luid'] in used_luids:
                bad_indices.append(i)
            use_luid(action['luid'])
        return bad_indices

    def load(self, path):
        with open(path, 'r') as ins:
            try:
                self.data = json.load(ins, object_pairs_hook=OrderedDict)
                self.path = path
                self._actions = self.data['actions']
                for action in self._actions:
                    for k, v in action.items():
                        action[k] = s2or3(v)
                bad_indices = self._use_all_luids()
                msg = None
                for i in bad_indices:
                    new_luid = gen_luid()
                    if msg is None:
                        msg = ""
                    msg += ("* replacing duplicate luid in {}"
                            " with {}"
                            "".format(self._actions[i], new_luid))
                    self._actions[i]['luid'] = new_luid
                self.project_dir = self.data.get('project_dir')
                if self.project_dir is None:
                    self.project_dir = os.path.dirname(path)
                self._complete_settings()
                return True, msg
            except ValueError as ex:  # Python 2 JSON decode error
                return False, str(ex)
            # except json.JSONDecodeError as ex:  # Python 3
            #     # json.JSONDecodeError never happens since
            #     # ValueError is its ancestor class.
            #     return False, str(ex)
        return False, "unknown error"

    def save(self):
        if self.path is None:
            if self.project_dir is None:
                raise RuntimeError("The project dir or path must be set.")
            self.path = os.path.join(self.project_dir, "anewcommit.json")
        tmp = self.path + ".tmp"
        with open(tmp, 'w') as outs:
            json.dump(self.data, outs, indent=2, sort_keys=True)
        if os.path.isfile(self.path):
            os.remove(self.path)
        shutil.move(tmp, self.path)
        echo1('* wrote {}'.format(repr(self.path)))
        return True

    def get_project_dir(self):
        if self.project_dir is None:
            raise RuntimeError("The project dir or path must be set.")
        return self.project_dir

    def remove(self, index, add_undo_step=True):
        action = self._actions.pop(index)
        echo1("* removed [{}]: {}".format(index, action))
        echo1("  len {}".format(len(self._actions)))
        if self.auto_save:
            self.save()
        undo_substep = [
            "insert",
            index,
            action,
        ]
        if add_undo_step:
            self._add_undo_step([undo_substep])
        return undo_substep

    def insert(self, index, action, add_undo_step=True):
        '''
        Args:
            index (int): This is an index in self._actions (usually NOT
                the same as self._actions[index].luid).
            action (dict): Insert this action dictionary.
            add_undo_step (optional, bool): This should only be False if
                an undo/redo is doing the step, or there is some
                particular internal reason not to record a step.

        Returns:
            list: an undo substep which can be appended to a step. A
                substep is a command in the form of a list, and a step
                is a list of lists (commands).
        '''
        assert isinstance(action, (dict, OrderedDict))
        if index > len(self._actions):
            raise IndexError("The index {} is beyond len {}"
                             "".format(index, len(self._actions)))
        # ^ insert at >=len actually works, so ensure the number is sane.
        self._actions.insert(index, action)
        echo1("* inserted [{}]: {}".format(index, action))
        echo1("  len {}".format(len(self._actions)))
        undo_substep = [
            "remove",
            index
        ]
        if add_undo_step:
            self._add_undo_step([undo_substep])
        if self.auto_save:
            self.save()
        return undo_substep

    def swap(self, index, other_index, add_undo_step=True):
        '''
        Args:
            add_undo_step (optional, bool) This should only be False if an undo/redo is doing the
                step, or there is some particular internal reason not to record a
                step.
        '''
        tmp_action = self._actions[index]
        self._actions[index] = self._actions[other_index]
        self._actions[other_index] = tmp_action
        undo_substep = [
            "swap",
            index,
            other_index,
        ]
        if add_undo_step:
            self._add_undo_step([undo_substep])
        if self.auto_save:
            self.save()
        return undo_substep

    def swap_where_luid(self, luid, other_luid, add_undo_step=True):
        '''
        Args:
            add_undo_step (optional, bool): This should only be False if
                an undo/redo is doing the step, or there is some
                particular internal reason not to record a step.
        '''
        index = self._find_where('luid', luid)
        other_index = self._find_where('luid', other_luid)
        if index < 0:
            raise ValueError("There is no '{}' {}".format('luid', luid))
        if other_index < 0:
            raise ValueError("There is no '{}' {}".format('luid', other_luid))

        tmp_action = self._actions[index]
        self._actions[index] = self._actions[other_index]
        self._actions[other_index] = tmp_action
        undo_substep = [
            "swap_where_luid",
            luid,
            other_luid,
        ]
        if add_undo_step:
            self._add_undo_step([undo_substep])
        if self.auto_save:
            self.save()

    def insert_where(self, name, value, action, direction=-1):
        '''
        Args:
            luid (str): Insert before this luid.
            action (dict): Insert this action dictionary.
            direction (optional, int): -1 to insert before the match, 1
                to insert afterward (or after all related
                post-processing steps if any).
        '''
        assert isinstance(action, (dict, OrderedDict))
        newI = self._find_where(name, value)
        if direction == -1:
            pass  # newI is the index of the luid in this case.
        elif direction == 1:
            at_i, at_range = self.get_affected(newI)
            newI = at_range[-1] + 1  # +1 so it is *after* any post_processes
        else:
            raise ValueError("The direction must be -1 or 1.")

        if newI < 0:
            raise ValueError("There is no {} {}".format(repr(name), value))
        return self.insert(newI, action)

    def insert_where_luid(self, luid, action, direction=-1):
        return self.insert_where('luid', luid, action,
                                 direction=direction)

    def remove_where(self, name, value):
        '''
        Args:
            luid (str): Insert before this luid.
        '''
        newI = self._find_where(name, value)
        if newI < 0:
            raise ValueError("There is no '{}' {}".format(name, value))
        return self.remove(newI)

    def remove_where_luid(self, luid):
        return self.remove_where('luid', luid)

    def set_commit(self, luid, on):
        '''
        Turn the commit option of the version or process off or on.
        '''
        action = self.get_action(luid)
        echo0("NotYetImplemented: set_commit('{}', {})"
              "".format(luid, on))

    def set_verb(self, luid, verb):
        action = self.get_action(luid)
        current_verb = None
        current_verb = action['verb']
        if current_verb in VERSION_VERBS:
            raise ValueError(
                "The verb is {} so it can't change."
                "The action parameters aren't same as for other"
                " TRANSITION_VERBS."
                .format(repr(current_verb))
            )
        echo0("NotYetImplemented: set_verb('{}', {})"
              .format(luid, verb))

    def to_dict(self):
        return {
            'project_dir': self.project_dir,
            'actions': self._actions,
        }

    def get_gitignore_path(self):
        return os.path.join(self.get_project_dir(), ".gitignore")

    def generate_rsync_files(self, ignore_root, rsync_from):
        '''Convert .gitignore to rsync pattern files.
        Get a pair of include and exclude files (one or both can be None if
        not applicable) from the projects .gitignore file.
        The --include-from must be used before --exclude-from since rsync uses
        the first matching pattern.

        For further documentation see gitignore_to_rsync_pair in
        hierosoft.ggrep.

        Args:
            ignore_root (optional, str) Behave as though the .gitignore
                file is in this folder.

        Returns:
            tuple(str,str): The names of the files that were generated.
        '''
        # formerly get_rsync_pair
        gitignore_path = self.get_gitignore_path()
        if gitignore_path is None:
            return None, None
        if not os.path.isfile(gitignore_path):
            echo0('* There is no "{}"'.format(gitignore_path))
            return None, None
        # ignore_root = os.path.dirname(gitignore_path)
        return gitignore_to_rsync_pair(
            gitignore_path,
            rsync_from,
            self.get_cache_dir(),
            ignore_root=ignore_root,
        )

    def get_cache_dir(self):
        project_dir = self.get_project_dir()
        cache_dir = os.path.join(project_dir, "_anewcommit_cache")
        if not os.path.isdir(cache_dir):
            os.makedirs(cache_dir)
        return cache_dir

    def get_cached_dir(self, name):
        path = os.path.join(self.get_cache_dir(), name)
        if not os.path.isdir(path):
            os.makedirs(path)
        return path

    def generate_cache(self, luid, do_uncommitted=False, increment_dir=None):
        """Generate/regenerate repo at the given luid increment
        (backup step to be transformed into a commit retroactively).

        Args:
            luid (int): Locally-unique step id that is unique to the
                project (anewcommit.json).
            do_uncommitted (bool, optional): do steps (versions) not
                marked as "commit". Defaults to False.
            increment_dir (str, optional): Where to perform *only one
                step*. If this is not specified, then *all* steps up to luid
                are performed. Defaults to None.

        Raises:
            NotImplementedError: Incorrect mode
            ValueError: "use" required before remove_blank_lines
            NotImplementedError: remove_blank_lines should be in
                preprocess list, and is not itself an independent
                sub-version.
            SyntaxError: Unknown preprocess command
            NotImplementedError: verb not implemented

        Returns:
            str: directory path of result
        """
        unfiltered_commits_dir = self.get_cached_dir("commits")
        out_dir = os.path.join(unfiltered_commits_dir, luid)
        last_i = self._find_where('luid', luid)
        start = 0
        if increment_dir:
            start = last_i
            out_dir = increment_dir
            echo0("* performing increment on {}".format(repr(out_dir)))
        else:
            echo0("+ generating {}".format(repr(out_dir)))
        resync = True  # always resync the first time.
        progress_max = float(last_i+1)
        for index, action in enumerate(self._actions):
            if action.get('luid') is None:
                logger.warning(f"Action {[index]} is missing 'luid'")
        for index in range(start, last_i+1):
            action = self._actions[index]
            progress_f = float(index) / progress_max
            if not do_uncommitted:
                if action.get('commit') is not True:
                    continue
            if action['verb'] in VERSION_VERBS:
                mode = action['mode']  # The mode only applies to 'get_version'
                cmd_start = [
                    'rsync',
                    '-rt',
                    # '--info=progress2',
                ]
                if mode == 'delete_then_add':
                    resync = True
                if resync:  # always resync first time.
                    cmd_start.append("--delete")
                    resync = False  # only use once (default to False)
                elif mode == 'overlay':
                    pass
                else:
                    raise NotImplementedError(f"Incorrect mode: {repr(mode)}")

                statements = action.get('statements')
                if statements is None:
                    echo0("  - {} has no statements, so it will not be used."
                          .format(action))
                    continue
                progress_subpart_increment = 1.0 / float(len(statements))
                progress_subpart = -progress_subpart_increment
                src = None
                dst = None
                preprocess = action.get('preprocesses')
                for statement_i, statement_d in enumerate(statements):
                    assert isinstance(statement_d, (dict, OrderedDict)), \
                        "New version requires statements stored as json dicts"
                    if statement_d['keyword'] == "remove_blank_lines":
                        if dst is None:
                            raise ValueError(
                                'Expected a "keyword": "use"'
                                ' before "remove_blank_lines"')
                        raise NotImplementedError(
                            "remove_blank_lines is only implemented"
                            " for preprocess list")
                        continue
                    assert statement_d['keyword'] == "use", \
                        'Expected "keyword": "use" in {}'.format(statement_d)
                    # assert " as " in statement
                    # halves = statement.split(" as ")
                    # assert halves[0].startswith("use ")
                    # srcSub = halves[0][4:].strip()
                    # dstSub = halves[1].strip()
                    # assert srcSub, \
                    #   f"redact missing src. name before 'as' in {statement}"
                    # ^ comment since "use as" is allowed for using src direct

                    # dstSub = statement_d.get('destination')
                    # assert dstSub, \
                    #     f"redact missing destination in {statement_d}"
                    #     # f"redact missing dst. name after 'as' in {statement}"
                    # otherwise implement using without destination
                    #   (Using source as root of destination)
                    # srcSub = statement_d.get('source')
                    # NOTE: source&destination are checked by
                    #   join_action_path below

                    # parsed = parse_statement(statement)

                    progress_subpart += progress_subpart_increment
                    progress_numerator = float(index) + progress_subpart
                    progress_f = progress_numerator / progress_max
                    print("{}%".format(round(progress_f*100.0, 1)))
                    cmd_parts = cmd_start.copy()
                    srcRoot = join_action_path(action, statement_d, 'source')
                    dstRoot = join_action_path(action, statement_d, 'destination',
                                               path=out_dir)
                    # src = os.path.join(srcRoot,srcSub) if srcSub else srcRoot
                    # dst = os.path.join(dstRoot, dstSub)
                    # NOTE: join_action_path already adds sub!
                    src = srcRoot
                    dst = dstRoot
                    ignore_root = src
                    # source_parts = None
                    # if action.get('source') is not None:
                    #     source_parts = split_subs(   )
                    #     # NOTE: ^ This part was never finished
                    #     while len(source_parts) > 1:
                    #         ignore_root = os.path.dirname(source_parts)
                    #         source_parts = source_parts[:-1]
                    #     source_parts = None
                    echo0('* Any absolute paths in gitignore will assume'
                          ' {} is the directory containing ".gitignore".'
                          .format(repr(ignore_root)))
                    # originalSrc = src
                    srcTemp = None
                    redact = self.data.get('redact')
                    if preprocess or redact:
                        # Copy to a temp directory for preprocessing
                        #   so we don't mangle src nor dest.
                        srcTemp = dst + "-statement-{}-tmp".format(statement_i)
                        shutil.copytree(src, srcTemp)
                        # ^ copytree raises FileExistsError if dst exists.
                        print("* generating {}".format(repr(srcTemp)))
                        redacted = False
                        this_redact = redact
                        if preprocess:
                            assert isinstance(preprocess, list), \
                                ("Expected preprocess list, got {}"
                                .format(emit_cast(preprocess)))
                            for pre_command in preprocess:
                                assert isinstance(pre_command, str)
                                print("* [generate_cache] {} in {} (from {})"
                                      .format(pre_command, srcTemp, src))
                                if pre_command == "remove_blank_lines":
                                    try:
                                        redact_all(srcTemp, redact=this_redact,
                                                   extensions=None,
                                                   originalPath=src)
                                        # ^ extensions None for security!
                                    except:
                                        logger.warning("Removing tmp: {}"
                                                       .format(repr(srcTemp)))
                                        shutil.rmtree(srcTemp)
                                        raise
                                    if this_redact:
                                        redacted = True
                                    this_redact = None  # Only redact once
                                else:
                                    raise SyntaxError(
                                        "Unknown preprocess entry: {}"
                                        .format(emit_cast(pre_command)))
                        if not redacted and this_redact:
                            print("* [generate_cache] redact in {} (from {})"
                                  .format(srcTemp, src))
                            try:
                                redact_all(srcTemp, max_blank=None,
                                           redact=this_redact,
                                           extensions=None,
                                           originalPath=src)
                                # ^ extensions None for security!
                            except:
                                logger.warning("Removing tmp: {}"
                                                .format(repr(srcTemp)))
                                shutil.rmtree(srcTemp)
                                raise
                            this_redact = None
                        # originalSrc = src
                        src = srcTemp

                    include_tmp, exclude_tmp = self.generate_rsync_files(
                        ignore_root,
                        src,
                    )
                    # The FIRST pattern is matched when using rsync, so
                    #   include must come first:
                    if include_tmp is not None:
                        cmd_parts += ['--include-from', include_tmp]
                    if exclude_tmp is not None:
                        cmd_parts += ['--exclude-from', exclude_tmp]

                    cmd_parts.append(src+"/")
                    cmd_parts.append(dst)
                    sys.stderr.write('* getting {}...'.format(repr(src)))
                    sys.stderr.flush()
                    if not os.path.isdir(dst):
                        sys.stderr.write('creating {}...'.format(repr(dst)))
                        sys.stderr.flush()
                        os.makedirs(dst)

                    # See <https://stackoverflow.com/a/61139019/4541104>:
                    print("[generate_cache] running: {}"
                          .format(shlex.join(cmd_parts)))
                    with subprocess.Popen(
                        cmd_parts, stdout=subprocess.PIPE, text=True,
                    ) as process:
                        # bufsize=1,  # allow backspace processing
                        pass
                        # for line in iter(process.stdout.readline, b''):
                        #     print(line.strip())
                    if exclude_tmp is not None:
                        os.remove(exclude_tmp)
                    if include_tmp is not None:
                        os.remove(include_tmp)
                    echo0("OK\n")
                    if srcTemp:
                        logger.warning("Removing tmp: {}".format(srcTemp))
                        shutil.rmtree(srcTemp)
                    # Clear the old info so modifier statements such as
                    #   "remove_blank_lines" require "use" before
                    #   each:
                    if statement_d['keyword'] != "use":
                        src = None
                        dst = None
            elif action['verb'] == "no_op":
                pass
            # TRANSITION_VERBS "pre_process", "post_process", "no_op"
            else:
                raise NotImplementedError(f"verb {action['verb']} is not implemented")
                if action.get('mode') is not None:
                    raise ValueError(
                        'Mode is {} but only the following verbs should have'
                        ' a mode: {}'.format(repr(action.get('mode')),
                                             VERSION_VERBS)
                    )
        print("Done generating cache: {}".format(repr(out_dir)))
        return out_dir


def main():
    echo0('Error: There is no main in "{}".'
          'It isn\'t intended to be used that way'
          ''.format(os.realpath(__file__)))
    return 1


if __name__ == "__main__":
    echo0("Import this module into your program to use it.")
    sys.exit(1)
