#!python3

# Various tests that can't go through the toml-test testsuite

import pytest
import qtoml
from collections import OrderedDict

def test_encode_none():
    value = { 'a': None }
    with pytest.raises(qtoml.encoder.TOMLEncodeError):
        qtoml.dumps(value)
    rv = qtoml.dumps(value, encode_none=0)
    cycle = qtoml.loads(rv)
    assert cycle['a'] == 0

def test_encode_unencodable():
    def func():
        pass
    # functions cannot be encoded
    value = { 'a': func }
    with pytest.raises(qtoml.encoder.TOMLEncodeError):
        qtoml.dumps(value)

def test_encode_subclass():
    value = OrderedDict(a=1, b=2, c=3, d=4, e=5)
    toml_val = qtoml.dumps(value)
    # ensure order is preserved
    assert toml_val == 'a = 1\nb = 2\nc = 3\nd = 4\ne = 5\n'
    cycle = qtoml.loads(toml_val)
    # cycle value is a plain dictionary, so this comparison is
    # order-insensitive
    assert value == cycle

def test_non_str_keys():
    value = { 1: 'foo' }
    with pytest.raises(qtoml.TOMLEncodeError):
        qtoml.dumps(value)

    class EnsureStringKeys(qtoml.TOMLEncoder):
        def default(self, o):
            if isinstance(o, dict):
                return { str(k): v for k, v in o.items() }
            return super().default(o)

    v = EnsureStringKeys().encode(value)
    assert qtoml.loads(v) == { '1': 'foo' }
