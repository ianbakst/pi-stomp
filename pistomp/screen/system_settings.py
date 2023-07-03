import logging
import os
import pkg_resources
import time
from typing import Dict, Optional, Tuple

import board
import digitalio
from PIL import Image, ImageDraw, ImageFont
import adafruit_rgb_display.ili9341 as ili9341

from .lcd import LCD
from .tool import Tool
from .zone import Zone
from pistomp.effects.plugin import Plugin
from pistomp.screen import Screen
from pistomp.screen.item import menu
from pistomp.switch.footswitch import Footswitch
from pistomp.util import constants, common
from pistomp.util.color import Color


class SystemSettingsScreen(Screen):

    def __post_init__(self):
        self.row_height = 16
        self.text_color = Color('SOFT_GREEN')
        self.font = ImageFont.truetype("DejaVuSans.ttf", self.row_height)
        self.scroll_vert = True

    def init_items(self):
        self.items = [
            {'item': menu.BackMenuItem(), 'pos': (0, 0)},
            {'item': menu.InputGainMenuItem(), 'pos': (0, 1)},
            {'item': menu.HeadphoneVolumeMenuItem(), 'pos': (0, 2)},
            {'item': menu.SaveMenuItem(), 'pos': (0, 3)},
            {'item': menu.ReloadMenuItem(), 'pos': (0, 4)},
            {'item': menu.RestartSoundMenuItem(), 'pos': (0, 5)},
            {'item': menu.SystemInfoMenuItem(), 'pos': (0, 6)},
            {'item': menu.RebootMenuItem(), 'pos': (0, 7)},
            {'item': menu.SystemInfoMenuItem(), 'pos': (0, 7)},
        ]

    def build(self):
        rows = len(self.items)
        total_height = rows * self.row_height
        images = [Image.new("RGB", (self.width, self.row_height))] * rows
        draws = [ImageDraw.Draw(im) for im in images]
