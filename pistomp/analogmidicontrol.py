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

from rtmidi.midiconstants import CONTROL_CHANGE

from pistomp.util import common as util
from .analogcontrol import AnalogControl

import logging

LOGGER = logging.getLogger(__name__)


class AnalogMidiControl(AnalogControl):
    def __init__(
        self,
        spi,
        adc_channel,
        tolerance,
        midi_CC,
        midi_channel,
        midiout,
        type,
    ):
        super().__init__(spi, adc_channel, tolerance)
        self.midi_CC = midi_CC
        self.midiout = midiout
        self.midi_channel = midi_channel

        # Parent member overrides
        self.type = type
        self.last_read = 0  # this keeps track of the last potentiometer value
        self.value = None

    def set_midi_channel(self, midi_channel):
        self.midi_channel = midi_channel

    def set_value(self, value):
        self.value = value

    def refresh(self):
        # read the analog pin
        value = self.read_channel()
        if abs(value - self.last_read) > self.tolerance:
            # convert 16bit adc0 (0-65535) trim pot read into 0-100 volume level
            set_volume = util.renormalize(value, 0, 1023, 0, 127)
            cc = [self.midi_channel | CONTROL_CHANGE, self.midi_CC, set_volume]
            LOGGER.debug("AnalogControl Sending CC event %s" % cc)
            self.midiout.send_message(cc)

            # save the potentiometer reading for the next loop
            self.last_read = value
