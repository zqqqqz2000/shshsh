import os


class PipeCloseError(Exception):
    ...


class Pipe:
    def __init__(self, first_process_auto_close: bool = True) -> None:
        self.out_fd, self.in_fd = os.pipe()
        self.out_closed, self.in_closed = False, False
        self.write_path = f"/dev/fd/{self.out_fd}"
        self.auto_close = first_process_auto_close

    def close_in(self):
        os.close(self.in_fd)

    def close_out(self):
        os.close(self.out_fd)
