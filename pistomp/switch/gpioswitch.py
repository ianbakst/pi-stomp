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
from abc import abstractmethod
import json
import logging
import queue
import time

import RPi.GPIO as GPIO

LOGGER = logging.getLogger(__name__)


class GpioSwitch:
    def __init__(self, pin: int, midi_channel: int, midi_CC, long_press_threshold: float = 0.5):
        self._pin = None
        self.pin = pin
        self.midi_channel = midi_channel
        self.midi_CC = midi_CC
        self.minimum = None
        self.maximum = None
        self.parameter = None
        self.hardware_name = None
        self.type = None
        self.cur_tstamp = None
        self.events = queue.Queue()

        # Long press threshold in seconds
        self.long_press_threshold = long_press_threshold

    def __del__(self):
        GPIO.remove_event_detect(self.pin)

    @property
    def pin(self):
        return self._pin

    @pin.setter
    def pin(self, pin: int):
        if self._pin is not None:
            GPIO.remove_event_detect(self._pin)
        self._pin = pin
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.add_event_detect(pin, GPIO.FALLING, callback=self._gpio_down, bouncetime=250)

    def to_json(self):
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)

    @property
    def midi_channel(self):
        return self._midi_channel

    @midi_channel.setter
    def midi_channel(self, value):
        self._midi_channel = value

    @property
    def midi_CC(self):
        return self._midi_CC

    @midi_CC.setter
    def midi_CC(self, value):
        self._midi_CC = value

    def _gpio_down(self):
        # This is run from a separate thread, timestamp pressed and queue an event
        #
        # I considered using a dual edge callback and handle the timestamp here
        # to queue long/short press events, but in practice, I noticed dual edge
        # is rather unreliable with such a long debounce, we often don't get the
        # rising edge callback at all. So let's just timestamp and we'll handle
        # everything from the poller thread
        #
        self.events.put(time.monotonic())

    def poll(self):
        # Grab press event if any
        new_timestamp = None if self.events.empty() else self.events.get_nowait()

        # If we were a already pressed and waiting for a release, drop it, it's easier
        # that way and we should be polling fast enough for this not to matter.
        # Otherwise record it
        self.cur_tstamp = new_timestamp if self.cur_tstamp is None else self.cur_tstamp

        # Are we waiting for release?
        if self.cur_tstamp is None:
            return

        time_pressed = time.monotonic() - self.cur_tstamp

        # If it's a long press, process as soon as we reach the threshold, otherwise
        # check the GPIO input
        if time_pressed > self.long_press_threshold:
            short = False
        elif GPIO.input(self.pin):
            short = True
        else:
            return
        self.cur_tstamp = None

        LOGGER.debug("Switch %d %s press" % (self.pin, "short" if short else "long"))
        self.pressed(short)

    @abstractmethod
    def pressed(self, short: bool):
        pass

    @abstractmethod
    def set_value(self, value):
        pass
