# MENU_ITEMS = [
#     {constants.NAME: "< Back to main screen", constants.ACTION: self.menu_back},
#     {constants.NAME: "System shutdown", constants.ACTION: self.system_menu_shutdown},
#     {constants.NAME: "System reboot", constants.ACTION: self.system_menu_reboot},
#     {constants.NAME: "System info", constants.ACTION: self.system_info_show},
#     {
#         constants.NAME: "Save current pedalboard",
#         constants.ACTION: self.system_menu_save_current_pb,
#     },
#     {constants.NAME: "Reload pedalboards", constants.ACTION: self.system_menu_reload},
#     {
#         constants.NAME: "Restart sound engine",
#         constants.ACTION: self.system_menu_restart_sound,
#     },
#     {constants.NAME: "Input Gain", constants.ACTION: self.system_menu_input_gain},
#     {constants.NAME: "Headphone Volume", constants.ACTION: self.system_menu_headphone_volume},
# ]

from .back import BackMenuItem
from .headphone import HeadphoneVolumeMenuItem
from .input_gain import InputGainMenuItem
from .reboot import RebootMenuItem
from .reload import ReloadMenuItem
from .restart_sound import RestartSoundMenuItem
from .save import SaveMenuItem
from .shutdown import ShutdownMenuItem
from .system_info import SystemInfoMenuItem


__all__ = [
    'BackMenuItem',
    'HeadphoneVolumeMenuItem',
    'InputGainMenuItem',
    'RebootMenuItem',
    'ReloadMenuItem',
    'RestartSoundMenuItem',
    'SaveMenuItem',
    'ShutdownMenuItem',
    'SystemInfoMenuItem',
]
