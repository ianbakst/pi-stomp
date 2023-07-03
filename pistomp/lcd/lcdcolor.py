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

from PIL import ImageColor

from .lcd import LCD
from pistomp.switch.footswitch import Footswitch
from pistomp.util import constants
from pistomp.util import common as util

LOGGER = logging.getLogger(__name__)


class LCDColor(LCD):
    def __init__(self):
        self.title_font = None
        self.splash_font = None
        self.small_font = None

        # Colors
        self.background = None
        self.foreground = None
        self.highlight = None
        self.color_plugin = None
        self.color_plugin_bypassed = None
        self.category_color_map = {}

        # Dimensions
        self.width = None
        self.height = None
        self.top = None
        self.left = None
        self.zone_height = None
        self.zone_y = None
        self.flip = False
        self.footswitch_width = None
        self.footswitch_height = None
        self.plugin_height = None
        self.plugin_width = None
        self.plugin_width_medium = None
        self.plugin_rect_x_pad = None
        self.plugin_bypass_thickness = None
        self.plugin_label_length = None
        self.footswitch_width = None
        self.footswitch_ring_width = None
        self.graph_width = None
        self.menu_y0 = None

        # Toolbar
        self.supports_toolbar = None
        self.tools = []
        self.imagedir = pkg_resources.resource_filename("pistomp", "static/images")
        self.tool_wifi = None
        self.tool_bypass = None
        self.tool_system = None

        # Content
        self.zones = None
        self.zone_height = None
        self.images = None
        self.draw = None
        self.selected_plugin = None
        self.selected_box = None  # ((x0, y0), (x1, y1), width)

        self.category_color_map = {
            "Delay": "MediumVioletRed",
            "Distortion": "Lime",
            "Dynamics": "OrangeRed",
            "Filter": (205, 133, 40),
            "Generator": "Indigo",
            "Midiutility": "Gray",
            "Modulator": (50, 50, 255),
            "Reverb": (20, 160, 255),
            "Simulator": "SaddleBrown",
            "Spacial": "Gray",
            "Spectral": "Red",
            "Utility": "Gray",
        }

    def check_vars_set(self):
        known_exceptions = [
            "selected_plugin",
            "selected_box",
            "tool_wifi",
            "tool_bypass",
            "tool_system",
        ]
        for v in self.__dict__:
            if getattr(self, v) is None:
                if v not in known_exceptions:
                    LOGGER.error("%s class doesn't set variable: %s" % (self, v))

    # Try to map color to a valid displayable color, if not use foreground
    def valid_color(self, color):
        if color is None:
            return self.foreground
        try:
            return ImageColor.getrgb(color)
        except ValueError:
            LOGGER.error("Cannot convert color name: %s" % color)
            return self.foreground

    # Get the color assigned to the plugin category
    def get_category_color(self, category):
        color = "Silver"
        if category:
            c = util.DICT_GET(self.category_color_map, category)
            if c:
                color = c if isinstance(c, tuple) else self.valid_color(c)
        return color

    def get_plugin_color(self, plugin):
        if plugin.category:
            return self.get_category_color(plugin.category)
        return "Silver"

    # Convert zone height values to absolute y values considering the flip setting
    def calc_zone_y(self):
        y_offset = 0 if not self.flip else self.height
        for i in range(self.zones):
            if self.flip:
                y_offset -= self.zone_height[i]
                if y_offset < 0:
                    break
            else:
                if i != 0:
                    y_offset += self.zone_height[i - 1]
                    if y_offset > self.height:
                        break
            self.zone_y[i] = y_offset

    def base_draw_title(
        self, draw, font, pedalboard, preset, invert_pb, invert_pre, highlight_only=False
    ):
        pb_size = font.getsize(pedalboard)[0]
        font_height = font.getsize(pedalboard)[1]
        x0 = self.left
        y = self.top  # negative pushes text to top of LCD
        highlight_color = self.highlight
        fill = highlight_color if highlight_only else self.background
        text_color = self.foreground

        # Pedalboard Name
        if invert_pb:
            draw.rectangle(((x0, y), (pb_size, font_height - 2)), fill, highlight_color)
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
                draw.rectangle(((x, y), (x2, y2 - 2)), fill, highlight_color)
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
            color = self.valid_color(f.lcd_color)
            if self.color_plugin_bypassed is not None and not f.enabled:
                color = self.color_plugin_bypassed
            label = "" if f.display_label is None else f.display_label
            x = self.footswitch_pitch[len(fss)] * fs_id
            self.draw_plugin(zone, x, 0, label, self.footswitch_width, False, None, True, color)

    def draw_just_a_box(self, draw, xy, xy2, fill=False, color=None, width=1):
        if color is None:
            color = self.foreground
        f = color if fill else None
        draw.rectangle((xy, xy2), f, outline=color, width=width)

    def draw_box(
        self, xy, xy2, zone, text=None, round_bottom_corners=False, fill=False, color=None, width=2
    ):
        self.draw_just_a_box(self.draw[zone], xy, xy2, fill, color, width)
        # self.draw[zone].point(xy, self.background)  # Round the top corners
        # self.draw[zone].point((xy2[0],xy[1]), self.background)
        # if round_bottom_corners:
        #    self.draw[zone].point((xy[0],xy2[1]))
        #    self.draw[zone].point((xy2[0],xy2[1]))
        if text:
            f = self.background if fill else self.foreground
            self.draw[zone].text((xy[0] + 2, xy[1] + 2), text, f, self.small_font)

    def draw_box_outline(self, xy, xy2, zone, color, width=2):
        self.draw[zone].line((xy, (xy[0], xy2[1])), color, width)
        self.draw[zone].line((xy, (xy2[0], xy[1])), color, width)
        self.draw[zone].line((xy2, (xy[0], xy2[1])), color, width)
        self.draw[zone].line((xy2, (xy2[0], xy[1])), color, width)

    def erase_all(self):
        for z in range(self.zones):
            self.erase_zone(z)
        for z in range(self.zones):
            self.refresh_zone(z)

    def erase_zone(self, zone_idx):
        self.images[zone_idx].paste(
            self.background, (0, 0, self.width, self.zone_height[zone_idx])
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

    # Menu Screens (uses deep_edit image and draw objects)
    def menu_show(self, page_title, menu_items):
        pass

    def menu_highlight(self, index):
        pass

    # Parameter Value Edit
    def draw_value_edit(self, plugin_name, parameter, value):
        self.draw_title(plugin_name, None, False, False, False)
        self.draw_value_edit_graph(parameter, value)

    def draw_value_edit_graph(self, parameter, value):
        # TODO super inefficient here redrawing the whole image every time the value changes
        self.draw_title(parameter.name, None, False, False, False)
        self.menu_image.paste(0, (0, 0, self.width, self.menu_image_height))

        y0 = self.menu_y0
        y1 = y0 - 2
        ytext = y0 // 2
        x = 0
        xpitch = 4

        # The current value text
        self.menu_draw.text(
            (0, ytext), "%s" % util.format_float(value), self.foreground, self.title_font
        )

        val = util.renormalize(value, parameter.minimum, parameter.maximum, 0, self.graph_width)
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
        if util.DICT_GET(wifi_status, "hotspot_active"):
            img = "wifi_orange.png"
        elif util.DICT_GET(wifi_status, "wifi_connected"):
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
        if not self.supports_toolbar:
            return
        tool.update_img(img_path)
        self.images[self.ZONE_TOOLS].paste(tool.image, (tool.x, tool.y))
        self.refresh_zone(self.ZONE_TOOLS)

    def clear_select(self):
        if self.selected_box:
            self.draw_box_outline(
                self.selected_box[0],
                self.selected_box[1],
                self.ZONE_TOOLS,
                color=self.background,
                width=self.selected_box[2],
            )
            self.refresh_zone(self.ZONE_TOOLS)
            self.selected_box = None

    def draw_title(self, pedalboard, preset, invert_pb, invert_pre, highlight_only=False):
        zone = self.ZONE_TITLE
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
        zone = self.ZONE_ASSIGNMENTS
        self.draw[zone].ellipse(((x, 3), (x + 14, 17)), self.background, color, 2)
        self.draw[zone].line(((x + 12, 5), (x + 7, 10)), color, 2)
        self.draw[zone].text((x + 19, 1), text, self.foreground, self.tiny_font)

    def draw_pedal(self, text, x, color="gray"):
        zone = self.ZONE_ASSIGNMENTS
        self.draw[zone].line(((x, 14), (x + 13, 4)), color, 2)
        self.draw[zone].line(((x, 14), (x + 14, 14)), color, 4)
        self.draw[zone].text((x + 19, 1), text, self.foreground, self.tiny_font)

    def draw_analog_assignments(self, controllers):
        zone = self.ZONE_ASSIGNMENTS
        self.erase_zone(zone)

        # spacing and scaling of text
        width_per_control = self.width
        text_per_control = self.width
        num = len(controllers)
        if num > 0:
            width_per_control = int(round(self.width / num))
            text_per_control = width_per_control - 16  # minus width of control icon

        x = 0
        for k, v in controllers.items():
            control_type = util.DICT_GET(v, constants.TYPE)
            color = util.DICT_GET(v, constants.COLOR)
            if color is None:
                # color not specified for control in config file
                category = util.DICT_GET(v, constants.CATEGORY)
                color = self.get_category_color(category)
            name = k.split(":")[1]
            n = self.shorten_name(name, text_per_control)
            if control_type == constants.KNOB:
                self.draw_knob(n, x, color)
            if control_type == constants.EXPRESSION:
                self.draw_pedal(n, x, color)
            x += width_per_control

        self.refresh_zone(zone)

    def draw_info_message(self, text):
        zone = self.ZONE_TOOLS
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
        zone = self.ZONE_FOOTSWITCHES
        self.erase_zone(
            zone
        )  # necessary when changing pedalboards with different switch assignments
        self.base_draw_bound_plugins(zone, plugins, footswitches)
        self.refresh_zone(zone)

    def draw_footswitch(self, xy1, xy2, zone, text, color):
        # implement in display class
        pass

    def draw_plugins(self, plugins):
        y = self.top + 3
        x = self.left
        xwrap = self.width - self.plugin_width  # scroll if exceeds this width
        ymax = 64  # Maximum y for plugin LCD zone
        zone = self.ZONE_PLUGINS1
        self.erase_zone(self.ZONE_PLUGINS1)
        self.erase_zone(self.ZONE_PLUGINS2)
        self.erase_zone(self.ZONE_PLUGINS3)

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
                self.get_plugin_color(plugin),
            )

        return x2
