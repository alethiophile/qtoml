#!python3

import re, datetime

def load(fo):
    """Load TOML data from a file-like object fo, and return it as a dict.

    """
    s = fo.read()
    return loads(s)

class ParseState:
    """A parser state. Holds the entire input string, advances through it as
    requested. Also tracks line and column for error reporting.

    """
    def __init__(self, string, line=1, col=0):
        self._string = string
        self._index = 0
        self.line = line
        self.col = col

    def at_string(self, s):
        return self._string[self._index:self._index + len(s)] == s

    def at_end(self):
        return self._index >= len(self._string)

    def len(self):
        return len(self._string) - self._index

    def get(self, n):
        return self._string[self._index:self._index + n]

    def advance_through_class(self, cls):
        i = self._index
        while True:
            if i < len(self._string) and self._string[i] in cls:
                i += 1
            else:
                break
        return self.advance(i - self._index)

    def advance_until(self, s):
        i = self._string.find(s, self._index)
        if i == -1:
            i = len(self._string)
        else:
            i += len(s)
        return self.advance(i - self._index)

    def advance(self, n):
        d = self._string[self._index:self._index + n]
        lc = d.count('\n')
        cc = len(d.rpartition("\n")[2])
        self.line += lc
        if lc > 0:
            self.col = cc
        else:
            self.col += cc
        self._index += n
        return d

    def __repr__(self):
        return ("ParseState({}, line={}, col={})".
                format(repr(self._string), self.line, self.col))

class TOMLDecodeError(Exception):
    def __init__(self, msg, parse, *args, **kwargs):
        super().__init__("{} (line {}, column {})".
                         format(msg, parse.line, parse.col))

def parse_throwaway(p):
    s = ""
    while True:
        s += p.advance_through_class(" \t\r\n")
        if p.at_string("#"):
            s += p.advance_until("\n")
        else:
            break
    lines = s.count("\n")
    return lines, p

def class_partition(cls, string):
    """Given a set of characters and a string, take the longest prefix made up of
    the characters in the set, and return a tuple of (prefix, remainder).

    """
    ns = string.lstrip(cls)
    lc = len(string) - len(ns)
    return (string[:lc], string[lc:])

def class_rpartition(cls, string):
    """As class_partition, but for rpartition/rstrip"""
    ns = string.rstrip(cls)
    lc = len(string) - len(ns)
    if lc == 0:
        return (string, '')
    return (string[:-lc], string[-lc:])

escape_vals = { 'b': "\b", 't': "\t", 'n': "\n", 'f': "\f", 'r': "\r",
                '"': '"', '\\': '\\' }
def parse_string(p, delim='"', allow_escapes=True, allow_newlines=False,
                 whitespace_escape=False):
    if not p.at_string(delim):
        raise TOMLDecodeError(f"string doesn't begin with delimiter '{delim}'",
                              p)
    p.advance(len(delim))
    sv = ""
    while True:
        sv += p.advance_until(delim)
        if p.at_end() and not sv.endswith(delim):  # closing quote not found
            raise TOMLDecodeError("end of file inside string", p)
        # get all backslashes before the quote
        if allow_escapes:
            a, b = class_rpartition("\\", sv[:-len(delim)])
            if len(b) % 2 == 0:  # if backslash count is even, it's not escaped
                break
        else:
            break
        if p.at_end():
            raise TOMLDecodeError("end of file after escaped delimiter", p)
    sv = sv[:-len(delim)]
    if "\n" in sv and not allow_newlines:
        raise TOMLDecodeError("newline in basic string", p)
    control_chars = [chr(i) for i in list(range(0, 9)) + list(range(11, 32)) +
                     [127]]
    if any(i in control_chars for i in sv):
        raise TOMLDecodeError("unescaped control character in string", p)
    if allow_newlines and sv.startswith("\n"):
        sv = sv[1:]
    bs = 0
    last_subst = ''
    ws_re = re.compile(r"[ \t]*\n")
    while allow_escapes:
        bs = sv.find("\\", bs + len(last_subst))
        if bs == -1:
            break
        escape_end = bs + 2
        ev = sv[bs + 1]
        if ev in escape_vals:
            subst = escape_vals[ev]
        elif ev == 'u':
            hexval = sv[bs + 2:bs + 6]
            if len(hexval) != 4:
                raise TOMLDecodeError("hexval cutoff in \\u", p)
            try:
                iv = int(hexval, base=16)
                # spec requires we error on Unicode surrogates
                if iv > 0xd800 and iv <= 0xdfff:
                    raise TOMLDecodeError(
                        f"non-scalar unicode escape '\\u{hexval}'", p
                    )
                subst = chr(iv)
            except ValueError as e:
                raise TOMLDecodeError(f"bad hex escape '\\u{hexval}'", p) from e
            escape_end += 4
        elif ev == 'U':
            hexval = sv[bs + 2:bs + 10]
            if len(hexval) != 8:
                raise TOMLDecodeError("hexval cutoff in \\U", p)
            try:
                iv = int(hexval, base=16)
                if iv > 0xd800 and iv <= 0xdfff:
                    raise TOMLDecodeError(
                        f"non-scalar unicode escape '\\u{hexval}'", p
                    )
                subst = chr(iv)
            except (ValueError, OverflowError) as e:
                raise TOMLDecodeError(f"bad hex escape '\\U{hexval}'", p) from e
            escape_end += 8
        elif whitespace_escape and ws_re.match(sv, pos=bs + 1):
            a, b = class_partition(" \t\n", sv[bs + 2:])
            escape_end += len(a)
            subst = ''
        else:
            raise TOMLDecodeError(f"\\{ev} not a valid escape", p)
        sv = sv[:bs] + subst + sv[escape_end:]
        last_subst = subst
    return sv, p  # .advance(adv_len)

