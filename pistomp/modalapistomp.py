import logging
import os
import RPi.GPIO as GPIO
import sys
import time

from rtmidi.midiutil import open_midioutput

from . import host as host
from . import audiocard as ac
from . import hardware
import pistomp


def main_loop(log: str, host_type: str) -> None:
    if log is not None:
        print("Log level now set to: %s" % logging.getLevelName(log.upper()))
        logging.basicConfig(level=log.upper())

    # Current Working Dir
    cwd = os.path.dirname(os.path.realpath(__file__))
    cfg = pistomp.config.load_cfg()

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
    handler = None

    if host_type == "mod":

        # Create singleton Mod handler
        handler = host.Factory().create(audiocard, cwd)

        # Initialize hardware (Footswitches, Encoders, Analog inputs, etc.)
        hw = hardware.Factory().create(cfg, handler, midiout)
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
