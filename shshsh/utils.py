from typing import TypeVar, List
import os
from pathlib import Path
from . import global_vars


_T = TypeVar("_T", str, bytes)


def split(line: _T, sep: _T = ...) -> List[_T]:
    if sep is ...:
        if isinstance(line, str):
            sep = " "  # type: ignore
        elif isinstance(line, bytes):  # type: ignore
            sep = b" "  # type: ignore
        else:
            raise ValueError(f"only support bytes or str, but got {type(line)}")

    return list(filter(None, line.split(sep)))  # type: ignore


def cwd(dir_: str = ...) -> str:
    """change/get current dir.

    :param dir_: defaults current dir.
    :return: changed dir(abs path).
    """
    if dir_ is ...:
        return os.getcwd()
    path = Path(dir_)
    if path.is_absolute():
        global_vars.CWD = str(path)
    else:
        global_vars.CWD = str((global_vars.CWD / path).resolve())
    return global_vars.CWD


exec_env = global_vars.ENV