float_re = re.compile(r"[+-]?(inf|nan|(([0-9]|[1-9][0-9_]*[0-9])" +
                      r"(?P<frac>\.([0-9]|[0-9][0-9_]*[0-9]))?" +
                      r"(?P<exp>[eE][+-]?([0-9]|[1-9][0-9_]*[0-9]))?))" +
                      r"(?=([\s,\]}]|$))")
def parse_float(p):
    o = float_re.match(p._string, pos=p._index)
    if o is None:
        raise TOMLDecodeError("tried to parse_float non-float", p)
    mv = o.group(0)
    if (not (o.group('frac') or o.group('exp')) and
        not ('inf' in mv or 'nan' in mv)):
        raise TOMLDecodeError("tried to parse_float, but should be int", p)
    p.advance(len(mv))
    if '__' in mv:
        raise TOMLDecodeError("double underscore in number", p)
    sv = mv.replace('_', '')
    rv = float(sv)
    return rv, p

int_re = re.compile(r"((0[xob][0-9a-fA-F_]+)|" +
                    r"([+-]?([0-9]|[1-9][0-9_]*[0-9])))" +
                    r"(?=[\s,\]}]|$)")
def parse_int(p):
    o = int_re.match(p._string, pos=p._index)
    if o is None:
        raise TOMLDecodeError("tried to parse_int non-int", p)
    mv = o.group(0)
    p.advance(len(mv))
    if '__' in mv or re.match('0[xob]_', mv) or mv.endswith('_'):
        raise TOMLDecodeError(f"invalid underscores in int '{mv}'", p)
    sv = mv.replace('_', '')
    base = 10
    if sv.startswith('0x'):
        base = 16
        sv = sv[2:]
    elif sv.startswith('0b'):
        base = 2
        sv = sv[2:]
    elif sv.startswith('0o'):
        base = 8
        sv = sv[2:]
    try:
        rv = int(sv, base=base)
    except ValueError as e:
        raise TOMLDecodeError(f"invalid base {base} integer '{mv}'", p) from e
    return rv, p

def parse_array(p):
    rv = []
    atype = None
    if not p.at_string('['):
        raise TOMLDecodeError("tried to parse_array non-array", p)
    p.advance(1)
    n, p = parse_throwaway(p)
    while True:
        if p.at_string(']'):
            p.advance(1)
            break
        v, p = parse_value(p)
        if atype is not None:
            if type(v) != atype:
                raise TOMLDecodeError("array of mixed type", p)
        else:
            atype = type(v)
        rv.append(v)
        n, p = parse_throwaway(p)
        if p.at_string(','):
            p.advance(1)
            n, p = parse_throwaway(p)
            continue
        if p.at_string(']'):
            p.advance(1)
            break
        else:
            raise TOMLDecodeError(f"bad next char {p.get(0)} in array", p)
    return rv, p


date_res = r"(?P<year>\d{4})-(?P<month>\d\d)-(?P<day>\d\d)"
time_res = r"(?P<hr>\d\d):(?P<min>\d\d):(?P<sec>\d\d)(\.(?P<msec>\d{3,}))?"

date_re = re.compile(date_res)
time_re = re.compile(time_res)

