from shshsh import I, utils


def test_ch_cwd():
    utils.cwd("tests/case")
    res = I >> "ls"
    res.wait()
    assert res.stdout.read().count(b"\n") == 6
    assert utils.cwd("../../").count("..") == 0
