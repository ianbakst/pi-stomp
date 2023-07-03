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

from abc import abstractmethod
from copy import deepcopy
import logging
import os

from typing import Optional

import rtmidi

from pistomp.config import Config
from pistomp.analogmidicontrol import AnalogMidiControl
from pistomp.switch.footswitch import Footswitch
from pistomp.util import constants as Token


LOGGER = logging.getLogger(__name__)


class Hardware:
    def __init__(self, cfg: Config, mod, midiout: rtmidi.MidiOut):
        LOGGER.info("Init hardware: " + type(self).__name__)
        self.mod = mod
        self.midiout = midiout
        self.spi = None
        self.test_pass = False
        self.test_sentinel = None

        # From config file(s)
        self.base_cfg = cfg
        self.version = self.base_cfg.hardware_version
        self.cfg = None  # compound cfg (default with user/pedalboard specific cfg overlaid)
        self.midi_channel = 0

        # Standard hardware objects (not required to exist)
        self.relays = []
        self.analog_controls = []
        self.encoders = []
        self.controllers = {}
        self.footswitches = []
        self.encoder_switches = []
        self.debounce_map = None

    def poll(self):
        # This is intended to be called periodically from main working loop to poll the instantiated controls
        for c in self.analog_controls:
            c.refresh()
        for e in self.encoders:
            e.read_rotary()
        for s in self.encoder_switches:
            s.poll()
        for s in self.footswitches:
            s.poll()

    def reinit(self, cfg: Optional[Config] = None):
        # reinit hardware as specified by the new cfg context (after pedalboard change, etc.)
        self.cfg = deepcopy(self.base_cfg)
        self.__init_midi_default()
        self.__init_footswitches(self.cfg)
        if cfg is None:
            return
        self.__init_midi(cfg)
        self.__init_footswitches(cfg)

    @abstractmethod
    def init_analog_controls(self):
        pass

    @abstractmethod
    def init_encoders(self):
        pass

    @abstractmethod
    def init_footswitches(self):
        pass

    @abstractmethod
    def init_relays(self):
        pass

    @abstractmethod
    def test(self):
        pass

    def run_test(self):
        # if test sentinel file exists execute hardware test
        script_dir = os.path.dirname(os.path.realpath(__file__))
        self.test_sentinel = os.path.join(script_dir, ".hardware_tests_passed")
        if not os.path.isfile(self.test_sentinel):
            self.test_pass = False
            self.test()

    def create_footswitches(self, cfg: Config):
        if cfg is None:
            return

        cfg_fs = cfg.footswitches
        if cfg_fs is None:
            return

        midi_channel = self.__get_real_midi_channel(cfg)
        for idx, f in enumerate(cfg_fs):
            if f.disable:
                continue

            di = f.debounce_input
            if self.debounce_map and di in self.debounce_map:
                gpio_input = self.debounce_map[di]
            else:
                gpio_input = f.gpio_input

            gpio_output = f.gpio_output
            midi_cc = f.midi_cc
            id = f.debounce_input

            if gpio_input is None:
                logging.error(
                    "Switch specified without %s or %s" % (Token.DEBOUNCE_INPUT, Token.GPIO_INPUT)
                )
                continue

            fs = Footswitch(
                id if id else idx,
                gpio_input,
                gpio_output,
                midi_cc,
                midi_channel,
                self.midiout,
            )
            self.footswitches.append(fs)

    def create_analog_controls(self, cfg: Config):
        midi_channel = self.__get_real_midi_channel(cfg)
        cfg_c = cfg.analog_controllers
        if cfg_c is None:
            return
        for c in cfg_c:
            if c.disable:
                continue

            adc_input = c.adc_input
            midi_cc = c.midi_cc
            threshold = c.threshold
            control_type = c.type

            if adc_input is None:
                logging.error("Analog control specified without %s" % Token.ADC_INPUT)
                continue
            if midi_cc is None:
                logging.error("Analog control specified without %s" % Token.MIDI_CC)
                continue
            if threshold is None:
                threshold = 16  # Default, 1024 is full scale

            control = AnalogMidiControl(
                self.spi,
                adc_input,
                threshold,
                midi_cc,
                midi_channel,
                self.midiout,
                control_type,
                c,
            )
            self.analog_controls.append(control)
            key = format("%d:%d" % (midi_channel, midi_cc))
            self.controllers[key] = control

    def __get_real_midi_channel(self, cfg: Config):
        chan = 0
        val = cfg.midi_channel
        # LAME bug in Mod detects MIDI channel as one higher than sent (7 sent, seen by mod as 8) so compensate here
        return val - 1 if val > 0 else 0

    def __init_midi_default(self):
        self.__init_midi(self.cfg)

    def __init_midi(self, cfg):
        self.midi_channel = self.__get_real_midi_channel(cfg)
        # TODO could iterate thru all objects here instead of handling in __init_footswitches
        for ac in self.analog_controls:
            if isinstance(ac, AnalogMidiControl):
                ac.set_midi_channel(self.midi_channel)

    def __init_footswitches_default(self):
        for fs in self.footswitches:
            fs.clear_relays()
        self.__init_footswitches(self.cfg)

    def __init_footswitches(self, cfg: Config):
        cfg_fs = cfg.footswitches
        for idx, fs in enumerate(self.footswitches):
            # See if a corresponding cfg entry exists.  if so, override
            f = None
            for f in cfg_fs:
                if f.debounce_input == idx:
                    break
                else:
                    f = None

            if f is not None:
                fs.clear_display_label()
                fs.clear_relays()
                fs.clear_preset()
                for _length in ["short", "long"]:
                    action = getattr(f, f"{_length}_action")
                    if action is None:
                        continue
                    if action == Token.BYPASS:
                        fs.add_relay(self.relay, _length == "short")
                        fs.set_display_label("byps")
                    if action.startswith(Token.PRESET):
                        preset_value = action.split("-")[-1]
                        if preset_value == Token.UP:
                            fs.add_preset(
                                callback=self.mod.preset_incr_and_change,
                                short=(_length == "short"),
                            )
                            fs.set_display_label("Pre+")
                        elif preset_value == Token.DOWN:
                            fs.add_preset(
                                callback=self.mod.preset_decr_and_change,
                                short=(_length == "short"),
                            )
                            fs.set_display_label("Pre-")
                        elif isinstance(preset_value, int):
                            fs.add_preset(
                                callback=self.mod.preset_set_and_change,
                                callback_arg=preset_value,
                                short=(_length == "short"),
                            )
                            fs.set_display_label(str(preset_value))
                    if f.midi_cc is not None:
                        cc = f.midi_cc
                        if cc == Token.NONE:
                            fs.set_midi_CC(None)
                            for k, v in self.controllers.items():
                                if v == fs:
                                    self.controllers.pop(k)
                                    break
                        else:
                            fs.set_midi_channel(self.midi_channel)
                            fs.set_midi_CC(cc)
                            key = format("%d:%d" % (self.midi_channel, fs.midi_CC))
                            self.controllers[
                                key
                            ] = fs  # TODO problem if this creates a new element?
                # LCD attributes
                if f.color is not None:
                    fs.set_lcd_color(f.color)
