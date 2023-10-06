import logging
import shutil
import sys
from time import sleep
from typing import TextIO, Optional

# noinspection PyUnresolvedReferences
from colorama import just_fix_windows_console


class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    BLINK = "\033[5m"

    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    BG_BLACK = "\033[50m"
    BG_RED = "\u001b[41m"
    BG_GREEN = "\u001b[42m"
    BG_YELLOW = "\u001b[43m"
    BG_BLUE = "\u001b[44m"
    BG_MAGENTA = "\u001b[45m"
    BG_CYAN = "\u001b[46m"
    BG_WHITE = "\u001b[47m"


def print_loading_bar(
        current: Optional[int] = None,
        total: Optional[int] = None,
        info: Optional[str] = None):
    if current is None:
        raise TypeError("print_loading_bar requires a current value")
    if not isinstance(sys.stdout, LoadingConsole):
        return
    if total is not None:
        sys.stdout.loading_bar.total = total
    if current is not None:
        sys.stdout.loading_bar.current = current
    if not sys.stdout.loading_bar.visible:
        sys.stdout.loading_bar.visible = True
    if info is not None:
        sys.stdout.loading_bar.info = info
    sys.stdout.refresh_loading_bar()


def clear_loading_bar():
    if not isinstance(sys.stdout, LoadingConsole):
        return
    sys.stdout.clear_bar()


def activate_loading_bar(total: int, info: str = ""):
    if not isinstance(sys.stdout, LoadingConsole):
        return
    sys.stdout.loading_bar.visible = True
    sys.stdout.loading_bar.total = total
    sys.stdout.loading_bar.info = info


def enable_global_loading_bar():
    just_fix_windows_console()
    console = LoadingConsole(stdout=sys.stdout)
    sys.stdout = console


class LoadingBar:
    def __init__(self):
        self.total = 1
        self.current = 0
        self.visible = False
        self.info = ""

    def print(self, size: int) -> str:
        if self.total <= 0:
            # Prevent zero-division and negative numbers
            progress = 1
        else:
            progress = self.current / self.total
        info = str(self.info)
        if self.current is not None and self.total is None:
            info = f"({self.current}) " + info
        elif self.current is not None and self.total is not None:
            total = str(self.total)
            info = f"({self.current: >{len(total)}}/{total}) " + info
        count = round(size * progress)
        msg = (f"{Colors.RESET}{Colors.BG_BLACK}{Colors.WHITE}[{Colors.CYAN}{'▓' * count}▒"
               f"{Colors.WHITE}{'░' * (size - count - 1)}] {progress:.2%}{Colors.RESET} ")
        if self.info is not None:
            return msg + info
        return msg

    def clear(self):
        self.total = 1
        self.current = 0
        self.visible = False
        self.info = ""


class LoadingConsole:
    def __init__(self, stdout: TextIO = None):
        self.loading_bar = LoadingBar()
        self._current_line_buf = ""
        self.stdout = stdout
        pass

    def write(self, buf: str):
        # First step is to make sure buf contains not multiple lines
        if len(buf) > 1 and "\n" in buf:
            # buf contains a new line and other characters
            if buf.startswith("\n"):
                self.write("\n")
                self.write(buf.lstrip("\n"))
            elif buf.endswith("\n"):
                self.write(buf.rstrip("\n"))
                self.write("\n")
            else:
                # buf does not start or end with \n, but contains one in the middle
                lines = buf.split("\n")
                while len(lines) > 0:
                    line = lines.pop(0)
                    self.write(line)
                    if len(lines) > 0:
                        self.write("\n")
            return
        # No we have two cases: buf is a single \n or a string without any new line
        if buf == "\n":
            # Reset current (last) line
            self.stdout.write("\r")
            # Write line buffer to a new line and clear the buffer
            self.stdout.write(self._current_line_buf)
            self._current_line_buf = ""
            self.stdout.write("\n")
            # Print loading bar into new line
            self.refresh_loading_bar()
            return
        # Now we have a string that is not a new line, so we append it to the buffer and wait for a newline
        self._current_line_buf += buf

    def refresh_loading_bar(self):
        cols = shutil.get_terminal_size().columns
        size = int(cols * 0.7)
        self.stdout.write("\r")
        if self.loading_bar.visible:
            self.stdout.write(self.loading_bar.print(size))

    def clear_bar(self):
        self.stdout.write("\r")
        self.loading_bar.clear()

    def flush(self):
        self.stdout.flush()


if __name__ == "__main__":
    enable_global_loading_bar()
    sys.stdout.write("Test123")
    sys.stdout.write("Test456")
    sys.stdout.write("Test789")
    activate_loading_bar(100)
    logger = logging.getLogger()
    for i in range(1, 101):
        print_loading_bar(i, info=f"Test {i}")
        print(i)
        sleep(0.2)
