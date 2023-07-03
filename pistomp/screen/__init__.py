from __future__ import annotations
from enum import auto, Enum
from typing import Optional

from .item import Item
from .screen import Screen
from .splash import Splash


class ScreenType(Enum):
    BLANK = auto()
    SPLASH = auto()

    @classmethod
    def _missing_(cls, value: object) -> ScreenType:
        return ScreenType.BLANK


class Factory:
    def __init__(self, display):
        self.disp = display

    def create(self, screen_type: Optional[str] = None):
        s_type = ScreenType(screen_type)
        if s_type == ScreenType.SPLASH:
            return Splash(self.disp.width, self.disp.height)
