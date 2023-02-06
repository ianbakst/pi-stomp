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
from typing import Optional

from PIL import Image


class Tool:
    def __init__(self, tool_type, x, y, img_path: Optional[str] = None):
        self.tool_type = tool_type
        self.x = x
        self.y = y
        self.image = None
        self.update_img(img_path)

    def update_img(self, img_path: Optional[str]):
        self.image = None if img_path is None else Image.open(img_path)
