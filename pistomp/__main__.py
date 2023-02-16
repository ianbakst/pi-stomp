import argparse
import logging
import sys
import time

import RPi.GPIO as GPIO
from rtmidi.midiutil import open_midioutput

from pistomp import audiocard as ac
from pistomp import hardware, host

LOGGER = logging.getLogger(__name__)


def loop(log: str, host_type: str, short_poll: float = 0.01, long_poll: int = 100) -> None:
    if log is not None:
        LOGGER.setLevel(level=log.upper())
        LOGGER.critical(f"Log level now set to: {log.upper()}")

    # Audio Card Config - doing this early so audio passes ASAP
    audiocard = ac.Factory().create()
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
    handler = None

    if host_type == "mod":

        # Create singleton Mod handler
        handler = host.Factory().create(audiocard)

        # Initialize hardware (Footswitches, Encoders, Analog inputs, etc.)
        hw = hardware.Factory().create(handler, midiout)
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
    #
    # elif args.host[0] == "generic":
    #     # No specific plugin host specified, so use a generic handler
    #     # Encoders and LCD not mapped without specific purpose
    #     # Just initialize the control hardware (footswitches, analog controls, etc.) for use as MIDI controls
    #     handler = Generichost.Generichost(homedir=cwd)
    #     factory = Hardwarefactory.Hardwarefactory()
    #     hw = factory.create(handler, midiout)
    #     handler.add_hardware(hw)
    #
    # elif args.host[0] == "test":
    #     handler = Testhost.Testhost(audiocard, homedir=cwd)
    #     try:
    #         factory = Hardwarefactory.Hardwarefactory()
    #         hw = factory.create(handler, midiout)
    #         handler.add_hardware(hw)
    #     except:
    #         handler.cleanup()
    #         raise

    LOGGER.info("Entering main loop. Press Control-C to exit.")
    it = 0
    try:
        while True:
            handler.poll_controls()
            time.sleep(
                short_poll
            )  # lower to increase responsiveness, but can cause conflict with LCD if too low

            # For less frequent events
            it += 1
            if it > long_poll:
                handler.poll_modui_changes()
                it = 0

    except KeyboardInterrupt:
        LOGGER.info("keyboard interrupt")
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
        help="Provide logging level. Example --log debug'",
        default="INFO",
        choices=["debug", "info", "warning", "error", "critical"],
        dest="log",
    )
    parser.add_argument(
        "--host",
        "-H",
        help="Plugin host to use. Example --host mod'",
        default="mod",
        choices=["mod", "generic", "test"],
        dest="host",
    )
    args = parser.parse_args()
    loop(args.log, args.host)
