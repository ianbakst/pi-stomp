import argparse
from .modalapistomp import main_loop

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
    "-h",
    help="Plugin host to use. Example --host mod'",
    default="mod",
    choices=["mod", "generic", "test"],
    dest="host",
)

args = parser.parse_args()
main_loop(args.log, args.host)
