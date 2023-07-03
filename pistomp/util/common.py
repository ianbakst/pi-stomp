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
def lilv_foreach(collection):
    collection_iter = iter(collection)
    while not collection_iter.is_end():
        next_collection = next(collection_iter)
        yield next_collection if next_collection.is_uri() else None

def renormalize(n, left_min, left_max, right_min, right_max):
    # this remaps a value from original (left) range to new (right) range
    # Figure out how 'wide' each range is
    delta1 = left_max - left_min
    delta2 = right_max - right_min
    return round((delta2 * (n - left_min) / delta1) + right_min)


def renormalize_float(value, left_min, left_max, right_min, right_max):
    # this remaps a value from original (left) range to new (right) range
    # Figure out how 'wide' each range is
    left_span = abs(left_max - left_min)
    num_divisions = left_span / value

    right_span = abs(right_max - right_min)

    return round(right_span / num_divisions, 2)


def format_float(value):
    if value < 10:
        if value < 1:
            return "%.2f" % value
        else:
            return "%.1f" % value
    else:
        return "%d" % value
