#!python3

import pytest, json
import qtoml
from qtoml.__main__ import untag

def test_valid_decode(valid_case):
    json_val = untag(json.loads(valid_case['json']))
    toml_val = qtoml.loads(valid_case['toml'])
    assert toml_val == json_val

def test_invalid_decode(invalid_decode_case):
    with pytest.raises(qtoml.decoder.TOMLDecodeError):
        qtoml.loads(invalid_decode_case['toml'])

def test_valid_encode(valid_case):
    json_val = untag(json.loads(valid_case['json']))
    toml_str = qtoml.dumps(json_val)
    toml_reload = qtoml.loads(toml_str)
    assert toml_reload == json_val

def test_invalid_encode(invalid_encode_case):
    json_val = untag(json.loads(invalid_encode_case['json']))
    with pytest.raises(qtoml.encoder.TOMLEncodeError):
        qtoml.dumps(json_val)
