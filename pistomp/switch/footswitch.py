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
from typing import Callable, Optional

import RPi.GPIO as GPIO
from rtmidi.midiconstants import CONTROL_CHANGE

from .gpioswitch import GpioSwitch
from pistomp.util.color import Color
from pistomp.util.mode import FootSwitchAction


LOGGER = logging.getLogger(__name__)


class ActionMessage:
    id: int
    action: FootSwitchAction
    value: Optional[int]
    callback: Optional[Callable]

    def __init__(self, id: int, action: FootSwitchAction, value, callback: Optional[Callable] = None):
        self.id = id
        self.action = action
        self.value = value
        self.callback = callback

    def add_callback(self, callback: Callable):
        old_callback = self.callback

        def new_callback():
            callback()
            if old_callback is not None:
                old_callback()
        self.callback = new_callback


class Footswitch(GpioSwitch):
    id: int
    top_disp_label: Optional[str]
    bot_disp_label: Optional[str]
    _enabled: bool
    _led_pin: Optional[int]
    led_short_action: bool
    short_action: ActionMessage
    long_action: ActionMessage
    _lcd_color_short = Optional[Color]
    _lcd_color_long = Optional[Color]

    def __init__(
        self,
        id: int,
        fs_pin: int,
        midi_CC: int,
        short_action: str,
        long_action: str,
        midi_channel: int = 0,
        led_pin: Optional[int] = None,
    ):
        super().__init__(fs_pin, midi_channel, midi_CC)
        self.id = id
        self._top_display_label = None
        self._bot_display_label = None
        self._enabled = False
        self.led_pin = led_pin
        self.led_short_action = True
        self.lcd_color_short = None
        self.lcd_color_long = None
        self.short_action = short_action
        self.long_action = long_action

    @property
    def short_action(self):
        return self._short_action

    @short_action.setter
    def short_action(self, action):
        self._short_action = self.generate_action(action)

    @property
    def long_action(self):
        return self._long_action

    @long_action.setter
    def long_action(self, action):
        self._long_action = self.generate_action(action)

    def generate_action(self, action):
        fsa = FootSwitchAction(action)
        if fsa == FootSwitchAction.RELAY:
            message = 0
        elif fsa == FootSwitchAction.MIDI_CC:
            message = [self.midi_channel | CONTROL_CHANGE, self.midi_CC, 127 if self.enabled else 0]
        else:
            message = None
        return ActionMessage(self.id, fsa, message)

    @property
    def led_pin(self):
        return self._led_pin

    @led_pin.setter
    def led_pin(self, value):
        self._led_pin = value
        if self._led_pin is not None:
            GPIO.setup(value, GPIO.OUT)
            self.enabled = False

    @property
    def enabled(self):
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool):
        self._enabled = value
        if self.led_pin is not None:
            GPIO.output(self.led_pin, self._enabled)

    def toggle(self):
        self.enabled = not self.enabled

    def set_value(self, value):
        self.enabled = value < 1

    @property
    def lcd_color_short(self):
        return self._lcd_color_short

    @lcd_color_short.setter
    def lcd_color_short(self, color: Optional[str]):
        self._lcd_color_short = Color('WHITE' if color is None else color)

    @property
    def lcd_color_long(self):
        return self._lcd_color_long

    @lcd_color_long.setter
    def lcd_color_long(self, color: Optional[str]):
        self._lcd_color_long = Color('WHITE' if color is None else color)

    def press_callback(self, short: bool):
        if self.led_short_action == short:
            LOGGER.debug(f'Footswitch {self.id} Toggle LED')
            self.toggle()

    def pressed(self, short: bool = True) -> ActionMessage:
        # return action for processing
        action = self.short_action if short else self.long_action
        action.callback = lambda: self.press_callback(short)
        return action

    def otherwise(self, short, new_enabled):
        # Update Relay (if relay is associated with this footswitch)
        if len(self.relay_list) > 0:
            if short == self.relay_action_short:
                # Pin kept low (long press)
                # toggle the relay and LED, exit this method

                for r in self.relay_list:
                    if self.enabled:
                        r.enable()
                    else:
                        r.disable()
                # True means this is a bypass change only
                return

        # If mapped to preset change
        if self.preset_callback is not None:
            if short == self.preset_action_short:
                # Change the preset and exit this method. Don't flip "enabled" since
                # there is no "toggle" action associated with a preset
                if self.preset_callback_arg is None:
                    self.preset_callback()
                else:
                    self.preset_callback(self.preset_callback_arg)
                return

        # Send midi
        if self.midi_CC is not None:
            self.enabled = new_enabled
            # Update LED
            self._set_led(self.enabled)
            cc = [self.midi_channel | CONTROL_CHANGE, self.midi_CC, 127 if self.enabled else 0]
            logging.debug("Sending CC event: %d %s" % (self.midi_CC, self.fs_pin))
            self.midiout.send_message(cc)

        # Update plugin parameter if any
        if self.parameter is not None:
            self.parameter.value = not self.enabled  # TODO assumes mapped parameter is :bypass

        # Update LCD

    def set_display_label(self, label):
        self.display_label = label

    def clear_display_label(self):
        self.display_label = None

    def add_relay(self, relay, action: bool):
        self.relay_list.append(relay)
        self.relay_action_short = action
        self.set_value(not relay.init_state())

    def clear_relays(self):
        self.relay_list.clear()

    def add_preset(self, callback, callback_arg=None, short: bool = True):
        self.preset_callback = callback
        self.preset_callback_arg = callback_arg
        self.preset_action_short = short

    def clear_preset(self):
        self.preset_callback = None
