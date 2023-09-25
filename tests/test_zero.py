from shshsh import IZ, I


def test_origin():
    i = -1
    res = ["abc", "def\x00ghi", "jkl\x00"]
    for i, line in enumerate(I >> "ls tests/case_zeros --zero"):
        assert line == res[i]
    assert i == 2


def test_zero():
    i = -1
    res = ["abc\ndef", "ghi\njkl", ""]  # empty string cause of split the latest "\x00"
    for i, line in enumerate(IZ >> "ls tests/case_zeros --zero"):
        assert line == res[i]
    assert i == 2
