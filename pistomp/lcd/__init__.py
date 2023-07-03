from os import getcwd
from typing import Optional

from .ili9341 import ILI9341
from .lcd import LCD
from .lcdbase import LCDBase
from .lcdcolor import LCDColor
from .tool import Tool

__all__ = [
    "ILI9341",
    "Factory",
    "LCD",
    "LCDBase",
    "LCDColor",
    "Tool",
]


class Factory:
    @staticmethod
    def create(version: Optional[str] = None) -> LCD:
        if version is None:
            pass
        return ILI9341(getcwd())
