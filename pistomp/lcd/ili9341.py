# This file is part of pi-stomp.
#
# pi-stomp is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pi-stomp is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pi-stomp.  If not, see <https://www.gnu.org/licenses/>.
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
from pistomp.switch.footswitch import Footswitch
from pistomp.util import constants, common
from pistomp.util.color import Color

# The code in this file should generally be specific to initializing a specific display and rendering (and refreshing)
# Most draw methods should be implemented in the parent class unless that needs to be overriden for this display
# All __init__ parameters from the lcdbase.py should be specified in this __init__

CWD = os.getcwd()
LOGGER = logging.getLogger(__name__)

ZONE_INFO = [
    ('TOOLS', 18),
    ('TITLE', 36),
    ('ASSIGNMENTS', 26),
    ('PLUGINS1', 30),
    ('PLUGINS2', 30),
    ('PLUGINS3', 34),
    ('FOOTSWITCHES', 66),
]


class ILI9341(LCD):
    def __init__(self):
        # Toolbar
        self.tools = []
        self.imagedir = pkg_resources.resource_filename("pistomp", "static/images")
        self.tool_wifi = None
        self.tool_bypass = None
        self.tool_system = None

        # Content
        self.selected_plugin = None
        self.selected_box = None  # ((x0, y0), (x1, y1), width)

        self.category_color_map = {
            "Delay": Color("MEDIUM_VIOLET_RED"),
            "Distortion": Color("GREEN"),
            "Dynamics": Color("ORANGE_RED"),
            "Filter": Color("PERU"),
            "Generator": Color("INDIGO"),
            "Midiutility": Color("GRAY"),
            "Modulator": Color("CORNFLOWER"),
            "Reverb": Color("BLUE_SKY"),
            "Simulator": Color("SADDLE_BROWN"),
            "Spacial": Color("GRAY"),
            "Spectral": Color("RED"),
            "Utility": Color("GRAY"),
        }

        # Init SPI display
        self.disp = self.init_spi_display()

        # Fonts
        self.title_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 26)
        self.splash_font = ImageFont.truetype("DejaVuSans.ttf", 48)
        self.small_font = ImageFont.truetype("DejaVuSans.ttf", 20)
        self.tiny_font = ImageFont.truetype("DejaVuSans.ttf", 16)

        # Colors
        self.background_color = Color.BLACK
        self.foreground_color = Color.WHITE
        self.highlight_color = Color.YELLOW
        self.plugin_color = Color.LAVENDER
        self.plugin_bypassed_color = Color.GRAY
        self.splash_up_color = Color.SOFT_GREEN
        self.splash_down_color = Color.SOFT_RED

        # Width and height exchanged for 90 degree rotation during render/refresh
        self.height = self.disp.width
        self.top = 0
        self.left = 2

        self.zones = {z.name: z for z in [Zone(i, z[0], z[1]) for i, z in enumerate(ZONE_INFO)]}

        self.zone_y = self.calc_zone_y()
        self.flip = True  # Flip the LCD vertically
        self.calc_zone_y()

        # space between footswitch icons where index is the footswitch count
        #                        0    1    2    3    4    5
        self.footswitch_pitch = [120, 120, 120, 128, 86, 65]

        # Menu (System menu, Parameter edit, etc.)
        self.menu_height = self.height - self.zones['TOOLS'].height - self.zones['TITLE'].height
        self.menu_image_height = self.menu_height * 10  # 10 pages (~80 parameters) enough?
        self.menu_image = Image.new("RGB", (self.disp.width, self.menu_image_height))
        self.menu_draw = ImageDraw.Draw(self.menu_image)
        self.menu_highlight_box_height = 20
        self.menu_highlight_box = ()
        self.menu_y0 = 150
        self.graph_width = 300

        # Element dimensions
        self.plugin_height = 24
        self.plugin_width = 75
        self.plugin_width_medium = 75
        self.plugin_rect_x_pad = 5
        self.plugin_bypass_thickness = 2
        self.plugin_label_length = 7
        self.footswitch_width = 56
        self.footswitch_height = 44
        self.footswitch_ring_width = 7

        self.images = {key: Image.new("RGB", (self.disp.width, zone.height)) for key, zone in self.zones.values()}
        self.draw = {key: ImageDraw.Draw(image) for key, image in self.images.values()}

        self.splash_image = Image.new("RGB", (self.disp.width, 60))
        self.splash_draw = ImageDraw.Draw(self.splash_image)

        self.lock = False
        self.supports_toolbar = True
        self.show_splash()

    @staticmethod
    def init_spi_display():
        spi = board.SPI()
        cs = digitalio.DigitalInOut(board.CE0)
        dc = digitalio.DigitalInOut(board.D6)
        rst = digitalio.DigitalInOut(board.D5)

        # Should agree with the SPI rate used in hardware.py for the ADC
        baud = 24_000_000
        return ili9341.ILI9341(spi, cs=cs, dc=dc, rst=rst, baudrate=baud)

    def clear(self):
        self.disp.fill(0)

    def render(self):
        pass

    def get_plugin_color(self, plugin: Plugin):
        return self.category_color_map.get(plugin.category, Color('GRAY'))

    def calc_zone_y(self) -> dict:
        y_ref = self.height if self.flip else 0
        direction = -1.0 if self.flip else 1.0
        o = 1 if self.flip else 0
        heights = [z.height for z in self.zones.values()]
        zone_y = {
            zone.name: y_ref + direction * sum(heights[:(i + o)])
            for i, zone in enumerate(self.zones.values())
        }
        return zone_y

    def base_draw_title(
        self, draw, font, pedalboard, preset, invert_pb, invert_pre, highlight_only=False
    ):
        pb_size = font.getsize(pedalboard)[0]
        font_height = font.getsize(pedalboard)[1]
        x0 = self.left
        y = self.top  # negative pushes text to top of LCD
        fill = self.highlight_color if highlight_only else self.background
        text_color = self.foreground

        # Pedalboard Name
        if invert_pb:
            draw.rectangle(((x0, y), (pb_size, font_height - 2)), fill, self.highlight_color)
            if highlight_only:
                text_color = self.background
        draw.text((x0, y), pedalboard, text_color, font)

        if preset is not None:
            # delimiter
            delimiter = "/"
            x = x0 + pb_size + 1
            draw.text((x, y), delimiter, self.foreground, font)

            # Preset Name
            pre_size = font.getsize(preset)[0]
            x = x + font.getsize(delimiter)[0]
            x2 = x + pre_size
            y2 = font_height
            if invert_pre:
                draw.rectangle(((x, y), (x2, y2 - 2)), fill, self.highlight_color)
                if highlight_only:
                    text_color = self.background
            draw.text((x, y), preset, text_color, font)

    def base_draw_bound_plugins(self, zone, plugins, footswitches):
        fss = footswitches.copy()
        for p in plugins:
            if p.has_footswitch is False:
                continue
            for c in p.controllers:
                if isinstance(c, Footswitch):
                    fs_id = c.id
                    fss[fs_id] = None
                    if c.parameter.symbol != ":bypass":  # TODO token
                        label = c.parameter.name
                    else:
                        label = self.shorten_name(p.instance_id, self.footswitch_width)
                    color = (
                        self.valid_color(c.lcd_color) if c.lcd_color else self.get_plugin_color(p)
                    )
                    x = self.footswitch_pitch[len(fss)] * fs_id
                    self.draw_plugin(
                        zone, x, 0, label, self.footswitch_width, False, p, True, color
                    )

        # Draw any footswitches which weren't found to be bound to a plugin
        for fs_id in range(len(fss)):
            if fss[fs_id] is None:
                continue
            f = fss[fs_id]
            color = f.lcd_color
            if self.plugin_bypassed_color is not None and not f.enabled:
                color = self.plugin_bypassed_color
            label = "" if f.display_label is None else f.display_label
            x = self.footswitch_pitch[len(fss)] * fs_id
            self.draw_plugin(zone, x, 0, label, self.footswitch_width, False, None, True, color)

    def draw_rectangle(
            self,
            draw,
            xy: Tuple[int, int],
            xy2: Tuple[int, int],
            fill: bool = False,
            color: Optional[Color] = None,
            width: int = 1
    ):
        color = self.foreground_color if color is None else color
        draw.rectangle((xy, xy2), color if fill else None, outline=color, width=width)

    def draw_box(
        self,
        xy: Tuple[int, int],
        xy2: Tuple[int, int],
        zone: Zone,
        text: str = Optional[None],
        fill: bool = False,
        color: Optional[Color] = None,
        width: int = 2,
    ):
        self.draw_rectangle(self.draw[zone], xy, xy2, fill, color, width)
        if text is not None:
            f = self.background if fill else self.foreground
            self.draw[zone].text((xy[0] + 2, xy[1] + 2), text, f, self.small_font)

    def draw_box_outline(self, xy, xy2, zone, color, width=2):
        self.draw[zone].line((xy, (xy[0], xy2[1])), color, width)
        self.draw[zone].line((xy, (xy2[0], xy[1])), color, width)
        self.draw[zone].line((xy2, (xy[0], xy2[1])), color, width)
        self.draw[zone].line((xy2, (xy2[0], xy[1])), color, width)

    def erase_all(self):
        for z in self.zones.values():
            self.erase_zone(z)
        for z in self.zones.values():
            self.refresh_zone(z)

    def erase_zone(self, zone):
        self.images[zone.id].paste(
            self.background_color, (0, 0, self.disp.width, zone.height)
        )

    def shorten_name(self, name, width):
        text = ""
        for x in name.lower().replace("_", "").replace("/", "").replace(" ", ""):
            test = text + x
            test_size = self.small_font.getsize(test)[0]
            if test_size >= width:
                break
            text = test
        return text

    # Parameter Value Edit
    def draw_value_edit(self, plugin_name, parameter, value):
        self.draw_title(plugin_name, None, False, False, False)
        self.draw_value_edit_graph(parameter, value)

    def draw_value_edit_graph(self, parameter, value):
        # TODO super inefficient here redrawing the whole image every time the value changes
        self.draw_title(parameter.name, None, False, False, False)
        self.menu_image.paste(0, (0, 0, self.disp.width, self.menu_image_height))

        y0 = self.menu_y0
        y1 = y0 - 2
        ytext = y0 // 2
        x = 0
        xpitch = 4

        # The current value text
        self.menu_draw.text(
            (0, ytext), "%s" % common.format_float(value), self.foreground, self.title_font
        )

        val = common.renormalize(value, parameter.minimum, parameter.maximum, 0, self.graph_width)
        yref = y1
        while x < self.graph_width:
            self.menu_draw.line(((x + 2, y0), (x + 2, yref)), self.color_plugin, 1)
            if (x < val) and (x % xpitch) == 0:
                self.menu_draw.rectangle(((x, y0), (x + 2, y1)), self.highlight, 2)
                y1 = y1 - 1
            x = x + xpitch
            yref = yref - 1

        self.menu_draw.text(
            (0, self.menu_y0 + 4), "%d" % parameter.minimum, self.foreground, self.small_font
        )
        self.menu_draw.text(
            (self.graph_width - (len(str(parameter.maximum)) * 4), self.menu_y0 + 4),
            "%d" % parameter.maximum,
            self.foreground,
            self.small_font,
        )
        self.refresh_menu()
        self.draw_info_message("Click to exit")

    def update_wifi(self, wifi_status):
        if not self.supports_toolbar:
            return
        if wifi_status.get("hotspot_active"):
            img = "wifi_orange.png"
        elif wifi_status.get("wifi_connected"):
            img = "wifi_silver.png"
        else:
            img = "wifi_gray.png"
        path = os.path.join(self.imagedir, img)
        self.change_tool_img(self.tool_wifi, path)

    def update_bypass(self, bypass):
        if not self.supports_toolbar:
            return
        img = "power_green.png" if bypass else "power_gray.png"
        path = os.path.join(self.imagedir, img)
        self.change_tool_img(self.tool_bypass, path)

    def change_tool_img(self, tool, img_path):
        if self.supports_toolbar:
            tool.update_img(img_path)
            self.images[self.zones['TOOLS'].id].paste(tool.image, (tool.x, tool.y))
            self.refresh_zone(self.zones['TOOLS'])

    def clear_select(self):
        if self.selected_box:
            self.draw_box_outline(
                self.selected_box[0],
                self.selected_box[1],
                self.zones['TOOLS'],
                color=self.background_color,
                width=self.selected_box[2],
            )
            self.refresh_zone(self.zones['TOOLS'])
            self.selected_box = None

    def draw_title(self, pedalboard, preset, invert_pb, invert_pre, highlight_only=False):
        zone = self.zones['TITLE']
        self.erase_zone(
            zone
        )  # TODO to avoid redraw of entire zone, could we just redraw what changed?
        self.base_draw_title(
            self.draw[zone],
            self.title_font,
            pedalboard,
            preset,
            invert_pb,
            invert_pre,
            highlight_only,
        )
        self.refresh_zone(zone)

    # Zone 1 - Analog Assignments (Tweak, Expression Pedal, etc.)
    def draw_knob(self, text, x, color="gray"):
        zone = self.zones['ASSIGNMENTS']
        self.draw[zone].ellipse(((x, 3), (x + 14, 17)), self.background, color, 2)
        self.draw[zone].line(((x + 12, 5), (x + 7, 10)), color, 2)
        self.draw[zone].text((x + 19, 1), text, self.foreground, self.tiny_font)

    def draw_pedal(self, text, x, color="gray"):
        zone = self.zones['ASSIGNMENTS']
        self.draw[zone].line(((x, 14), (x + 13, 4)), color, 2)
        self.draw[zone].line(((x, 14), (x + 14, 14)), color, 4)
        self.draw[zone].text((x + 19, 1), text, self.foreground, self.tiny_font)

    def draw_analog_assignments(self, controllers):
        zone = self.zones['ASSIGNMENTS']
        self.erase_zone(zone)

        # spacing and scaling of text
        width_per_control = self.disp.width
        text_per_control = self.disp.width
        num = len(controllers)
        if num > 0:
            width_per_control = int(round(self.disp.width / num))
            text_per_control = width_per_control - 16  # minus width of control icon

        x = 0
        for k, v in controllers.items():
            control_type = v.get(constants.TYPE)
            color = v.get(constants.COLOR)
            if color is None:
                # color not specified for control in config file
                category = v.get(constants.CATEGORY)
                color = self.category_color_map.get(category, "Silver")
            name = k.split(":")[1]
            n = self.shorten_name(name, text_per_control)
            if control_type == constants.KNOB:
                self.draw_knob(n, x, color)
            if control_type == constants.EXPRESSION:
                self.draw_pedal(n, x, color)
            x += width_per_control

        self.refresh_zone(zone)

    def draw_info_message(self, text):
        zone = self.zones['TOOLS']
        self.erase_zone(zone)
        self.draw[zone].text((0, 0), text, self.foreground, self.tiny_font)
        self.refresh_zone(zone)

    # Plugins
    def draw_plugin_select(self, plugin=None):
        width = 2
        # First unselect currently selected
        if self.selected_plugin:
            x0 = self.selected_plugin.lcd_xyz[0][0] - 3
            y0 = self.selected_plugin.lcd_xyz[0][1] - 3
            x1 = self.selected_plugin.lcd_xyz[1][0] + 3
            y1 = self.selected_plugin.lcd_xyz[1][1] + 3
            c = (
                self.background
            )  # if self.selected_plugin.has_footswitch else self.get_plugin_color(self.selected_plugin)
            self.draw_box_outline(
                (x0, y0), (x1, y1), self.selected_plugin.lcd_xyz[2], color=c, width=width
            )
            self.refresh_zone(self.selected_plugin.lcd_xyz[2])

        if plugin is not None:
            # Highlight new selection
            x0 = plugin.lcd_xyz[0][0] - 3
            y0 = plugin.lcd_xyz[0][1] - 3
            x1 = plugin.lcd_xyz[1][0] + 3
            y1 = plugin.lcd_xyz[1][1] + 3
            self.draw_box_outline(
                (x0, y0), (x1, y1), plugin.lcd_xyz[2], color=self.highlight, width=width
            )
            self.refresh_zone(plugin.lcd_xyz[2])
            self.selected_plugin = plugin

    def draw_bound_plugins(self, plugins, footswitches):
        zone = self.zones['FOOTSWITCHES']
        self.erase_zone(
            zone
        )  # necessary when changing pedalboards with different switch assignments
        self.base_draw_bound_plugins(zone, plugins, footswitches)
        self.refresh_zone(zone)

    def draw_plugins(self, plugins):
        y = self.top + 3
        x = self.left
        xwrap = self.disp.width - self.plugin_width  # scroll if exceeds this width
        ymax = 64  # Maximum y for plugin LCD zone
        zone = self.zones['PLUGINS1']
        for z_name in ['PLUGINS1', 'PLUGINS2', 'PLUGINS3']:
            self.erase_zone(self.zones[z_name])

        count = 0
        for p in plugins:
            if not p.has_footswitch:
                count = count + 1
        width = self.plugin_width_medium if count <= 8 else self.plugin_width

        count = 0
        eol = False
        for p in plugins:
            if p.has_footswitch:
                continue
            label = p.instance_id.replace("/", "")[: self.plugin_label_length]
            label = label.replace("_", "")
            count += 1
            if count > 4:
                eol = True
                count = 0
            x = self.draw_plugin(zone, x, y, label, width, eol, p)
            eol = False
            x = x + self.plugin_rect_x_pad
            if x > xwrap:
                zone += 1
                x = self.left
                if y >= ymax:
                    break  # Only display 2 rows, huge pedalboards won't fully render  # TODO make sure this works
        self.refresh_plugins()

    def draw_plugin(self, zone, x, y, text, width, eol, plugin, is_footswitch=False, color=0):
        text = self.shorten_name(text, width)

        y2 = y + (self.footswitch_height if is_footswitch else self.plugin_height)
        x2 = x + width
        if eol:
            x2 = x2 - 1
        xy1 = (x, y)
        xy2 = (x2, y2)

        if is_footswitch:
            if plugin:
                plugin.lcd_xyz = (xy1, xy2, zone)
            c = (
                self.color_plugin_bypassed
                if plugin is not None and plugin.is_bypassed()
                else color
            )
            self.draw_footswitch(xy1, xy2, zone, text, c)
        elif plugin:
            plugin.lcd_xyz = (xy1, xy2, zone)
            self.draw_box(
                xy1,
                xy2,
                zone,
                text,
                is_footswitch,
                not plugin.is_bypassed(),
                self.category_color_map.get(plugin.category),
            )

        return x2

    def refresh_plugins(self):
        # TODO could be smarter here and only refresh the affected zone
        for z_name in ['PLUGINS1', 'PLUGINS2', 'PLUGINS3']:
            self.refresh_zone(self.zones[z_name])

    def wait_lock(self, period, maximum):
        # wait for max number of periods (in seconds)
        count = 0
        while self.lock and count < maximum:
            time.sleep(period)
            count += 1

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

    def refresh_zone(self, zone):
        self.render_image(self.images[zone.id], self.zone_y[zone_idx])

    def refresh_menu(self, highlight_range=None, highlight_offset=0, scroll_offset=0):
        if highlight_range:
            highlight_width = 2
            x = 0
            y = 0
            y_draw = y + highlight_offset
            if y_draw < self.menu_image_height:
                xy = (x, y_draw)
                xy2 = (x + self.disp.width, y_draw + self.menu_highlight_box_height)
                if self.menu_highlight_box:
                    self.draw_just_a_box(
                        self.menu_draw,
                        self.menu_highlight_box[0],
                        self.menu_highlight_box[1],
                        False,
                        self.background,
                        highlight_width,
                    )

                self.draw_just_a_box(
                    self.menu_draw, xy, xy2, False, self.highlight, highlight_width
                )
                self.menu_highlight_box = (xy, xy2)

        # render_image is a windowed subset of menu_image which contains the full menu content which may be
        # too long to be displayed.  Use transform to "scroll" that window of content.
        render_image = self.menu_image.transform(
            (self.disp.width, self.menu_height),
            Image.EXTENT,
            (0, scroll_offset, self.disp.width, self.menu_height + scroll_offset),
        )
        self.render_image(render_image, 0)

    # Menu Screens (uses deep_edit image and draw objects)
    def menu_show(self, page_title: str, menu_items: dict):
        self.menu_image.paste(self.background_color, (0, 0, self.disp.width, self.menu_image_height))

        # Title (plugin name)
        self.draw_title(page_title, "", False, False, False)
        self.draw_info_message("")

        # Menu Items
        idx = 0
        x = 0
        y = 0
        menu_list = list(sorted(menu_items))
        for i in menu_list:
            if idx == 0:
                self.menu_draw.text(
                    (x, y), "%s" % menu_items[i][constants.NAME], self.foreground, self.small_font
                )
                x = 8  # indent after first element (back button)
            else:
                self.menu_draw.text(
                    (x, y),
                    "%s %s" % (i, menu_items[i][constants.NAME]),
                    self.foreground,
                    self.small_font,
                )
            y += self.menu_highlight_box_height
            idx += 1
        self.refresh_menu()

    def menu_highlight(self, index):
        scroll_idx = 0
        highlight = (index * 10, index * 10 + 8)
        num_visible = int(round(self.menu_height / self.menu_highlight_box_height)) - 1
        if index > num_visible:
            scroll_idx = index - num_visible
        self.refresh_menu(
            highlight,
            index * self.menu_highlight_box_height,
            scroll_idx * self.menu_highlight_box_height,
        )

    def draw_footswitch(self, xy1, xy2, zone, text, color):
        # Many fudge factors here to make the footswitch icon smaller than the highlight bounding box
        # TODO These aren't scalable to other LCD's

        # halo
        hx1 = xy1[0] + 2
        hy1 = xy1[1] + 10
        hx2 = xy2[0] - 2
        hy2 = xy2[1] - 2
        self.draw[zone].ellipse(
            ((hx1, hy1), (hx2, hy2)), fill=None, outline=color, width=self.footswitch_ring_width
        )

        # cap bottom
        fx1 = xy1[0] + 10
        fy1 = xy2[1] - 34
        fx2 = xy2[0] - 10
        fy2 = fy1 + 16
        self.draw[zone].ellipse(
            ((fx1, fy1), (fx2, fy2)), fill=self.background, outline="gray", width=2
        )

        # cap top
        fy1 -= 6
        fy2 -= 6
        self.draw[zone].ellipse(
            ((fx1, fy1), (fx2, fy2)), fill=self.background, outline="gray", width=2
        )

        # label
        self.draw[zone].text((xy1[0], xy2[1]), text, self.foreground, self.small_font)

    def draw_tools(self, wifi_type, bypass_type, system_type):
        if not self.supports_toolbar:
            return
        self.erase_zone(self.zones['TOOLS'])
        tools = []
        if self.tool_wifi is None:
            self.tool_wifi = Tool(wifi_type, 240, 1, os.path.join(self.imagedir, "wifi_gray.png"))
            tools.append(self.tool_wifi)
        if self.tool_bypass is None:
            self.tool_bypass = Tool(
                bypass_type, 270, 1, os.path.join(self.imagedir, "power_gray.png")
            )
            tools.append(self.tool_bypass)
        if self.tool_system is None:
            self.tool_system = Tool(
                system_type, 296, 1, os.path.join(self.imagedir, "wrench_silver.png")
            )
            tools.append(self.tool_system)
        if len(tools) > 0:
            self.tools = tools
        for t in self.tools:
            self.images[self.zones['TOOLS'].id].paste(t.image, (t.x, t.y))
        self.refresh_zone(self.zones['TOOLS'])

    def draw_tool_select(self, tool_type):
        if not self.supports_toolbar:
            return
        for t in self.tools:
            if t.tool_type == tool_type:
                xy0 = (t.x - 4, t.y - 1)
                xy1 = (t.x + 17, t.y + 16)
                width = 1
                self.draw_box_outline(xy0, xy1, self.zones['TOOLS'], color=self.highlight, width=width)
                self.refresh_zone(self.zones['TOOLS'])
                self.selected_box = (xy0, xy1, 1)
                break

    def show_splash(self, boot=True):
        self.clear()
        color = self.splash_up_color if boot is True else self.splash_down_color
        self.splash_draw.text((50, self.top), "pi Stomp!", font=self.splash_font, fill=color)
        self.render_image(self.splash_image, 90, 0)
