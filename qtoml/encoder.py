#!python3

import datetime
from .decoder import key_chars

class TOMLEncodeError(Exception):
    pass

def dump(obj, fp, **kwargs):
    """Take a dict that can be TOML-encoded, encode it, and write the data to the
    file-like object fp.

    dump(obj, fp, encode_none=None)

    Because TOML does not support None/null values, by default any structure
    containing None will error on encode. If you pass the encode_none
    parameter, None will instead be encoded as that parameter. Sensible values
    might include 0, empty string, or a unique string sentinel value.

    """
    fp.write(dumps(obj, **kwargs))

def dumps(obj, **kwargs):
    """Take a dict that can be TOML-encoded, and return an encoded string.

    dumps(obj, encode_none=None)

    Because TOML does not support None/null values, by default any structure
    containing None will error on encode. If you pass the encode_none
    parameter, None will instead be encoded as that parameter. Sensible values
    might include 0, empty string, or a unique string sentinel value.

    """
    return TOMLEncoder(**kwargs).dump_sections(obj, [], False)

class TOMLEncoder:
    # spec-defined string escapes
    escapes = { "\b": "\\b", "\t": "\\t", "\n": "\\n", "\f": "\\f",
                "\r": "\\r", "\"": "\\\"", "\\": "\\\\" }

    def __init__(self, encode_none=None):
        self.encode_none = encode_none
        self.st = { str: self.dump_str, bool: self.dump_bool,
                    int: self.dump_int, float: self.dump_float,
                    datetime.datetime: self.dump_datetime,
                    datetime.date: self.dump_date,
                    datetime.time: self.dump_time }

    def _st_lookup(self, v):
        for i in self.st:
            if isinstance(v, i):
                return self.st[i]

    def is_scalar(self, v):
        if isinstance(v, tuple(self.st.keys())):
            return True
        if (isinstance(v, (list, tuple)) and
            (len(v) == 0 or self.is_scalar(v[0]))):
            return True
        if v is None and self.encode_none is None:
            raise TOMLEncodeError("TOML cannot encode None")
        elif v is None:
            return True
        return False

    def dump_bstr(self, s, multiline=False):
        delim = '"""' if multiline else '"'
        rv = delim
        for i in s:
            if ord(i) < 32 or i in '\\"':
                if i == '\n' and multiline:
                    rv += i
                elif i in self.escapes:
                    rv += self.escapes[i]
                else:
                    hv = "{:04x}".format(ord(i))
                    rv += "\\u" + hv
            else:
                rv += i
        rv += delim
        return rv

    def dump_rawstr(self, s, multiline=False):
        delim = "'''" if multiline else "'"
        if delim in s:
            raise TOMLEncodeError("raw string delimiter in raw string")
        return delim + s + delim

    def dump_str(self, s, multiline_allowed=True):
        multiline = "\n" in s
        if (("'" in s and not multiline) or "'''" in s or
            any(ord(i) < 32 and i != "\n" for i in s) or
            (multiline and not multiline_allowed)):
            # can't put these in raw string
            return self.dump_bstr(s, multiline and multiline_allowed)
        else:
            return self.dump_rawstr(s, multiline)

    def dump_bool(self, b):
        return 'true' if b else 'false'

    def dump_int(self, i):
        return str(i)

    def dump_float(self, i):
        return str(i)

    def dump_datetime(self, d):
        rv = d.isoformat()
        if rv.endswith("+00:00"):
            rv = rv[:-6] + "Z"
        return rv

    def dump_date(self, d):
        return d.isoformat()

    def dump_time(self, d):
        return d.isoformat()

    def dump_array(self, a):
        rv = "["
        if len(a) == 0:
            return "[]"
        at = None
        for i in a:
            if at is not None:
                if type(i) != at:
                    raise TOMLEncodeError("array with mixed type")
            else:
                at = type(i)
            rv += self.dump_value(i)
            rv += ", "
        rv = (rv[:-2] if rv.endswith(', ') else rv)
        return rv + "]"

    def dump_itable(self, t):
        rv = "{ "
        for k, v in t.items():
            rv += f"{self.dump_key(k)} = {self.dump_value(v)}, "
        return (rv[:-2] if rv.endswith(", ") else rv) + " }"

    def dump_key(self, k):
        if len(k) > 0 and all(i in key_chars for i in k):
            return k
        else:
            return self.dump_str(k, multiline_allowed=False)

    def dump_value(self, v):
        if isinstance(v, tuple(self.st.keys())):
            return self._st_lookup(v)(v)
        elif isinstance(v, (list, tuple)):
            return self.dump_array(v)
        elif v is None and self.encode_none is not None:
            return self.dump_value(self.encode_none)
        else:
            raise TypeError(f"bad type '{type(v)}' for dump_value")

    def dump_sections(self, obj, obj_name, tarray):
        rv = ""
        if obj_name and (any(self.is_scalar(i) for i in obj.values()) or
                         tarray or len(obj) == 0):
            rv += "[[" if tarray else "["
            rv += '.'.join(self.dump_key(i) for i in obj_name)
            rv += "]]\n" if tarray else "]\n"
        dumped_keys = set()
        # we dump first all scalars, then all single tables, then all table
        # arrays
        for k, v in obj.items():
            if self.is_scalar(v):
                rv += f"{self.dump_key(k)} = {self.dump_value(v)}\n"
                dumped_keys.add(k)
        for k, v in obj.items():
            if isinstance(v, dict):
                if len(rv) > 0:
                    rv += "\n"
                rv += self.dump_sections(v, obj_name + [k], False)
                dumped_keys.add(k)
        for k, v in obj.items():
            if isinstance(v, list) and not self.is_scalar(v):
                for ent in v:
                    if len(rv) > 0:
                        rv += "\n"
                    rv += self.dump_sections(ent, obj_name + [k], True)
                dumped_keys.add(k)
        all_keys = set(obj.keys())
        if dumped_keys != all_keys:
            not_dumped = all_keys.difference(dumped_keys)
            k1 = not_dumped.pop()
            kl = obj_name + [k1]
            raise TOMLEncodeError("got object of non-encodable type on key "
                                  f"'{'.'.join(kl)}'")
        return rv
