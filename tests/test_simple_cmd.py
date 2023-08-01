from shshsh import I, Sh


def test_one_cmd():
    res = Sh("echo 123")
    assert res.stdout.read() == b"123\n"


def test_quick_cmd():
    res = I >> "echo 123"
    assert res.stdout.read() == b"123\n"


def test_get_stderr():
    res = I >> "ls not_exist"
    assert res.stderr.read()
