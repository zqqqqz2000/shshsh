from shshsh import I, keep


def test_redirect():
    res = I >> "ls not_exist" >= keep
    res.wait()
    assert res.code != 0
    assert res.stderr.read()


def test_redirect2file():
    with open("test", "w") as f:
        res = I >> "echo test" > f
        res.wait()
    assert (I >> "cat test").stdout.read() == b"test\n"
    (I >> "rm test").wait()
