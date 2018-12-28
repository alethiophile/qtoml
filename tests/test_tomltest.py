#!python3

import pytest, json, math
import qtoml
from io import StringIO
from contextlib import redirect_stdout, redirect_stderr, contextmanager
from qtoml.__main__ import untag

def patch_floats(d):
    if type(d) == float and math.isnan(d):
        return 'NaN'
    elif type(d) == dict:
        return { i: patch_floats(d[i]) for i in d }
    elif type(d) == list:
        return [ patch_floats(i) for i in d ]
    else:
        return d

@contextmanager
def assert_no_output():
    """This makes sure debug print statements I might add don't accidentally get
    into released versions.

    """
    so, se = StringIO(), StringIO()
    try:
        with redirect_stdout(so), redirect_stderr(se):
            yield
    finally:
        assert so.getvalue() == ''
        assert se.getvalue() == ''

def test_valid_decode(valid_case):
    with assert_no_output():
        json_val = untag(json.loads(valid_case['json']))
        toml_val = qtoml.loads(valid_case['toml'])
    # some test cases include floats with value NaN, which compare unequal to
    # themselves and thus break a plain comparison
    assert patch_floats(toml_val) == patch_floats(json_val)

def test_invalid_decode(invalid_decode_case):
    with assert_no_output():
        with pytest.raises(qtoml.decoder.TOMLDecodeError):
            qtoml.loads(invalid_decode_case['toml'])

def test_valid_encode(valid_case):
    with assert_no_output():
        json_val = untag(json.loads(valid_case['json']))
        toml_str = qtoml.dumps(json_val)
        toml_reload = qtoml.loads(toml_str)
    assert patch_floats(toml_reload) == patch_floats(json_val)

def test_invalid_encode(invalid_encode_case):
    with assert_no_output():
        json_val = untag(json.loads(invalid_encode_case['json']))
        with pytest.raises(qtoml.encoder.TOMLEncodeError):
            qtoml.dumps(json_val)
