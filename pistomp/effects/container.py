from dataclasses import dataclass
from typing import List, Optional

from .parameter import Parameter
from .pedalboard import Pedalboard
from .plugin import Plugin


@dataclass
class Current:
    pedalboard: Pedalboard
    presets: dict
    preset_index: int
    analog_controllers = dict

    def __init__(self, pedalboard):
        self.pedalboard = pedalboard
        self.presets = {}
        self.preset_index = 0
        self.analog_controllers = {}  # { type: (plugin_name, param_name) }


@dataclass
class Deep:
    plugin: Plugin
    parameters: List[Parameter]
    selected_parameter_index: int
    selected_parameter: Optional[Parameter]
    value: float

    def __init__(self, plugin):
        self.plugin = plugin
        self.parameters = list(plugin.parameters.values()) if plugin is not None else None
        self.selected_parameter_index = 0
        self.selected_parameter = None
        self.value = 0  # TODO shouldn't need this
