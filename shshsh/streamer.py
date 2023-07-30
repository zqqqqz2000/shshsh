from typing import (
    IO,
    TextIO,
    Iterable,
    Callable,
    Union,
    TypeVar,
    List,
    Optional,
    TYPE_CHECKING,
    overload,
)
import io
import os
import copy
from threading import Thread
import inspect

if TYPE_CHECKING:
    from .shell import Sh


def bytes_streamer(stream: IO[bytes], sep: bytes = b"\n", chunk_size: int = 1024):
    chunk_data = b""
    while True:
        chunk_data += stream.read(chunk_size)
        chunks = chunk_data.split(sep)
        for chunk in chunks[:-1]:
            yield chunk
        chunk_data = chunks[-1]
        if len(chunk_data) < chunk_size:
            return


def str_streamer(stream: IO[bytes], sep: str = "\n", chunk_size: int = 1024):
    for chunk in bytes_streamer(stream, sep=sep.encode("utf8"), chunk_size=chunk_size):
        yield chunk.decode("utf8")


_T = TypeVar("_T", str, bytes)


def to_bytes(i: Union[str, bytes, None]) -> bytes:
    if i is None:
        return b""
    if isinstance(i, str):
        return i.encode("utf8")
    else:
        return i


class P:
    def __init__(
        self,
        process_func: Union[
            Callable[[_T], Union[str, bytes]],
            Callable[[], List[_T]],
            Iterable[Union[bytes, str]],
        ],
        sep: _T = ...,
        chunk_size: int = 1024,
    ) -> None:
        self._chunk_size = chunk_size
        # io -> [process_func] -> in_fd -> [thread: out_fd ->]
        self.out_fd, self.in_fd = os.pipe()
        # self.in_stream = os.fdopen(self.in_fd, "wb")
        self.io: Optional[IO[bytes]] = None
        self.t: Optional[Thread] = None
        self.process_func = process_func
        if isinstance(process_func, Iterable):
            self.arg_type = None
            if sep is ...:
                self.sep = "\n"
            else:
                self.sep = sep
            return
        signature = inspect.signature(process_func)
        if signature.parameters:
            assert (
                len(signature.parameters) == 1
            ), "the process function must have only 1 arg, which type should be in (str, bytes)"
            self.arg_type = next(iter(signature.parameters.values())).annotation
            assert self.arg_type in (
                str,
                bytes,
            ), f"the process function arg type should be in (str, bytes), but got {type(self.arg_type)}"
            if sep is ...:
                if self.arg_type is str:
                    self.sep = "\n"
                else:
                    self.sep = b"\n"
            assert isinstance(
                self.sep, self.arg_type
            ), f"sep type should same as arg_type, but sep: {type(self.sep)} arg: {self.arg_type}"
        else:
            self.arg_type = None
            if sep is ...:
                self.sep = "\n"
            else:
                self.sep = sep

    def set_source(self, io: IO[bytes]):
        assert self.arg_type is not None, "datasource function cannot have extra source"
        self.io = io

    def _stream_helper(self):
        if self.arg_type:
            if self.arg_type is str:
                streamer = str_streamer
            else:
                streamer = bytes_streamer

            for chunk in streamer(self.io, sep=self.sep, chunk_size=self._chunk_size):  # type: ignore
                res = self.process_func(chunk)  # type: ignore
                if isinstance(res, str):
                    res = res.encode("utf8")
                assert isinstance(res, bytes)
                os.write(self.in_fd, res + to_bytes(self.sep))
        elif isinstance(self.process_func, Iterable):
            for res in self.process_func:  # type: ignore
                if isinstance(res, str):
                    res = res.encode("utf8")
                os.write(self.in_fd, res + to_bytes(self.sep))  # type: ignore
        else:
            res_list = self.process_func()  # type: ignore
            for res in res_list:
                if isinstance(res, str):
                    res = res.encode("utf8")
                os.write(self.in_fd, res + to_bytes(self.sep))
        os.close(self.in_fd)

    def run(self):
        assert not self.t, "already running"
        if self.arg_type and not self.io:
            raise ValueError(
                "process function with parameter should set source before run."
            )
        t = Thread(target=self._stream_helper, daemon=True)
        t.start()
        self.t = t

    def wait(self, timeout: Optional[int] = None):
        assert self.t, "not running"
        self.t.join(timeout)

    @overload
    def __or__(self, other: Union["Sh", str]) -> "Sh":
        ...

    @overload
    def __or__(self, other: TextIO) -> None:
        ...

    def __or__(self, other: Union["Sh", str, TextIO]) -> Optional["Sh"]:
        from .shell import Sh

        if not self.t:
            self.run()
        assert self.t

        if isinstance(other, str):
            return Sh(other, stdin=self.out_fd)
        if isinstance(other, io.IOBase):
            stdout = os.fdopen(self.out_fd, "rb")
            while True:
                chunk = stdout.read(self._chunk_size)
                other.buffer.write(chunk)  # type: ignore
                if len(chunk) < self._chunk_size:
                    break
            other.flush()
            stdout.close()
        elif isinstance(other, Sh):  # type: ignore
            other = copy.copy(other)
            other.set_stdin(self.out_fd)
            return other
        else:
            raise ValueError(
                f"cannot pipe with type: {type(other)}, only accept (Sh, str)"
            )
