#!/usr/bin/env python3

import argparse
import atexit
import RPi.GPIO as GPIO
import json
import logging
import os
import requests as req
import RPi.GPIO as GPIO
import spidev
import sys
import time

from rtmidi.midiutil import open_midiinput
from rtmidi.midiutil import open_midioutput
from rtmidi.midiconstants import (CONTROLLER_CHANGE, PROGRAM_CHANGE)

import modalapi.mod as Mod
import pistomp.lcdgfx as Lcd
#import pistomp.lcd128x32 as Lcd
#import pistomp.lcd135x240 as Lcd
#import pistomp.lcdsy7789 as Lcd
#import pistomp.lcdili9341 as Lcd # Color
import pistomp.pistomp as Pistomp


def main():
    # Command line parsing
    parser = argparse.ArgumentParser()
    parser.add_argument("-l", "--log", nargs='+', help="Provide logging level. Example --log debug'", default="info",
                        choices=['debug', 'info', 'warning', 'error', 'critical'])

    # Handle Log Level
    level_config = {'debug': logging.DEBUG, 'info': logging.INFO, 'warning': logging.WARNING, 'error': logging.ERROR,
                    'critical': logging.CRITICAL}
    log = parser.parse_args().log[0]
    log_level = level_config[log] if log in level_config else None
    if log_level:
        print("Log level now set to: %s" % logging.getLevelName(log_level))
        logging.basicConfig(level=log_level)

    # MIDI initialization
    # Prompts user for MIDI input port, unless a valid port number or name
    # is given as the first argument on the command line.
    # API backend defaults to ALSA on Linux.
    # TODO discover and use the thru port (seems to be 14:0 on my system)
    # shouldn't need to aconnect, just send msgs directly to the thru port
    port = 0 # TODO get this (the Midi Through port) programmatically
    #port = sys.argv[1] if len(sys.argv) > 1 else None
    try:
        midiout, port_name = open_midioutput(port)
    except (EOFError, KeyboardInterrupt):
        sys.exit()

    # LCD
    lcd = Lcd.Lcd()

    # Create singleton data model object
    mod = Mod.Mod(lcd)

    # Initialize hardware (Footswitches, Encoders, Analog inputs, etc.)
    hw = Pistomp.Pistomp(mod, midiout, refresh_callback=mod.update_lcd_fs)
    mod.add_hardware(hw)

    # Load all pedalboard info from the lilv ttl file
    mod.load_pedalboards()

    # Load the current pedalboard as "current"
    current_pedal_board_bundle = mod.get_current_pedalboard_bundle_path()
    if not current_pedal_board_bundle:
        # Apparently, no pedalboard is currently loaded so just load the first one
        current_pedal_board_bundle = list(mod.pedalboards.keys())[0]
    mod.set_current_pedalboard(mod.pedalboards[current_pedal_board_bundle])


    # Load LCD
    #mod.update_lcd()
    #touch.set_led(0, 1)
    #touch.set_led(2, 1)

    logging.info("Entering main loop. Press Control-C to exit.")
    #period = 0
    try:
        while True:
            hw.poll_controls()
            time.sleep(0.01)  # TODO less to increase responsiveness

            # For less frequent events
            # period += 1
            # if period > 100:
            #     period = 0

    except KeyboardInterrupt:
        logging.info('keyboard interrupt')
    finally:
        logging.info("Exit.")
        midiout.close_port()
        lcd.cleanup()
        GPIO.cleanup()
        logging.info("Completed cleanup")


if __name__ == '__main__':
    main()
