from typing import IO


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
