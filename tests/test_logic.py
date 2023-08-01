from shshsh import I


def test_and():
    res = I >> "echo 1" & "ls not_exist" & "echo 234"
    assert res.code != 0
    assert res.stdout.read() == b""


def test_or():
    res = (I >> "echo 1" & "ls not_exist" | "echo 234").or_("echo 567")
    res.wait()
    assert res.code == 0
    assert res.stdout.read() == b"234\n"
