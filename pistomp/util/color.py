from __future__ import annotations
from enum import auto, Enum
from typing import Any, Tuple


def hex_digest(val: int) -> str:
    if val > 255:
        raise ValueError
    hex_val = hex(val)[2:]
    pad = '' if len(hex_val) == 2 else '0'
    return f"{pad}{hex_val.upper()}"


class Color(Enum):
    BLACK = (auto(), (0, 0, 0))
    WHITE = (auto(), (255, 255, 255))
    GRAY = (auto(), (80, 80, 80))
    RED = (auto(), (255, 0, 0))
    GREEN = (auto(), (0, 255, 255))
    BLUE = (auto(), (0, 0, 255))
    YELLOW = (auto(), (255, 255, 0))
    CYAN = (auto(), (0, 255, 255))
    MAGENTA = (auto(), (255, 0, 255))
    SOFT_GREEN = (auto(), (70, 255, 70))
    SOFT_RED = (auto(), (255, 20, 20))
    LAVENDER = (auto(), (100, 100, 240))
    MEDIUM_VIOLET_RED = (auto(), (199, 21, 133))
    ORANGE_RED = (auto(), (255, 69, 0))
    INDIGO = (auto(), (75, 0, 130))
    PERU = (auto(), (205, 133, 63))
    SADDLE_BROWN = (auto(), (139, 69, 19))
    CORNFLOWER = (auto(), (50, 50, 255))
    BLUE_SKY = (auto(), (20, 160, 255))

    @classmethod
    def _missing_(cls, value: Any) -> Color:
        return cls.GRAY

    @property
    def rgb(self) -> Tuple[int, int, int]:
        return self.value[1]

    @property
    def hex(self) -> str:
        rgb = self.rgb
        return f"#{hex_digest(rgb[0])}{hex_digest(rgb[1])}{hex_digest(rgb[2])}"