datetime_re = re.compile(date_res + r"[T ]" + time_res +
                         r"(?P<tz>(Z|[+-]\d\d:\d\d))?")

def date_from_string(o):
    year, month, day = [int(o.group(i)) for i in ['year', 'month', 'day']]
    rv = datetime.date(year, month, day)
    return rv

def time_from_string(o):
    hour, minute, sec = [int(o.group(i)) for i in ['hr', 'min', 'sec']]
    msec_str = (o.group('msec') if o.group('msec') else "0")[:6]
    msec = int(msec_str) * 10 ** (6 - len(msec_str))
    rv = datetime.time(hour, minute, sec, msec)
    return rv

def datetime_from_string(o):
    date = date_from_string(o)
    time = time_from_string(o)
    tz = o.group('tz')
    if tz == 'Z':
        tzi = datetime.timezone.utc
    elif tz:
        td = datetime.timedelta(hours=int(tz[1:3]), minutes=int(tz[4:6]))
        if tz[0] == '-':
            td = -td
        tzi = datetime.timezone(td)
    else:
        tzi = None
    rv = datetime.datetime(date.year, date.month, date.day, time.hour,
                           time.minute, time.second, time.microsecond, tzi)
    return rv

def parse_datetime(p):
    o = datetime_re.match(p._string, pos=p._index)
    if o:
        p.advance(o.end() - o.pos)
        return datetime_from_string(o), p
    o = time_re.match(p._string, pos=p._index)
    if o:
        p.advance(o.end() - o.pos)
        return time_from_string(o), p
    o = date_re.match(p._string, pos=p._index)
    if o:
        p.advance(o.end() - o.pos)
        return date_from_string(o), p
    raise TOMLDecodeError("failed to parse datetime (shouldn't happen)", p)

def is_date_or_time(p):
    return (date_re.match(p._string, pos=p._index) or
            time_re.match(p._string, pos=p._index))

def parse_inline_table(p):
    if not p.at_string('{'):
        raise TOMLDecodeError("tried to parse_inline_table non-table", p)
    rv = {}
    p.advance(1)
    p.advance_through_class(" \t")
    while True:
        if p.at_string('}'):
            p.advance(1)
            break
        kl, p = parse_keylist(p)
        p.advance_through_class(" \t")
        if not p.at_string('='):
            raise TOMLDecodeError(f"no = after key {kl} in inline", p)
        p.advance(1)
        p.advance_through_class(" \t")
        v, p = parse_value(p)
        p.advance_through_class(" \t")
        target = proc_kl(rv, kl[:-1], False, p, set())
        k = kl[-1]
        if k in target:
            raise TOMLDecodeError(f"duplicated key '{k}' in inline", p)
        target[k] = v
        if p.at_string(','):
            p.advance(1)
            p.advance_through_class(" \t")
            continue
        if p.at_string('}'):
            p.advance(1)
            break
        else:
            raise TOMLDecodeError(f"bad next char {repr(p.get(1))}" +
                                  " in inline table", p)
    return rv, p

def parse_dispatch_string(p, multiline_allowed=True):
    if p.at_string('"""'):
        if not multiline_allowed:
            raise TOMLDecodeError("multiline string where not allowed", p)
        val, p = parse_string(p, delim='"""', allow_escapes=True,
                              allow_newlines=True, whitespace_escape=True)
    elif p.at_string('"'):
        val, p = parse_string(p, delim='"', allow_escapes=True,
                              allow_newlines=False, whitespace_escape=False)
    elif p.at_string("'''"):
        if not multiline_allowed:
            raise TOMLDecodeError("multiline string where not allowed", p)
        val, p = parse_string(p, delim="'''", allow_escapes=False,
                              allow_newlines=True, whitespace_escape=False)
    elif p.at_string("'"):
        val, p = parse_string(p, delim="'", allow_escapes=False,
                              allow_newlines=False, whitespace_escape=False)
    return val, p

def parse_value(p):
    if p.get(1) in ["'", '"']:
        val, p = parse_dispatch_string(p)
    elif p.at_string('['):
        val, p = parse_array(p)
    elif p.at_string('{'):
        val, p = parse_inline_table(p)
    elif p.at_string('true'):
        val = True
        p.advance(4)
    elif p.at_string('false'):
        val = False
        p.advance(5)
    elif int_re.match(p._string, pos=p._index):
        val, p = parse_int(p)
    elif float_re.match(p._string, pos=p._index):
        val, p = parse_float(p)
    elif is_date_or_time(p):
        val, p = parse_datetime(p)
    else:
        raise TOMLDecodeError("can't parse type", p)
    return val, p

