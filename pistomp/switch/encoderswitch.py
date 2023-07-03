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
import time
from typing import Optional

from .gpioswitch import GpioSwitch
from pistomp.util.mode import SwitchValue

LOGGER = logging.getLogger(__name__)


class EncoderSwitch(GpioSwitch):
    def __init__(self, gpio):
        super().__init__(gpio, None, None)
        self.last_read = None  # this keeps track of the last value
        self.trigger_count = 0
        self.longpress_state = False
        self.gpio = gpio

    def poll(self) -> Optional[bool]:
        # Grab press event if any
        new_timestamp = None if self.events.empty() else self.events.get_nowait()

        # If we were a already pressed and waiting for a release, drop it, it's easier
        # that way and we should be polling fast enough for this not to matter.
        # Otherwise record it
        self.cur_tstamp = new_timestamp if self.cur_tstamp is None else self.cur_tstamp

        # Are we waiting for release ?
        if self.cur_tstamp is None:
            return

        time_pressed = time.monotonic() - self.cur_tstamp

        # If it's a long press, process as soon as we reach the threshold, otherwise
        # check the GPIO input
        if time_pressed > self.long_press_threshold:
            short = False
        elif GPIO.input(self.fs_pin):
            short = True
        else:
            return
        self.cur_tstamp = None

        LOGGER.debug("Switch %d %s press" % (self.fs_pin, "short" if short else "long"))
        return short
