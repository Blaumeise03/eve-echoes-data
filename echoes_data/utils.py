import math
import os
import shutil
from enum import Enum
from time import sleep

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


def print_loading_bar(progress: float):
    cols = shutil.get_terminal_size().columns
    size = int(cols * 0.7)
    count = round(size * progress)
    msg = f"{Colors.RESET}{Colors.BG_BLACK}{Colors.WHITE}[{Colors.CYAN}{'▓'*count}▒{Colors.WHITE}{'░'*(size - count - 1)}] {progress:.2%}{Colors.RESET}"
    print(msg, end="\r")
    pass


if __name__ == "__main__":
    just_fix_windows_console()
    for i in range(1, 1001):
        print_loading_bar(i / 1000)
        sleep(0.01)
