#!/usr/bin/env python3

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
import argparse
import logging
import os
import RPi.GPIO as GPIO
import sys
import time

from rtmidi.midiutil import open_midioutput

from . import mod as Mod
from . import audiocard as ac
from .hardwarefactory import Hardwarefactory


def main(log: str = 'INFO', host: str = 'mod'):
    print("Log level now set to: %s" % logging.getLevelName(log))
    logging.basicConfig(level=log)

    # Current Working Dir
    cwd = os.path.dirname(os.path.realpath(__file__))

    # Audio Card Config - doing this early so audio passes ASAP
    audiocard = ac.Factory().create(cwd)
    audiocard.restore()

    # MIDI initialization
    # Prompts user for MIDI input port, unless a valid port number or name
    # is given as the first argument on the command line.
    # API backend defaults to ALSA on Linux.
    # TODO discover and use the thru port (seems to be 14:0 on my system)
    # shouldn't need to aconnect, just send msgs directly to the thru port
    port = 0  # TODO get this (the Midi Through port) programmatically
    # port = sys.argv[1] if len(sys.argv) > 1 else None
    try:
        midiout, port_name = open_midioutput(port)
    except (EOFError, KeyboardInterrupt):
        sys.exit()

    # Hardware and handler objects
    hw = None
    handler = None

    if args.host == "mod":
        # Create singleton Mod handler
        handler = Mod.Mod(audiocard, cwd)

        # Initialize hardware (Footswitches, Encoders, Analog inputs, etc.)
        hw = Hardwarefactory().create(handler, midiout)
        handler.add_hardware(hw)

        # Load all pedalboard info from the lilv ttl file
        handler.load_pedalboards()

        # Load the current pedalboard as "current"
        current_pedal_board_bundle = handler.get_current_pedalboard_bundle_path()
        if not current_pedal_board_bundle:
            # Apparently, no pedalboard is currently loaded so just change to the default
            handler.pedalboard_change()
        else:
            handler.set_current_pedalboard(handler.pedalboards[current_pedal_board_bundle])

        # Load system info.  This can take a few seconds
        handler.system_info_load()
    logging.info("Entering main loop. Press Control-C to exit.")
    period = 0
    try:
        while True:
            handler.poll_controls()
            time.sleep(
                0.01
            )  # lower to increase responsiveness, but can cause conflict with LCD if too low

            # For less frequent events
            period += 1
            if period > 100:
                handler.poll_modui_changes()
                period = 0

    except KeyboardInterrupt:
        logging.info("keyboard interrupt")
    finally:
        handler.cleanup()
        logging.info("Exit.")
        midiout.close_port()
        if handler.lcd is not None:
            handler.lcd.cleanup()
        GPIO.cleanup()
        del handler
        logging.info("Completed cleanup")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--log",
        "-l",
        nargs="+",
        help="Provide logging level. Example --log debug'",
        default="INFO",
        choices=["debug", "info", "warning", "error", "critical"],
        dest='log',
    )
    parser.add_argument(
        "--host",
        "-h",
        help="Plugin host to use. Example --host mod'",
        default="mod",
        choices=["mod", "generic", "test"],
        dest='host',
    )

    args = parser.parse_args()
    main(args.log, args.host)
