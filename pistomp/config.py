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
from os import getcwd
from os.path import join
from typing import List, Optional
import yaml


LOGGER = logging.getLogger(__name__)

DEFAULT_CONFIG_DIR = join(getcwd(), "conf")
DEFAULT_CONFIG_FILE = "default_config.yml"


class Version:
    major: int
    minor: int
    patch: int

    def __init__(self, version: str):
        _pieces = str(version).split(".")
        self.major = int(_pieces[0])
        self.minor = int(_pieces[1]) if len(_pieces) > 1 else 0
        self.patch = int(_pieces[2]) if len(_pieces) > 2 else 0

    def __str__(self):
        return f"{self.major}.{self.minor}.{self.patch}"

    def __repr__(self):
        return str(self)


class FootSwitchConfig:
    debounce_input: int
    gpio_input: Optional[int]
    gpio_output: Optional[int]
    short_action: Optional[str]
    long_action: Optional[str]
    color: Optional[str]
    midi_cc: Optional[str]
    disable: bool

    def __init__(
        self,
        debounce_input: int,
        gpio_input: Optional[int] = None,
        gpio_output: Optional[int] = None,
        short: Optional[str] = None,
        long: Optional[str] = None,
        color: Optional[str] = None,
        midi_cc: Optional[int] = None,
        disable: bool = False,
        **kwargs,
    ):
        self.debounce_input = debounce_input
        self.gpio_input = gpio_input
        self.gpio_output = gpio_output
        self.short_action = short
        self.long_action = long
        self.color = color
        self.midi_cc = midi_cc
        self.disable = disable


class AnalogConfig:
    adc_input: int
    disable: bool
    midi_cc: int
    threshold: Optional[int]
    type: str

    def __init__(
        self,
        adc_input: int,
        midi_cc: int,
        type: str,
        threshold: Optional[int] = None,
        disable: bool = False,
    ):
        self.adc_input = adc_input
        self.midi_cc = midi_cc
        self.type = type
        self.threshold = threshold
        self.disable = disable


class RelayConfig:
    id: int
    set_pin: int
    reset_pin: int

    def __init__(self, id: int, set_pin: int, reset_pin: int):
        self.id = id
        self.set_pin = set_pin
        self.reset_pin = reset_pin


class Config:
    hardware_version: Version
    midi_channel: int
    footswtiches: List[FootSwitchConfig]
    analog_controllers: List[AnalogConfig]
    relays: List[RelayConfig]

    def __init__(
        self,
        hardware_version: str = "2.0.0",
        midi_channel: int = 14,
        footswitches: Optional[List[FootSwitchConfig]] = None,
        analog_controllers: Optional[List[AnalogConfig]] = None,
    ):
        self.hardware_version = Version(hardware_version)
        self.midi_channel = midi_channel
        self.footswitches = (
            [] if footswitches is None else [FootSwitchConfig(**fs) for fs in footswitches]
        )
        self.analog_controllers = (
            [] if analog_controllers is None else [AnalogConfig(**ac) for ac in analog_controllers]
        )
        self.relays = [RelayConfig(0, 12, 16)]

    def dict(self) -> dict:
        d = self.__dict__
        d["footswitches"] = [fs.__dict__ for fs in self.footswitches]
        d["analog_controllers"] = [ac.__dict__ for ac in self.analog_controllers]
        return d

    def save(self):
        with open(join(DEFAULT_CONFIG_DIR, DEFAULT_CONFIG_FILE), "w") as f:
            yaml.dump(self.dict(), f)


def load_cfg(file_name: Optional[str] = None) -> dict:
    # Read the default config file - should only need to read once per session
    if file_name is None:
        file_name = join(DEFAULT_CONFIG_DIR, DEFAULT_CONFIG_FILE)
    with open(file_name, "r") as f:
        return yaml.load(f, Loader=yaml.SafeLoader)


def load(file_name: Optional[str] = None) -> Config:
    if file_name is None:
        file_name = join(DEFAULT_CONFIG_DIR, DEFAULT_CONFIG_FILE)
    with open(file_name, "r") as f:
        conf_data = yaml.load(f, Loader=yaml.FullLoader)
    return Config(
        hardware_version=conf_data.get("hardware-version"),
        midi_channel=conf_data.get("midi-channel"),
        footswitches=conf_data.get("footswitches"),
        analog_controllers=conf_data.get("analog_controllers"),
    )
