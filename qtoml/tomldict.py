#!python3

from .decoder import (parse_key, parse_dispatch_string, parse_int, parse_float,
                      parse_datetime, int_re, float_re, is_date_or_time)
from .common import ParseState, TOMLDecodeError
from collections.abc import Mapping
import click, pprint

class TomlElem:
    def __init__(self, string=None):
        if string is not None:
            self.string = string

    def __repr__(self):
        if hasattr(self, 'newlines') and self.newlines:
            nl, ss = '\n', '  '
        else:
            nl, ss = '', ''
        rv = type(self).__name__ + f'({nl}'
        el = []
        keys = set(['string'])
        keys.update(self.__dict__.keys())
        for i in keys:
            f = getattr(self, i)
            rs = ss + i + '='
            rs += ''.join(ss + n for n in
                          repr(f).splitlines(keepends=True))[len(ss):]
            el.append(rs)
        rv += f', {nl}'.join(el)
        rv += f'{nl})'
        return rv

class ComplexElem(TomlElem):
    def __init__(self, data):
        self.data = data

    @property
    def string(self) -> str:
        return ''.join(i.string for i in self.data)

class Whitespace(TomlElem):
    def __init__(self, allow_newlines, require_newlines, string=None):
        self.allow_newlines = allow_newlines
        self.require_newlines = require_newlines
        super().__init__(string)

    @classmethod
    def parse(cls, p, allow_newlines=True, require_newlines=False):
        wsc = " \t"
        if allow_newlines:
            wsc += "\r\n"
        s = p.advance_through_class(wsc)
        if len(s) == 0:
            return []
        if require_newlines and '\n' not in s:
            raise TOMLDecodeError("Didn't find required newline", p)
        return [cls(allow_newlines, require_newlines, s)]

class Comment(TomlElem):
    @classmethod
    def parse(cls, p):
        if not p.at_string('#'):
            raise TOMLDecodeError("Tried to parse comment at non-comment", p)
        sv = p.advance_until('\n')
        # comment element doesn't own its terminating newline
        if sv.endswith('\n'):
            sv = sv[-1]
            p._index -= 1
        return [cls(sv)]

class Key(TomlElem):
    def __init__(self, string, value):
        self.value = value
        super().__init__(string)

class Punct(TomlElem):
    def __init__(self, string):
        super().__init__(string)

class ScalarValue(TomlElem):
    def __init__(self, string, value):
        self.value = value
        super().__init__(string)

    @classmethod
    def parse(cls, p):
        if p.get(1) in ['"', "'"]:
            v, s = parse_dispatch_string(p)
        elif p.at_re(int_re):
            v, s = parse_int(p)
        elif p.at_re(float_re):
            v, s = parse_float(p)
        elif is_date_or_time(p):
            v, s = parse_datetime(p)
        else:
            raise TOMLDecodeError("can't parse scalar type", p)
        return [cls(s, v)]

class InlineDict(ComplexElem):
    pass

class InlineArray(ComplexElem):
    pass

class DataPair(ComplexElem):
    newlines = True

    def __init__(self, data, key, value):
        self.key = key
        self.value = value
        super().__init__(data)

class DictElem(ComplexElem, Mapping):
    newlines = True

    def __init__(self):
        self.keydata = {}
        super().__init__([])

    def __getitem__(self, y):
        return self.keydata[y].value.value

    def __iter__(self):
        for i in self.keydata:
            yield i

    def __len__(self):
        return len(self.keydata)

    @classmethod
    def parse(cls, p):
        rv = cls()
        while True:
            rv.data.extend(parse_blanklines(p))
            if p.at_end():
                break
            else:
                pair = parse_pair(p)[0]
                rv.data.append(pair)
                rv.keydata[pair.key.value] = pair
        return rv

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

def parse_blanklines(p, require_newlines=False):
    rv = []
    while True:
        rv.extend(Whitespace.parse(p, allow_newlines=True,
                                   require_newlines=False))
        if p.at_string('#'):
            rv.extend(Comment.parse(p))
            continue
        else:
            break
    if require_newlines:
        for i in rv:
            if isinstance(i, Whitespace) and '\n' in i.string:
                break
        else:
            raise TOMLDecodeError("Required newline not found", p)
    return rv

def parse_pair(p):
    rv = []

    k, s = parse_key(p)
    key = Key(s, k)
    rv.append(key)

    rv.extend(Whitespace.parse(p, allow_newlines=False))

    if not p.at_string('='):
        raise TOMLDecodeError(f"no = following key '\"{rv[0].string}\"'", p)
    p.advance(1)
    rv.append(Punct('='))

    rv.extend(Whitespace.parse(p, allow_newlines=False))

    value = ScalarValue.parse(p)[0]
    rv.append(value)
    return [DataPair(rv, key, value)]

class TomlDict(Mapping):
    def __init__(self, toml_string):
        # self._data = []
        # self._data = DictElem()
        if hasattr(toml_string, 'read'):
            toml_string = toml_string.read()
        self._parse(toml_string)

    def _parse(self, toml_string):
        p = ParseState(toml_string)
        self._data = DictElem.parse(p)
        # self._data.parse(p)

    #     while not p.at_end():
    #         self._data.extend(parse_blanklines(p))

    #         self._data.extend(parse_pair(p))

    #         self._data.extend(parse_blanklines(p))

    @property
    def string(self):
        return self._data.string

    def __getitem__(self, y):
        return self._data[y]

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)


@click.command()
@click.argument('inp', type=click.File('r'))
def tomldict_test(inp):
    inp_str = inp.read()
    d = TomlDict(inp_str)
    pprint.pprint(d._data, indent=2, width=140)
    pprint.pprint(dict(d), indent=2, width=140)
    print(d.string == inp_str)
