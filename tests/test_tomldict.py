#!python3

# import pytest
from qtoml import tomldict
from qtoml.__main__ import untag
from test_tomltest import assert_no_output, patch_floats
import json

def test_valid_decode(valid_case):
    with assert_no_output():
        json_val = untag(json.loads(valid_case['json']))
        td = tomldict.TomlDict(valid_case['toml'])
        rs = td.string
        toml_val = dict(td)
    assert rs == valid_case['toml']
    assert patch_floats(json_val) == patch_floats(toml_val)
