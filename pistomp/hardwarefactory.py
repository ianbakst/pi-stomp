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

from .util import constants as Token
from .util import config

# import pistomp.pistomp as Pistomp
from .pistompcore import Pistompcore


class HardwareExistsError(Exception):
    pass


class Hardwarefactory:
    __exists = False

    def __init__(self):
        self.cfg = config.load_default_cfg()

    def create(self, handler, midiout):
        if Hardwarefactory.__exists:
            raise HardwareExistsError
        ps = Pistompcore(
            self.cfg, handler, midiout, refresh_callback=handler.update_lcd_fs
        )
        Hardwarefactory.__exists = True
        return ps
        # version = self.cfg[Token.HARDWARE][Token.VERSION]
        # if version is None or (version < 2.0):
        #     return Pistomp.Pistomp(
        #         self.cfg, handler, midiout, refresh_callback=handler.update_lcd_fs
        #     )
        # elif (version >= 2.0) and (version < 3.0):
        #     return Pistompcore.Pistompcore(
        #         self.cfg, handler, midiout, refresh_callback=handler.update_lcd_fs
        #     )
