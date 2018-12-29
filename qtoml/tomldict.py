#!python3

from .decoder import (parse_key, parse_value)
from .common import ParseState, TOMLDecodeError
from dataclasses import dataclass, fields
from functools import partial
from typing import Any, List, Dict
from collections.abc import Mapping
import click, pprint

@dataclass(repr=False)
class TomlElem:
    string: str

    def __repr__(self):
        if hasattr(self, 'newlines') and self.newlines:
            nl, ss = '\n', '  '
        else:
            nl, ss = '', ''
        rv = type(self).__name__ + f'({nl}'
        el = []
        for i in fields(self):
            f = getattr(self, i.name)
            rs = ss + i.name + '='
            rs += ''.join(ss + n for n in repr(f).splitlines(keepends=True))[len(ss):]
            el.append(rs)
        rv += f', {nl}'.join(el)
        rv += f'{nl})'
        return rv

@dataclass(repr=False)
class ComplexElem(TomlElem):
    data: List[TomlElem]

    @partial(property, fset=lambda x, y: None)
    def string(self) -> str:
        return ''.join(i.string for i in self.data)

@dataclass(repr=False)
class Whitespace(TomlElem):
    allow_newlines: bool
    require_newlines: bool

@dataclass(repr=False)
class Key(TomlElem):
    value: str

@dataclass(repr=False)
class Punct(TomlElem):
    pass

@dataclass(repr=False)
class ScalarValue(TomlElem):
    vtype: type
    value: Any

@dataclass(repr=False)
class DataPair(ComplexElem):
    key: Key
    value: ScalarValue
    newlines = True

@dataclass(repr=False)
class DictElem(ComplexElem, Mapping):
    keydata: Dict[str, DataPair]
    newlines = True

    def __getitem__(self, y):
        return self.keydata[y].value.value

    def __iter__(self):
        for i in self.keydata:
            yield i

    def __len__(self):
        return len(self.keydata)

    def parse(self, p):
        while True:
            self.data.extend(parse_blanklines(p))
            if p.at_end():
                break
            else:
                pair = parse_pair(p)[0]
                self.data.append(pair)
                self.keydata[pair.key.value] = pair

# class Stringcatcher:
#     def __init__(self, p):
#         self.p = p

#     def __enter__(self):
#         self.p.capture_string()
#         return self

#     def __exit__(self, exc_type, exc_value, traceback):
#         self.s = self.p.string_val()

#     def __str__(self):
#         return self.s

#     def __len__(self):
#         return len(self.s)

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

def parse_blanklines(p):
    with Stringcatcher(p) as s:
        n, p = parse_throwaway(p)
    if len(str(s)) == 0:
        return []
    return [Whitespace(str(s), True, True)]

def parse_whitespace(p):
    with Stringcatcher(p) as s:
        p.advance_through_class(" \t")
    if len(s) == 0:
        return []
    return [Whitespace(str(s), False, False)]

def parse_pair(p):
    rv = []

    with Stringcatcher(p) as s:
        k, p = parse_key(p)
    key = Key(str(s), k)
    rv.append(key)

    rv.extend(parse_whitespace(p))

    if not p.at_string('='):
        raise TOMLDecodeError(f"no = following key '\"{rv[0].string}\"'", p)
    p.advance(1)
    rv.append(Punct('='))

    rv.extend(parse_whitespace(p))

    with Stringcatcher(p) as s:
        v, p = parse_value(p)
    value = ScalarValue(str(s), type(v), v)
    rv.append(value)
    return [DataPair(None, rv, key, value)]

class TomlDict(Mapping):
    def __init__(self, toml_string):
        # self._data = []
        self._data = DictElem(None, [], {})
        if hasattr(toml_string, 'read'):
            toml_string = toml_string.read()
        self._parse(toml_string)

    def _parse(self, toml_string):
        p = ParseState(toml_string)
        self._data.parse(p)

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
