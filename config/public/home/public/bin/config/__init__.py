
__all__ = [
    "header",
    "trim_margin",
    "GenericConfig"
]

import re
from enum import StrEnum
from typing import Iterator


class TermColors(StrEnum):
    RESET = "\33[0m"
    BLUE = "\33[34m"


class GenericConfig:
    verbose_output: bool = False

    def __init__(self, options: Iterator[str]):
        for option in options:
            if option == "-h" or option == "--help":
                GenericConfig.print_help()
            elif option == "-v" or option == "--verbose":
                self.verbose_output = True
            elif self.parse_option(option):
                continue
            else: break

    @classmethod
    def print_help(cls):
        pass

    def parse_option(self, option: str) -> bool:
        return False

    def log(self, message: str):
        if self.verbose_output: print(message)


margin = re.compile(r'^\s+\|')

def header(text: str) -> str:
    return f"{TermColors.BLUE}{text}{TermColors.RESET}"

def trim_margin(text: str) -> str:
    return "\n".join(
        [re.sub(margin, '', line) for line in text.splitlines()[1::] if line.rstrip()]
    )