#!python3

import pytest
import qtoml

from collections import UserDict
from pathlib import Path

def test_encode_default():
    value = UserDict({'a': 10, 'b': 20})
    with pytest.raises(qtoml.TOMLEncodeError):
        qtoml.dumps(value)

    class UserDictEncoder(qtoml.TOMLEncoder):
        def default(self, obj):
            if isinstance(obj, UserDict):
                return obj.data
            # this calls the parent version which just always TypeErrors
            return super().default(obj)

    v = UserDictEncoder().encode(value)
    v2 = qtoml.dumps(value, cls=UserDictEncoder)
    assert v == v2
    nv = qtoml.loads(v)
    assert nv == value.data

def test_encode_path():
    class PathEncoder(qtoml.TOMLEncoder):
        def default(self, obj):
            if isinstance(obj, Path):
                return obj.as_posix()
            return super().default(obj)

    pval = { 'top': { 'path': Path("foo") / "bar" } }
    sval = { 'top': { 'path': "foo/bar" } }
    v = PathEncoder().encode(pval)
    v2 = qtoml.dumps(pval, cls=PathEncoder)
    assert v == v2
    nv = qtoml.loads(v)
    assert nv == { 'top': { 'path': 'foo/bar' } }

    v3 = qtoml.dumps(sval, cls=PathEncoder)
    assert v == v3