# characters allowed in unquoted keys
key_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
def parse_key(p):
    ic = p.get(1)
    if ic in ['"', "'"]:
        k, p = parse_dispatch_string(p, multiline_allowed=False)
    elif ic in key_chars:
        k = p.advance_through_class(key_chars)
    else:
        raise TOMLDecodeError(f"'{p.get(1)}' cannot begin key", p)
    return k, p

def parse_keylist(p):
    rv = []
    while True:
        k, p = parse_key(p)
        p.advance_through_class(" \t")
        rv.append(k)
        if p.at_string('.'):
            p.advance(1)
            p.advance_through_class(" \t")
        else:
            break
    return rv, p

def parse_pair(p):
    if p.at_end():
        return (None, None), p
    kl, p = parse_keylist(p)
    p.advance_through_class(" \t")
    if not p.at_string('='):
        raise TOMLDecodeError(f"no = following key '\"{kl}\"'", p)
    p.advance(1)
    p.advance_through_class(" \t")
    v, p = parse_value(p)
    return (kl, v), p

def parse_tablespec(p):
    if not p.at_string('['):
        raise TOMLDecodeError("tried parse_tablespec on non-tablespec", p)
    p.advance(1)
    tarray = False
    if p.at_string('['):
        p.advance(1)
        tarray = True
    p.advance_through_class(" \t")
    rv, p = parse_keylist(p)
    if not p.at_string(']'):
        raise TOMLDecodeError(f"Bad char {repr(p.get(1))} in tablespec",
                              p)
    p.advance(1)
    if tarray:
        if not p.at_string(']'):
            raise TOMLDecodeError(f"Didn't close tarray properly", p)
        p.advance(1)
    return rv, p

def proc_kl(rv, kl, tarray, p, toplevel_arrays):
    """Handle a table spec keylist, modifying rv in place; returns target"""
    c = rv
    if len(kl) == 0:
        return c
    # all entries except last must be dicts
    for i in kl[:-1]:
        if i in c:
            if type(c[i]) not in [dict, list]:
                raise TOMLDecodeError(f"repeated key in keylist {repr(kl)}", p)
        else:
            c[i] = {}
        if type(c[i]) == list and id(c[i]) in toplevel_arrays:
            raise TOMLDecodeError("appended to statically defined " +
                                  f"array '{i}'", p)
        c = c[i] if type(c[i]) == dict else c[i][-1]
    fk = kl[-1]
    if tarray:
        if fk in c:
            if type(c[fk]) != list:
                raise TOMLDecodeError(f"repeated key in keylist {repr(kl)}", p)
        else:
            c[fk] = []
        if id(c[fk]) in toplevel_arrays:
            raise TOMLDecodeError("appended to statically defined " +
                                  f"array '{fk}'", p)
        c[fk].append({})
        return c[fk][-1]
    else:
        if fk in c:
            if type(c[fk]) != dict:
                raise TOMLDecodeError(f"repeated key in keylist {repr(kl)}", p)
        else:
            c[fk] = {}
        return c[fk]

def loads(string):
    """Load TOML data from the string passed in, and return it as a dict."""
    rv = {}
    cur_target = rv
    p = ParseState(string)
    first = True
    n = 0
    # this tracks tables we've already seen just so we can error out on
    # duplicates as spec requires
    toplevel_targets = set()
    toplevel_arrays = set()
    while not p.at_end():
        n2, p = parse_throwaway(p)
        n += n2
        if not first:
            if n == 0:
                raise TOMLDecodeError("Didn't find expected newline", p)
        else:
            first = False
        if p.at_string('['):
            tarray = p.get(2) == '[['
            kl, p = parse_tablespec(p)
            cur_target = proc_kl(rv, kl, tarray, p, toplevel_arrays)
            if id(cur_target) in toplevel_targets:
                raise TOMLDecodeError(f"duplicated table {kl}", p)
            toplevel_targets.add(id(cur_target))
        else:
            (kl, v), p = parse_pair(p)
            if kl is not None:
                if type(v) == list:
                    toplevel_arrays.add(id(v))
                    print("ta is", toplevel_arrays)
                target = proc_kl(cur_target, kl[:-1], False, p, set())
                k = kl[-1]
                if k in target:
                    raise TOMLDecodeError(f"Key '{k}' is repeated", p)
                target[k] = v
        n, p = parse_throwaway(p)
    return rv
