#!/usr/bin/env python3

from .decoder import load
from .encoder import dump
import dateutil.parser

import click, json, datetime

def type_tag(value):
    if isinstance(value, dict):
        d = {}
        for k, v in value.items():
            d[k] = type_tag(v)
        return d
    elif isinstance(value, list):
        a = []
        for v in value:
            a.append(type_tag(v))
        try:
            a[0]["value"]
        except KeyError:
            return a
        except (IndexError, TypeError):
            pass
        return {'type': 'array', 'value': a}
    elif isinstance(value, str):
        return {'type': 'string', 'value': value}
    elif isinstance(value, bool):
        return {'type': 'bool', 'value': str(value).lower()}
    elif isinstance(value, int):
        return {'type': 'integer', 'value': str(value)}
    elif isinstance(value, float):
        return {'type': 'float', 'value': repr(value)}
    elif isinstance(value, datetime.datetime):
        tn = 'datetime' if value.tzinfo is not None else 'datetime-local'
        return {'type': tn, 'value': value.isoformat()
                .replace('+00:00', 'Z')}
    elif isinstance(value, datetime.date):
        return {'type': 'date', 'value': value.isoformat()}
    elif isinstance(value, datetime.time):
        return {'type': 'time', 'value': value.isoformat()}
    assert False, 'Unknown type: %s' % type(value)

def to_bool(s):
    assert s in ['true', 'false']
    return s == 'true'

def date_from_string(s):
    return dateutil.parser.parse(s).date()

def time_from_string(s):
    return dateutil.parser.parse(s).time()

stypes = { 'string': str, 'bool': to_bool, 'integer': int, 'float': float,
           'datetime': dateutil.parser.parse,
           'datetime-local': dateutil.parser.parse, 'date': date_from_string,
           'time': time_from_string }
def untag(value):
    if isinstance(value, list):
        return [untag(i) for i in value]
    elif 'type' in value and 'value' in value and len(value) == 2:
        if value['type'] in stypes:
            return stypes[value['type']](value['value'])
        elif value['type'] == 'array':
            return [untag(i) for i in value['value']]
        else:
            raise Exception(f"can't understand type {value['type']}")
    else:
        return { k: untag(v) for k, v in value.items() }

@click.group()
def main():
    pass

@main.command()
@click.option("--encode-none", type=str, default=None,
              help="Value to use in place of None/null")
@click.option("--test/--no-test", default=False,
              help="Untag data for toml-test")
@click.argument('inp', type=click.File('r'))
@click.argument('out', type=click.File('w'))
def encode(inp, out, encode_none, test):
    """Encode TOML from JSON. Reads from the file INP, writes to OUT; you can pass
    '-' to either to use stdin/stdout."""
    try:
        encode_none = int(encode_none)
    except (ValueError, TypeError):
        pass
    val = json.load(inp)
    if test:
        val = untag(val)
    dump(val, out, encode_none=encode_none)

@main.command()
@click.option('--test/--no-test', default=False,
              help="Tag output for toml-test")
@click.argument('inp', type=click.File('r'))
@click.argument('out', type=click.File('w'))
def decode(inp, out, test):
    """Decode TOML to JSON. Reads from the file INP, writes to OUT; you can pass
    '-' to either to use stdin/stdout."""
    idata = load(inp)
    if test:
        idata = type_tag(idata)
    json.dump(idata, out, indent=2)

if __name__ == '__main__':
    main()
