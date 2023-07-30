import shlex
from threading import Thread
from .streamer import str_streamer, bytes_streamer, P
import io
import sys
import copy
import re
from typing import (
    IO,
    Iterable,
    List,
    Generator,
    overload,
    Type,
    Any,
    Tuple,
    Union,
    Pattern,
    Dict,
    Optional,
    TextIO,
    Collection,
    Callable,
)
import subprocess

from shshsh.pipe import Pipe


class Symbol:
    def __init__(self, name: str) -> None:
        self._name = name

    def __str__(self) -> str:
        return f"Symbol[{self._name}]"


stdout = sys.stdout
stderr = sys.stderr
fork_stream = Symbol("fork_stream")

_STD = Optional[Union[IO[bytes], int]]


class Sh:
    @staticmethod
    def _if_placeholder_valid(placeholder: str) -> bool:
        """
        >>> Sh._if_placeholder_valid("x*x")
        True
        >>> Sh._if_placeholder_valid("*x")
        False
        >>> Sh._if_placeholder_valid("x*")
        False
        >>> Sh._if_placeholder_valid("xxxx*xxx")
        True
        >>> Sh._if_placeholder_valid("yyy**xxx")
        False
        """
        if placeholder.count("*") == 1:
            left, right = placeholder.split("*")
            return bool(left and right)
        else:
            return False

    @staticmethod
    def _get_placeholder_matcher(placeholder: str) -> Pattern[str]:
        left, right = placeholder.split("*")
        left_re_escape, right_re_escape = re.escape(left), re.escape(right)
        return re.compile(f"{left_re_escape}.*?{right_re_escape}")

    @staticmethod
    def _split_with_placeholder(cmd: str, placeholder: str) -> List[str]:
        """
        >>> Sh._split_with_placeholder("echo #{abc}, #{}", "#{*}")
        ['echo', '#{abc},', '#{}']
        >>> Sh._split_with_placeholder("echo #{abc},#{def}${} #{}", "#{*}")
        ['echo', '#{abc},#{def}${}', '#{}']
        """
        r = Sh._get_placeholder_matcher(placeholder=placeholder)

        # find all placeholder and record
        placeholder_list = re.findall(r, cmd)

        # replace placeholder to internal placeholder to prevent split it to different part
        internal_placeholder = "SHSH_PLACEHOLDER_SHSH"
        replaced = re.sub(r, internal_placeholder, cmd)
        cmd_replaced_list = shlex.split(replaced)

        # recover origin placeholders
        curr_placeholder_index = 0
        for i, _ in enumerate(cmd_replaced_list):
            while True:
                if internal_placeholder in cmd_replaced_list[i]:
                    if curr_placeholder_index >= len(placeholder_list):
                        raise ValueError(
                            "unknown error, cannot recover placeholder. should be a bug, place report and change to a different placeholder."
                        )
                    cmd_replaced_list[i] = cmd_replaced_list[i].replace(
                        internal_placeholder,
                        placeholder_list[curr_placeholder_index],
                        1,
                    )
                    curr_placeholder_index += 1
                else:
                    break
        return cmd_replaced_list

    @staticmethod
    def _parse_cmd(
        cmd: Union[str, List[str]], arg_placeholder: str, *args: str, **kwargs: Any
    ) -> Tuple[bool, List[str]]:
        """parse cmd and fill args and kwargs

        :param cmd: command string.
        :return: a tuple which contains if all parameter be filled, a cmd list.

        >>> Sh._parse_cmd("echo #{abc}, #{}, #{}#{efg}", '#{*}', abc='test')
        (False, ['echo', 'test,', '#{},', '#{}#{efg}'])
        >>> Sh._parse_cmd("echo #{abc}, #{}, #{}#{efg}", '#{*}', '123', abc='test', efg='xxx')
        (False, ['echo', 'test,', '123,', '#{}xxx'])
        >>> Sh._parse_cmd("echo #{abc}, #{}, #{}#{efg}", '#{*}', '123', '456', abc='test', efg='xxx')
        (True, ['echo', 'test,', '123,', '456xxx'])
        """
        cmd = copy.copy(cmd)
        if isinstance(cmd, str):
            cmd_list = Sh._split_with_placeholder(cmd, arg_placeholder)
        else:
            cmd_list = cmd

        placeholder_matcher = Sh._get_placeholder_matcher(placeholder=arg_placeholder)
        left_placeholder, right_placeholder = arg_placeholder.split("*")

        curr_args_idx = 0
        param_complete = True
        for i, _ in enumerate(cmd_list):
            for placeholder in re.findall(placeholder_matcher, cmd_list[i]):
                key = placeholder[len(left_placeholder) : -len(right_placeholder)]
                if key in kwargs:
                    cmd_list[i] = cmd_list[i].replace(
                        placeholder, shlex.quote(kwargs[key])
                    )
                    continue
                if not key and curr_args_idx < len(args):
                    cmd_list[i] = cmd_list[i].replace(
                        placeholder, shlex.quote(args[curr_args_idx]), 1
                    )
                    curr_args_idx += 1
                    continue
                param_complete = False
        return param_complete, cmd_list

    def __init__(
        self,
        cmd: str,
        arg_placeholder: str = "#{*}",
        stdin: _STD = None,
        stdout: _STD = subprocess.PIPE,
        stderr: _STD = subprocess.PIPE,
        pass_fds: Collection[int] = (),
        callback: Optional[Callable[..., Any]] = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        self._proc = None
        self._stdin = stdin
        self._stdout = stdout
        self._stderr = stderr
        self.pass_fds = pass_fds
        assert self._if_placeholder_valid(
            arg_placeholder
        ), "placeholder should must has one `*` to represent arg name, and should not as first and last char. valid e.g. `#{*}`"

        self.arg_placeholder = arg_placeholder
        self.cmd = cmd
        self.callback = callback
        self._try_parse(*args, **kwargs)

    def _try_parse(self, *args: str, **kwargs: str):
        self.param_complete, self.cmd = self._parse_cmd(
            self.cmd, self.arg_placeholder, *args, **kwargs
        )

    def set_stdin(self, stdin: Union[int, IO[bytes]]):
        assert not self._proc, "is running, cannot set stdin"
        self._stdin = stdin

    @property
    def stdout(self):
        if self._proc is None:
            self.run()
        assert self._proc
        assert self._proc.stdout
        return self._proc.stdout

    @property
    def stderr(self):
        if self._proc is None:
            self.run()
        assert self._proc
        assert self._proc.stderr
        return self._proc.stderr

    def run(self):
        assert (
            not self._proc
        ), f"cannot run twice, command {self.cmd} already run, place create a new Sh"
        if self.param_complete:
            self._proc = subprocess.Popen(
                self.cmd,
                stdin=self._stdin,
                stderr=self._stderr,
                stdout=self._stdout,
                pass_fds=self.pass_fds,
            )

            # wait done and call callback
            def wait_done():
                assert self._proc
                self._proc.wait()
                assert self.callback
                self.callback()

            if self.callback:
                Thread(target=wait_done, daemon=True).run()
        else:
            raise ValueError(f"some args may not fill, current cmd: {self.cmd}")

    def pid(self) -> int:
        assert self._proc, "process not start yet"
        return self._proc.pid

    @property
    def code(self) -> int:
        assert self._proc, "process not start yet"
        return self._proc.returncode

    def wait(self, timeout: Optional[float] = None):
        if self._proc is None:
            self.run()
        assert self._proc
        self._proc.wait(timeout=timeout)
        return self

    def __mod__(self, other: Union[Tuple[str, ...], Dict[str, str], str, Pipe]):
        if isinstance(other, Tuple):
            self._try_parse(*other)
        elif isinstance(other, Dict):
            self._try_parse(**other)
        elif isinstance(other, str):
            self._try_parse(other)
        elif isinstance(other, Pipe):  # type: ignore
            self.pass_fds = (other.in_fd, other.out_fd, *self.pass_fds)
            if other.auto_close:
                if self.callback:
                    current_callback = self.callback

                    def combine_callback():
                        assert current_callback
                        current_callback()
                        other.close_in()

                    self.callback = combine_callback
                else:
                    self.callback = other.close_in

            other.auto_close = False

            return self
        else:
            raise ValueError(
                f"only accept Tuple[str] or Dict[str, str] as arg, bug got {type(other)}"
            )

        return self

    def __call__(self, *args: str, **kwargs: str) -> Any:
        self._try_parse(*args, **kwargs)
        return self

    @overload
    def __or__(self, other: Union["Sh", TextIO, str]) -> "Sh":  # type: ignore
        ...

    @overload
    def __or__(
        self,
        other: Union[
            P,
            Callable[[bytes], Union[str, bytes]],
            Callable[[str], Union[str, bytes]],
            Iterable[Union[str, bytes]],
        ],
    ) -> P:
        ...

    def __or__(  # type: ignore
        self,
        other: Union[
            "Sh",
            TextIO,
            str,
            P,
            Callable[[Union[str, bytes]], Union[str, bytes]],
            Iterable[Union[str, bytes]],
        ],
    ) -> Union["Sh", P]:
        if isinstance(other, io.IOBase):
            if not self._proc:
                self.run()
            while True:
                chunk = self.stdout.read(1024)
                other.buffer.write(chunk)  # type: ignore
                if len(chunk) < 1024:
                    break
            other.flush()
            return self
        elif isinstance(other, Sh):
            assert other._proc is None, f"cannot pipe after cmd run.({other.cmd})"
            if not self._proc:
                self.run()
            assert self._proc
            other._stdin = self._proc.stdout
            return other
        elif isinstance(other, P):
            other.set_source(self.stdout)
            return other
        elif isinstance(other, str):
            if not other:
                return self
            if not self._proc:
                self.run()
            assert self._proc
            assert self._proc.stdout
            new_sh = Sh(other, stdin=self.stdout)
            return new_sh
        elif isinstance(other, Callable) or isinstance(other, Iterable):  # type: ignore
            p = P(other)
            self.run()
            assert self.stdout
            p.set_source(self.stdout)
            return p
        else:
            raise ValueError(f"chain opt not support {other}")

    @overload
    def iter(
        self, result_type: Type[str], sep: str = "\n", chunk_size: int = 1024
    ) -> Generator[str, Any, None]:
        ...

    @overload
    def iter(
        self, result_type: Type[bytes], sep: bytes = b"\n", chunk_size: int = 1024
    ) -> Generator[bytes, Any, None]:
        ...

    def iter(
        self,
        result_type: Union[Type[str], Type[bytes]] = str,
        sep: Union[str, bytes] = ...,
        chunk_size: int = 1024,
    ):
        if result_type is str:
            if sep is ...:
                sep = "\n"
            else:
                assert isinstance(sep, str)
            return str_streamer(self.stdout, sep=sep, chunk_size=chunk_size)
        elif result_type is bytes:
            if sep is ...:
                sep = b"\n"
            else:
                assert isinstance(sep, bytes)
            return bytes_streamer(self.stdout, sep=sep, chunk_size=chunk_size)
        else:
            raise ValueError(f"result type: {result_type} is not supported")

    def __iter__(self) -> Generator[str, Any, None]:
        return self.iter()  # type: ignore

    def __and__(self, other: Union["Sh", str]) -> "Sh":
        if self._proc is None:
            self.run()
        self.wait()
        code = self.code
        if code == 0:
            if isinstance(other, str):
                if not other:
                    return self
                res = Sh(other)
                res.run()
                return res
            elif isinstance(other, Sh):  # type: ignore
                other.run()
                return other
        return self

    def __floordiv__(self, other: Union["Sh", str]) -> "Sh":
        if self._proc is None:
            self.run()
        self.wait()
        code = self.code
        if code != 0:
            if isinstance(other, str):
                if not other:
                    return self
                res = Sh(other)
                res.run()
                return res
            elif isinstance(other, Sh):  # type: ignore
                other.run()
                return other
        return self

    def and_(self, other: Union["Sh", str]) -> "Sh":
        return self & other

    def or_(self, other: Union["Sh", str]) -> "Sh":
        return self // other
