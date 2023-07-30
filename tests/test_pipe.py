from shshsh import I, Sh, Pipe


def test_simple_pipe():
    res = I >> "echo 123" | "grep 1"
    assert res.stdout.read() == b"123\n"


def test_multi_pipe():
    pipe = Pipe()
    pipe1 = Pipe()
    res = (
        I >> "echo 123" | Sh(f"tee {pipe1.write_path} {pipe.write_path}") % pipe1 % pipe
    )
    assert res.stdout.read() == b"123\n"
    pipe_out = I >> pipe | "grep ."
    pipe1_out = I >> pipe1 | "grep ."
    assert pipe_out.stdout.read() == b"123\n"
    assert pipe1_out.stdout.read() == b"123\n"


def test_str_function_pipe():
    def filter_non_test(line: str) -> str:
        if "test" in line:
            return line
        else:
            return ""

    res = I >> "ls tests/case" | filter_non_test | "grep 1"
    assert res.stdout.read() == b"test1\n"


def test_bytes_function_pipe():
    def filter_non_test(line: bytes) -> bytes:
        if b"test" in line:
            return line
        else:
            return b""

    res = I >> "ls tests/case" | filter_non_test | "grep 1"
    assert res.stdout.read() == b"test1\n"


def test_str_source_pipe():
    def source():
        for i in range(10):
            yield f"test{i}"

    res = I >> source() | "grep 1"
    assert res.stdout.read() == b"test1\n"


def test_bytes_source_pipe():
    def source():
        for i in range(10):
            yield f"test{i}".encode("utf8")

    res = I >> source() | "grep 1"
    assert res.stdout.read() == b"test1\n"
