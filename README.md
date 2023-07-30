# shshsh 🐍❤️🐚
Shshsh is a bridge connects python and shell.
- A simple way to write shell in python.
- Flexable.
- Support directly chain a python function in pipe.

## Installation
To install shshsh with pip, run: `pip install shshsh`

To install shshsh with conda, run: `conda install shshsh -c conda-forge`

To install shshsh from source, clone the repository and run: `pip install poetry;poetry install`

## Basic Usage
You can use `I >> "[command]"` or `Sh("[command]")`in any Python object.

Here's an example of get all file which name contains "test":
```python
from shshsh import I

for filename in I >> "ls" | "grep test":
    print(filename)

```
Also, you can safely pass parameter without command injection, shshsh will help you escape all bash control character:
```python
from shshsh import I
from sys import stdout

(I >> "echo #{}") % "dangerous; cat /etc/passwd" | stdout
# dangerous; cat /etc/passwd

```
Python function or iterable can be part of chain, you no longer have to search Google (or chatgpt) repeatedly to write sed or awk😇:
```python
from shshsh import I
from sys import stdout

# as map function
def add_suffix(line: str) -> str:
    return line + ".py"

I >> "ls -alh" | add_suffix | "grep test" | stdout

# as data source
def data_source():
    for i in range(10):
        yield f"test{i}"

I >> data_source() | "grep test1" | stdout

```
