from enum import Enum


class TopEncoderMode(Enum):
    DEFAULT = 0
    PRESET_SELECT = 1
    PRESET_SELECTED = 2
    PEDALBOARD_SELECT = 3
    PEDALBOARD_SELECTED = 4
    SYSTEM_MENU = 5
    HEADPHONE_VOLUME = 6
    INPUT_GAIN = 7


class BotEncoderMode(Enum):
    DEFAULT = 0
    DEEP_EDIT = 1
    VALUE_EDIT = 2


class UniversalEncoderMode(Enum):
    DEFAULT = 0
    SCROLL = 1
    PRESET_SELECT = 2
    PEDALBOARD_SELECT = 3
    PLUGIN_SELECT = 4
    SYSTEM_MENU = 5
    HEADPHONE_VOLUME = 6
    INPUT_GAIN = 7
    DEEP_EDIT = 8
    VALUE_EDIT = 9
    LOADING = 10


class SelectedType(Enum):
    PEDALBOARD = 0
    PRESET = 1
    PLUGIN = 2
    CONTROLLER = 3
    BYPASS = 4
    WIFI = 5
    SYSTEM = 6


# Replace this with menu objects
class MenuType(Enum):
    MENU_NONE = 0
    MENU_SYSTEM = 1
    MENU_INFO = 2


class SwitchValue(Enum):
    DEFAULT = 0
    PRESSED = 1
    RELEASED = 2
    LONGPRESSED = 3
    CLICKED = 4
    DOUBLECLICKED = 5