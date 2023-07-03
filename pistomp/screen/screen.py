from abc import ABC, abstractmethod
from dataclasses import dataclass
from math import floor
from typing import Any, List, Optional, Tuple


@dataclass
class Screen(ABC):
    width: int
    height: int
    items: List[Any]
    highlight: int
    scroll_vert: Optional[bool]

    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.highlight = 0
        self.items = self.init_items()
        self.scroll_vert = None

    @abstractmethod
    def init_items(self):
        pass

    @property
    def highlight(self):
        return self._highlight

    @highlight.setter
    def highlight(self, value):
        self._highlight = value

    def inc_highlight(self):
        self.highlight = 0 if self.highlight == len(self.items) - 1 else self.highlight + 1

    def dec_highlight(self):
        self.highlight = len(self.items) - 1 if self.highlight == 0 else self.highlight - 1

    def x_pos(self, x: float) -> int:
        return floor(x * self.width)

    def y_pos(self, y: float) -> int:
        return floor(y * self.height)

    def xy_pos(self, xy: Tuple[float, float]) -> Tuple[int, int]:
        return self.x_pos(xy[0]), self.y_pos(xy[1])

    @abstractmethod
    def build(self):
        pass





    def render_image(self, image, y0, x0=0):
        # ONLY THIS METHOD SHOULD BE USED TO PRINT AN IMAGE TO THE DISPLAY
        # TODO check and possibly transform image to assure that it will fit the display without an error

        # Wait if a lock is present (to avoid multiple async refreshes accessing the SPI simultaneously
        # If the LCD clears out during certain events, might need to increase the max wait
        self.wait_lock(0.005, 10)
        self.lock = True

        # Since rotating 270 or 90, x becomes y, y becomes x
        self.disp.image(image, 270 if self.flip else 90, x=y0, y=x0)

        # unlock so the next refresh can happen
        self.lock = False
