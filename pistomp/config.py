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

from os import getcwd
from os.path import join
from typing import Optional
import yaml


DEFAULT_CONFIG_DIR = getcwd() + 'conf'
DEFAULT_CONFIG_FILE = "default_config.yml"


def load_cfg(file_name: Optional[str] = None) -> dict:
    # Read the default config file - should only need to read once per session
    if file_name is None:
        file_name = join(DEFAULT_CONFIG_DIR, DEFAULT_CONFIG_FILE)
    with open(file_name, "r") as f:
        return yaml.load(f, Loader=yaml.SafeLoader)
