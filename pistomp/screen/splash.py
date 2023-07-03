from typing import Tuple
from PIL import Image, ImageDraw, ImageFont

from pistomp.util.color import Color
from .screen import Screen


class Splash(Screen):

    def __post_init__(self):
        self.up_color = Color('SOFT_GREEN')
        self.down_color = Color('SOFT_RED')
        self.font = ImageFont.truetype("DejaVuSans.ttf", 48)
        self.text = "pi Stomp!"

    def init_items(self):
        pass

    def build(self, up: bool = True, text_pos: Tuple[float, float] = (0, 0.5)):
        image = Image.new("RGB", (self.width, self.height))
        draw = ImageDraw.Draw(image)
        color = self.up_color if up else self.down_color
        draw.text(self.xy_pos(text_pos), self.text, font=self.font, fill=color)
        return image
