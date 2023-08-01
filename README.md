# shshsh 🐍❤️🐚
[![PyPI](https://img.shields.io/badge/python-3.8%7C3.9%7C3.10%7C3.11-blue.svg)](https://pypi.org/project/shshsh/)

Shshsh is a bridge connects python and shell.
- A simple way to write shell in python.
- Flexable.
- Support directly chain a python function in pipe.

## Installation
To install shshsh with pip, run: `pip install shshsh`

To install shshsh with conda, run: `conda install shshsh -c conda-forge`

To install shshsh from source, clone the repository and run: `pip install poetry;poetry install`

⚠️ **If you are using python3.8**: Be very careful with python function Pipe, there are known bugs!

## Basic Usage
You can use `I >> "[command]"` or `Sh("[command]")`in any Python project.

Here's an example of getting all file which name contains "test":
```python
from shshsh import I

for filename in I >> "ls" | "grep test":
    print(filename)

```

Also, you can safely pass parameter without command injection, shshsh will help you escape all bash control character:
```python
from shshsh import I
from sys import stdout

res = (I >> "echo #{}") % "dangerous; cat /etc/passwd" | stdout
res.wait()
# dangerous; cat /etc/passwd

```

The way to operate cwd:
```python
from shshsh.utils import cwd

# change dir
after_change_path = cwd("../../")

# to get current cwd, just don't give any parameter
cwd()

```

Python function or iterable can be part of chain, you no longer have to search Google (or chatgpt) repeatedly to write sed or awk😇:
```python
from shshsh import I
from sys import stdout

# as map function
def add_suffix(line: str) -> str:
    return line + ".py"

res = I >> "ls -alh" | add_suffix | "grep test" | stdout
res.wait()

# as data source
def data_source():
    for i in range(10):
        yield f"test{i}"

res = I >> data_source() | "grep test1" | stdout
res.wait()

```

By default, the stderr will directly redirect to current python process's stderr. 

But you can also keep its result by redirect expr `>=` for stderr and `>` for stdout:

```python
from shshsh import I, keep

res = I >> "ls not_exist" >= keep
res.wait()

print(res.stderr.read())

```

The redirect expr can redirect the stream to any kind of IO object:
```python
from shshsh import I

with open("res", "w") as f:
    # redirect stdout to file.
    res = I >> "echo 123" > f
    # redirect stderr to file.
    res1 = I >> "ls not_exist" >= f
    res1.wait()
    res.wait()

```
