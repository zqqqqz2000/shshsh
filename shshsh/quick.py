from typing import Optional, List, IO, Union, overload, Iterable, Generator, Any
import io
import subprocess
from .pipe import Pipe
from .streamer import P
from .shell import Sh


class _I:
    def __init__(
        self,
        with_fds: Optional[List[int]] = None,
        with_stdin: Optional[Union[int, IO[bytes]]] = subprocess.PIPE,
    ) -> None:
        self.with_fds: Optional[List[int]] = with_fds
        self.with_stdin: Optional[Union[int, IO[bytes]]] = with_stdin

    @overload
    def __rshift__(self, other: str) -> Sh:
        ...

    @overload
    def __rshift__(self, other: int) -> "_I":
        ...

    @overload
    def __rshift__(self, other: Pipe) -> "_I":
        ...

    @overload
    def __rshift__(self, other: IO[bytes]) -> "_I":
        ...

    def __rshift__(
        self,
        other: Union[
            str,
            int,
            Pipe,
            IO[bytes],
            Iterable[str],
            Iterable[bytes],
            Generator[str, Any, None],
            Generator[bytes, Any, None],
        ],
    ):
        if isinstance(other, str):
            return Sh(other, pass_fds=self.with_fds or (), stdin=self.with_stdin)
        elif isinstance(other, int):
            if self.with_fds:
                return _I(with_stdin=other, with_fds=[*self.with_fds, other])
            else:
                return _I(with_stdin=other)
        elif isinstance(other, io.IOBase):
            if self.with_fds:
                return _I(with_stdin=other, with_fds=self.with_fds)  # type: ignore
            else:
                return _I(with_stdin=other)  # type: ignore
        elif isinstance(other, Iterable):
            return P(other)
        elif isinstance(other, Pipe):  # type: ignore
            if self.with_fds:
                return _I(
                    with_stdin=other.out_fd,
                    with_fds=[*self.with_fds, other.in_fd, other.out_fd],
                )
            else:
                return _I(with_stdin=other.out_fd, with_fds=[other.in_fd, other.out_fd])
        else:
            raise ValueError("only accept str(command), int(fd), IO[bytes] or Pipe")

    def __or__(self, other: str) -> Sh:
        assert isinstance(other, str), "must be string command after I | str"
        return self >> other


I = _I()
