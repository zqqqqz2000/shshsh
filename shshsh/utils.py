from typing import TypeVar, List


_T = TypeVar("_T", str, bytes)


def split(line: _T, sep: _T = ...) -> List[_T]:
    if sep is ...:
        if isinstance(line, str):
            sep = " "
        elif isinstance(line, bytes):
            sep = b" "
        else:
            raise ValueError(f"only support bytes or str, but got {type(line)}")

    return list(filter(None, line.split(sep)))  # type: ignore
