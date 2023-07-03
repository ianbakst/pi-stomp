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
from sys import exit
from typing import Optional

from rtmidi.midiutil import open_midioutput

from pistomp import config
from .pistompcore import Pistompcore
from .hardware import Hardware


class Factory:
    __exists: bool = False

    @staticmethod
    def create() -> Optional[Hardware]:
        try:
            midiout, _ = open_midioutput(0)
        except (EOFError, KeyboardInterrupt):
            exit()
        cfg = config.load()
        version = cfg.hardware_version
        if version.major < 2:
            return
        elif (version.major >= 2) and (version.major < 3):
            hw = Pistompcore(cfg, midiout)
            Factory.__exists = True
            return hw
