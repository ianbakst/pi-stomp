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

# This subclass defines hardware specific to pi-Stomp Core
# 3 Footswitches
# 1 Analog Pot
# 1 Expression Pedal
# 2 Encoders with switches
#
# A new version with different controls should have a new separate subclass
from copy import deepcopy
import logging
from os import getcwd
from typing import Callable, Dict, List, Optional, Tuple

import RPi.GPIO as GPIO
import rtmidi
from rtmidi.midiconstants import CONTROL_CHANGE
import spidev

from pistomp.analogmidicontrol import AnalogMidiControl
from pistomp.config import AnalogConfig, Config, FootSwitchConfig
from pistomp.encoder import Encoder
from pistomp.switch.encoderswitch import EncoderSwitch
from pistomp.switch.footswitch import ActionMessage, Footswitch
from pistomp.relay import Relay
from pistomp.util import constants as Token
from pistomp.util.mode import FootSwitchAction


# Pins (Unless the hardware has been changed, these should not be altered)
TOP_ENC_PIN_D = 17
TOP_ENC_PIN_CLK = 4
TOP_ENC_SWITCH_CHANNEL = 7
ENC_SW_THRESHOLD = 512

# Map of Debounce chip pin (user friendly) to GPIO (code friendly)
DEBOUNCE_MAP = {0: 27, 1: 23, 2: 22, 3: 24, 4: 25}

CWD = getcwd()
LOGGER = logging.getLogger(__name__)


class Pistompcore:
    def __init__(self, cfg: Config, midiout: rtmidi.MidiOut):
        LOGGER.info("Init hardware: " + type(self).__name__)
        self.midiout = midiout
        self.spi = self.init_spi()

        # From config file(s)
        self.hw_cfg = cfg
        self.version = self.hw_cfg.hardware_version
        self.midi_channel = self._get_real_midi_channel(self.hw_cfg)
        self.cfg = None  # compound cfg (default with user/pedalboard specific cfg overlaid)

        # Standard hardware objects (not required to exist)
        self.relays = self.init_relays(cfg)
        self.encoders = self.init_encoders()
        self.encoder_switches = self.init_encoder_switches()
        self.footswitches = self.init_footswitches()
        self.controllers = self.init_analog_controls()
        self.analog_controls = self.controllers.values()
        GPIO.setmode(GPIO.BCM)

    @staticmethod
    def init_spi(max_freq: int = 240000):
        spi = spidev.SpiDev()
        spi.open(0, 1)  # Bus 0, CE1
        # TODO SPI bus is shared by ADC and LCD.  Ideally, they would use the same frequency.
        # MCP3008 ADC has a max of 1MHz (higher makes it loose resolution)
        # Color LCD needs to run at 24Mhz
        # until we can get them on the same, we'll set ADC (the one set here) to be a slower multiple of the LCD
        # self.spi.max_speed_hz = 24000000
        # self.spi.max_speed_hz =  1000000
        spi.max_speed_hz = max_freq
        return spi

    @staticmethod
    def _get_real_midi_channel(cfg: Config):
        return cfg.midi_channel - 1 if cfg.midi_channel > 0 else 0

    @staticmethod
    def init_relays(cfg: Config):
        return {r.id: Relay(r.set_pin, r.reset_pin) for r in cfg.relays}

    @staticmethod
    def init_encoders() -> List[Encoder]:
        return [Encoder(TOP_ENC_PIN_D, TOP_ENC_PIN_CLK)]

    @staticmethod
    def init_encoder_switches() -> List[EncoderSwitch]:
        return [EncoderSwitch(1)]

    def init_footswitches(self) -> List[Optional[Footswitch]]:
        return [self.create_footswitch(f) for f in self.hw_cfg.footswitches]

    def create_footswitch(self, fs_cfg: FootSwitchConfig) -> Optional[Footswitch]:
        gpio_input = DEBOUNCE_MAP.get(fs_cfg.debounce_input, fs_cfg.gpio_input)
        if gpio_input is None:
            LOGGER.error(
                "Switch specified without %s or %s" % (Token.DEBOUNCE_INPUT, Token.GPIO_INPUT)
            )
            return
        return Footswitch(
            fs_cfg.debounce_input,
            gpio_input,
            fs_cfg.midi_cc,
            fs_cfg.short_action,
            fs_cfg.long_action,
            self.midi_channel,
            fs_cfg.gpio_output,
        )

    def init_analog_controls(self) -> Dict[Optional[AnalogMidiControl]]:
        controllers = [self.create_analog_controls(a) for a in self.hw_cfg.analog_controllers]
        return {k: v for c in controllers if c is not None for k, v in c.items()}

    def create_analog_controls(
        self, ac_cfg: AnalogConfig
    ) -> Optional[Dict[str, AnalogMidiControl]]:
        if ac_cfg.disable:
            return
        if ac_cfg.adc_input is None:
            LOGGER.error("Analog control specified without %s" % Token.ADC_INPUT)
            return
        if ac_cfg.midi_cc is None:
            LOGGER.error("Analog control specified without %s" % Token.MIDI_CC)
            return

        control = AnalogMidiControl(
            self.spi,
            ac_cfg.adc_input,
            16 if ac_cfg.threshold is None else ac_cfg.threshold,
            ac_cfg.midi_cc,
            self.midi_channel,
            self.midiout,
            ac_cfg.type,
        )
        return {f"{self.midi_channel}:{ac_cfg.midi_cc}": control}

    def poll(
        self,
        analog_controls_key: str = "analog_controls",
        encoder_key: str = "encoders",
        encoder_switch_key: str = "encoder_switches",
        footswitch_key: str = "footswitches",
    ) -> Dict[str, List[str]]:
        # This is intended to be called periodically from main working loop to poll the instantiated controls
        return {
            analog_controls_key: [c.refresh() for c in self.analog_controls],
            encoder_key: [e.read_rotary() for e in self.encoders],
            encoder_switch_key: [s.poll() for s in self.encoder_switches],
            footswitch_key: [self.poll_footswitch(s) for s in self.footswitches],
        }

    def poll_footswitch(self, fs: Footswitch) -> ActionMessage:
        action = fs.poll()
        if action.action == FootSwitchAction.RELAY:
            action.add_callback(lambda: self.relays[action.message].toggle())
        elif action == FootSwitchAction.MIDI_CC:
            action.add_callback(lambda: self.midiout.send_message(action.message))
        return action


    # def reinit(self, cfg: Optional[Config] = None):
    #     # reinit hardware as specified by the new cfg context (after pedalboard change, etc.)
    #     self.cfg = deepcopy(self.hw_cfg)
    #     self.__init_footswitches(self.cfg)
    #     if cfg is None:
    #         return
    #     self.__init_footswitches(cfg)

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
