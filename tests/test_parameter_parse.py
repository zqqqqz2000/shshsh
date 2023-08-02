from shshsh import Sh, I
import pytest


def test_parse():
    res = Sh("echo #{}") % "test"
    assert res.stdout.read() == b"test\n"


def test_parse_named():
    res = Sh("echo #{name}") % {"name": "test"}
    assert res.stdout.read() == b"test\n"


def test_parse_mix():
    res = (
        Sh("echo #{name},#{},#{},#{}") % {"name": "test"} % "test1" % ("test2", "test3")
    )
    assert res.stdout.read() == b"test,test1,test2,test3\n"


def test_parse_inline():
    res = Sh("echo #{name},#{},#{},#{}")("test1", "test2", "test3", name="test")
    assert res.stdout.read() == b"test,test1,test2,test3\n"


def test_miss_argument():
    res = Sh("echo #{name},#{},#{},#{}")("test1", "test2", "test3")
    with pytest.raises(ValueError):
        res.run()


def test_spec_filename():
    res = I >> "cat tests/case1/spec_[token]"
    assert res.stdout.read() == b"content"
