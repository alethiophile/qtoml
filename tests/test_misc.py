#!python3

# Various tests that can't go through the toml-test testsuite

import pytest
import qtoml

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
