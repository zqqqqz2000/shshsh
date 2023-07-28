import shlex
import io
import sys
import copy
import re
from typing import IO, List, Any, Tuple, Union, Pattern, Dict, Optional, TextIO
import subprocess


stdout = sys.stdout
stderr = sys.stderr

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
                        placeholder, shlex.quote(args[curr_args_idx])
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
        *args: Any,
        **kwargs: Any,
    ) -> None:
        self.proc = None
        self._stdin = stdin
        self._stdout = stdout
        self._stderr = stderr
        assert self._if_placeholder_valid(
            arg_placeholder
        ), "placeholder should must has one `*` to represent arg name, and should not as first and last char. valid e.g. `#{*}`"

        self.arg_placeholder = arg_placeholder
        self.cmd = cmd
        self._try_parse(*args, **kwargs)

    def _try_parse(self, *args: str, **kwargs: str):
        self.param_complete, self.cmd = self._parse_cmd(
            self.cmd, self.arg_placeholder, *args, **kwargs
        )

    def run(self):
        if self.param_complete:
            self.proc = subprocess.Popen(
                self.cmd, stdin=self._stdin, stderr=self._stderr, stdout=self._stderr
            )
        else:
            raise ValueError(f"some args may not fill, current cmd: {self.cmd}")

    def status(self):
        ...

    def wait(self):
        if self.proc:
            self.proc.wait()
        return self

    def __mod__(self, other: Union[Tuple[str, ...], Dict[str, str], str]):
        if isinstance(other, Tuple):
            self._try_parse(*other)
        elif isinstance(other, Dict):
            self._try_parse(**other)
        elif isinstance(other, str):  # type: ignore
            self._try_parse(other)
        else:
            raise ValueError(
                f"only accept Tuple[str] or Dict[str, str] as arg, bug got {type(other)}"
            )

        return self

    def __call__(self, *args: str, **kwargs: str) -> Any:
        self._try_parse(*args, **kwargs)
        return self

    def __or__(self, other: Union["Sh", TextIO, str]):
        if isinstance(other, io.IOBase):
            if not self.proc:
                self.run()
            assert self.proc
            assert self.proc.stdout
            sys.stdout.buffer.write(self.proc.stdout.read())
            return self
        elif isinstance(other, Sh):
            assert other.proc is None, f"cannot pipe after cmd run.({other.cmd})"
            if not self.proc:
                self.run()
            assert self.proc
            other._stdin = self.proc.stdout
            other.run()
            return other
        elif isinstance(other, str):  # type: ignore
            if not self.proc:
                self.run()
            assert self.proc
            assert self.proc.stdout
            new_sh = Sh(other, stdin=self.proc.stdout)
            return new_sh
        else:
            raise ValueError(f"chain opt not support {other}")
