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
from typing import Optional
from pistomp.util import constants

from .pistompcore import Pistompcore
from .hardware import Hardware


class Factory:
    __exists: bool = False

    @staticmethod
    def create(cfg, handler, midiout) -> Optional[Hardware]:
        version = cfg.get(constants.HARDWARE, {}).get(constants.VERSION)
        if version < 2.0:
            return
        elif (version >= 2.0) and (version < 3.0):
            hw = Pistompcore(cfg, handler, midiout, refresh_callback=handler.update_lcd_fs)
            Factory.__exists = True
            return hw
