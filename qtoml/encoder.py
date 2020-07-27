#!python3

import datetime
from .decoder import key_chars

from typing import Dict, Any, IO, Union, Optional, Callable, Collection, List

class TOMLEncodeError(Exception):
    pass

class TOMLEncoder:
    # spec-defined string escapes
    escapes = { "\b": "\\b", "\t": "\\t", "\n": "\\n", "\f": "\\f",
                "\r": "\\r", "\"": "\\\"", "\\": "\\\\" }

    def __init__(self, encode_none: Optional[Union[int, str]] = None) -> None:
        """Create a TOML encoder.

        encode_none: the value that should replace instances of None within the
        output (if not set, any None values will raise an exception)

        """
        self.encode_none = encode_none
        self.st: Dict[type, Callable[[Any], str]] = {
            str: self.dump_str, bool: self.dump_bool,
            int: self.dump_int, float: self.dump_float,
            datetime.datetime: self.dump_datetime,
            datetime.date: self.dump_date,
            datetime.time: self.dump_time
        }

    def encode(self, obj: Any) -> str:
        o = self._get_encodable_object(obj)
        return self.dump_sections(o, [], False)

    def _get_encodable_object(self, obj: Any) -> Any:
        try:
            rv = self.default(obj)
        except (TypeError, TOMLEncodeError):
            if self._is_encodable_type(obj):
                return obj
            raise TOMLEncodeError(f"object of non-encodable type {type(obj)}")
        if not self._is_encodable_type(rv):
            raise TOMLEncodeError(f"self.default() returned non-encodable "
                                  f"object of type {type(rv)}")
        return rv

    def _st_lookup(self, v: Any) -> Optional[Callable[[Any], str]]:
        for i in self.st:
            if isinstance(v, i):
                return self.st[i]
        return None

    def _is_encodable_type(self, v: Any) -> bool:
        if (isinstance(v, tuple(self.st.keys())) or
            isinstance(v, (list, tuple, dict))):
            return True
        if v is None:
            return (self.encode_none is not None and
                    self._is_encodable_type(self.encode_none))
        return False

    def default(self, val: Any) -> Any:
        """This method should take any value and, if possible, return a TOML-encodable
        equivalent. If the value is not encodable, raise TypeError.

        The default implementation always raises TypeError.

        """
        raise TypeError(f"object of non-TOML-encodable type {type(val)}")

    def is_scalar(self, v: Any, can_tarray: bool = True) -> bool:
        if isinstance(v, tuple(self.st.keys())):
            return True
        if isinstance(v, (list, tuple)):
            if len(v) == 0 or any(self.is_scalar(i, can_tarray=False)
                                  for i in v):
                return True
            # if a list of dicts is nested under another list, it must be
            # represented as a scalar (yes, this is a horribly pathological
            # case)
            if any(isinstance(i, dict) for i in v) and not can_tarray:
                return True
        if v is None and self.encode_none is None:
            raise TOMLEncodeError("TOML cannot encode None")
        elif v is None:
            return True
        return False

    def dump_bstr(self, s: str, multiline: bool = False) -> str:
        delim = '"""' if multiline else '"'
        rv = delim
        for n, i in enumerate(s):
            if ord(i) < 32 or i in '\\"':
                if i == '\n' and multiline and n != 0:
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

    def dump_rawstr(self, s: str, multiline: bool = False) -> str:
        delim = "'''" if multiline else "'"
        if delim in s:
            raise TOMLEncodeError("raw string delimiter in raw string")
        return delim + s + delim

    def dump_str(self, s: str, multiline_allowed: bool = True) -> str:
        """This handles newlines at the start of the string specially, since multiline
        strings must escape them.

        """
        multiline = "\n" in s[1:]
        if (("'" in s and not multiline) or "'''" in s or
            any(ord(i) < 32 and i != "\n" for i in s) or
            (multiline and not multiline_allowed) or
            s.startswith("\n") or s.endswith("'")):
            # can't put these in raw string
            return self.dump_bstr(s, multiline and multiline_allowed)
        else:
            return self.dump_rawstr(s, multiline)

    def dump_bool(self, b: bool) -> str:
        return 'true' if b else 'false'

    def dump_int(self, i: int) -> str:
        return str(i)

    def dump_float(self, i: float) -> str:
        fv = str(i)
        # Python by default emits two-digit exponents with leading zeroes,
        # which violates the TOML spec.
        if 'e' in fv:
            f, e, exp = fv.rpartition('e')
            exp = str(int(exp))
            fv = f + e + exp
        return fv

    def dump_datetime(self, d: datetime.datetime) -> str:
        rv = d.isoformat()
        if rv.endswith("+00:00"):
            rv = rv[:-6] + "Z"
        return rv

    def dump_date(self, d: datetime.date) -> str:
        return d.isoformat()

    def dump_time(self, d: datetime.time) -> str:
        return d.isoformat()

    # "Collection" means sized and iterable
    def dump_array(self, a: Collection[Any]) -> str:
        rv = "["
        if len(a) == 0:
            return "[]"
        for i in a:
            rv += self.dump_value(i)
            rv += ", "
        rv = (rv[:-2] if rv.endswith(', ') else rv)
        return rv + "]"

    def dump_itable(self, t: Dict[str, Any]) -> str:
        rv = "{ "
        for k, v in t.items():
            rv += f"{self.dump_key(k)} = {self.dump_value(v)}, "
        return (rv[:-2] if rv.endswith(", ") else rv) + " }"

    def dump_key(self, k: str) -> str:
        if len(k) > 0 and all(i in key_chars for i in k):
            return k
        else:
            return self.dump_str(k, multiline_allowed=False)

    def dump_value(self, v: Any) -> str:
        if isinstance(v, tuple(self.st.keys())):
            f = self._st_lookup(v)
            # we know this will never happen due to the check; this just
            # satisfies mypy
            assert f is not None
            return f(v)
        elif isinstance(v, (list, tuple)):
            return self.dump_array(v)
        elif isinstance(v, dict):
            # if we get here, then is_scalar returned true and we have to do
            # inline arrays
            return self.dump_itable(v)
        elif v is None and self.encode_none is not None:
            return self.dump_value(self.encode_none)
        else:
            raise TypeError(f"bad type '{type(v)}' for dump_value")

    def dump_sections(self, obj: Dict[str, Any], obj_name: List[str],
                      tarray: bool) -> str:
        # dump_sections should only be called on an object that has already
        # been passed through _get_encodable_object
        if any(not isinstance(i, str) for i in obj.keys()):
            raise TOMLEncodeError("dictionary keys must all be strings")
        encodable_pairs = [ (k, self._get_encodable_object(v))
                            for k, v in obj.items() ]
        vlist = [v for k, v in encodable_pairs]
        rv = ""
        if obj_name and (any(self.is_scalar(i) for i in vlist) or
                         tarray or len(obj) == 0):
            rv += "[[" if tarray else "["
            rv += '.'.join(self.dump_key(i) for i in obj_name)
            rv += "]]\n" if tarray else "]\n"
        dumped_keys = set()
        # we dump first all scalars, then all single tables, then all table
        # arrays
        for k, v in encodable_pairs:
            if self.is_scalar(v):
                rv += f"{self.dump_key(k)} = {self.dump_value(v)}\n"
                dumped_keys.add(k)
        for k, v in encodable_pairs:
            if isinstance(v, dict):
                if len(rv) > 0:
                    rv += "\n"
                rv += self.dump_sections(v, obj_name + [k], False)
                dumped_keys.add(k)
        for k, v in encodable_pairs:
            if isinstance(v, list) and not self.is_scalar(v):
                for ent in v:
                    if len(rv) > 0:
                        rv += "\n"
                    rv += self.dump_sections(ent, obj_name + [k], True)
                rv += "\n"
                dumped_keys.add(k)
        all_keys = set(obj.keys())
        if dumped_keys != all_keys:
            not_dumped = all_keys.difference(dumped_keys)
            k1 = not_dumped.pop()
            kl = obj_name + [k1]
            raise TOMLEncodeError("got object of non-encodable type on key "
                                  f"'{'.'.join(kl)}'")
        return rv

def dump(obj: Dict[str, Any], fp: IO[str],
         encode_none: Union[int, str, None] = None,
         cls: type = TOMLEncoder) -> None:
    """Take a dict that can be TOML-encoded, encode it, and write the data to the
    file-like object fp.

    dump(obj, fp, encode_none=None)

    Because TOML does not support None/null values, by default any structure
    containing None will error on encode. If you pass the encode_none
    parameter, None will instead be encoded as that parameter. Sensible values
    might include 0, empty string, or a unique string sentinel value.

    """
    fp.write(dumps(obj, encode_none, cls=cls))

def dumps(obj: Dict[str, Any], encode_none:
          Union[int, str, None] = None,
          cls: type = TOMLEncoder) -> str:
    """Take a dict that can be TOML-encoded, and return an encoded string.

    dumps(obj, encode_none=None)

    Because TOML does not support None/null values, by default any structure
    containing None will error on encode. If you pass the encode_none
    parameter, None will instead be encoded as that parameter. Sensible values
    might include 0, empty string, or a unique string sentinel value.

    """
    return cls(encode_none).encode(obj)
