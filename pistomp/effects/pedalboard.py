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

import json
import lilv
import logging
import operator
import os
import requests as req
import sys
import urllib.parse

from pistomp.util import constants as Token
from .parameter import Parameter
from .plugin import Plugin

LOGGER = logging.getLogger(__name__)
PB_NODE_URI = "http://moddevices.com/ns/modpedal#Pedalboard"


class Pedalboard:
    def __init__(self, title, bundle):
        self.root_uri = "http://localhost:80/"
        self.title = title
        self.bundle = bundle  # TODO used?
        self.plugins = []

        self.world = self.init_world()
        self.uri_block = self.world.new_uri("http://drobilla.net/ns/ingen#block")
        self.uri_head = self.world.new_uri("http://drobilla.net/ns/ingen#head")
        self.uri_port = self.world.new_uri("http://lv2plug.in/ns/lv2core#port")
        self.uri_tail = self.world.new_uri("http://drobilla.net/ns/ingen#tail")
        self.uri_value = self.world.new_uri("http://drobilla.net/ns/ingen#value")

    @staticmethod
    def init_world() -> lilv.World:
        world = lilv.World()
        world.load_specifications()
        world.load_plugin_classes()
        return world

    def get_pedalboard_plugin(self) -> lilv.Plugin:
        # lilv wants the last character as the separator
        bundle = os.path.abspath(self.bundle)
        bundle += '' if bundle.endswith(os.sep) else os.sep
        # convert bundle string into a lilv node
        bundlenode = self.world.new_file_uri(None, bundle)

        # load the bundle
        self.world.load_bundle(bundlenode)

        # free bundlenode, no longer needed
        # self.world.node_free(bundlenode)  # TODO find out why this is no longer necessary (why did API method go away)

        # get all plugins in the bundle
        ps = self.world.get_all_plugins()

        # make sure the bundle includes 1 and only 1 plugin (the pedalboard)
        if len(ps) != 1:
            raise Exception("get_pedalboard_info(%s) - bundle has 0 or > 1 plugin".format(bundle))

        # no indexing in python-lilv yet, just get the first item
        plugin = next(iter(ps))
        if plugin is None:
            raise Exception("get_pedalboard_plugin(%s)".format(bundle))
        return plugin

    def get_plugin_data(self, uri) -> dict:
        url = self.root_uri + "effect/get?uri=" + urllib.parse.quote(uri)
        try:
            resp = req.get(url, headers={"Cache-Control": "no-cache", "Pragma": "no-cache"})
        except:  # TODO
            LOGGER.error("Cannot connect to mod-host.")
            sys.exit()

        if resp.status_code != 200:
            LOGGER.error(
                "mod-host not able to get plugin data: %s\nStatus: %s" % (url, resp.status_code)
            )
            return {}

        return json.loads(resp.text)

    def chase_tail(self, block, conn: list = None, first: bool = False):
        if conn is None:
            conn = []
        if first:
            ports = block.get_value(self.uri_port)
        else:
            if block is None:
                return
            conn.append(block)
            ports = self.world.find_nodes(block, self.uri_port, None)
        for port in ports:
            if port is None:
                continue
            tail = self.world.get(None, self.uri_tail, port)
            if tail is None:
                continue
            head = self.world.get(tail, self.uri_head, None)
            if head is not None:
                block = self.world.get(None, self.uri_port, head)
                if block is not None and block not in conn:
                    self.chase_tail(block, conn)
            break
        return conn

    # Get info from an lv2 bundle
    # @a bundle is a string, consisting of a directory in the filesystem (absolute pathname).
    def load_bundle(self) -> dict:
        plugin_dict = {}
        # Load the bundle, return the single plugin for the pedalboard
        plugin = self.get_pedalboard_plugin()

        u = self.world.new_uri("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")
        if PB_NODE_URI not in [n for n in plugin.get_value(u)]:
            raise Exception(
                "get_pedalboard_info(%s) - plugin has no mod:Pedalboard type".format(self.bundle)
            )

        # Walk ports starting from capture1 to determine general plugin order
        plugin_order = self.chase_tail(plugin, None, True)

        # Iterate blocks (plugins)
        plugins_unordered = {}
        plugins_extra = []
        blocks = plugin.get_value(self.uri_block)
        for block in blocks:
            if block is None or block.is_blank():
                continue

            # Add plugin data (from plugin registry) to global plugin dictionary
            category = None
            plugin_info = {}
            prototype = self.world.find_nodes(block, self.world.ns.lv2.prototype, None)
            if len(prototype) > 0:
                # logging.debug("prototype %s" % prototype[0])
                plugin_uri = str(prototype[0])  # plugin.get_uri()
                plugin_info = plugin_dict.get(plugin_uri, self.get_plugin_data(plugin_uri))
                if plugin_info:
                    LOGGER.debug("added %s" % plugin_uri)
                    plugin_dict[plugin_uri] = plugin_info
                    cat = plugin_info.get(Token.CATEGORY)
                    if cat is not None and len(cat) > 0:
                        category = cat[0]

            # Extract Parameter data
            instance_id = str(block.get_path()).replace(self.bundle, "", 1)
            nodes = self.world.find_nodes(block, self.world.ns.lv2.port, None)
            parameters = {}
            if len(nodes) > 0:
                # These are the port nodes used to define parameter controls
                for port in nodes:
                    param_value = self.world.get(port, self.uri_value, None)
                    # logging.debug("port: %s  value: %s" % (port, param_value))
                    binding = self.world.get(port, self.world.ns.midi.binding, None)
                    if binding is not None:
                        controller_num = self.world.get(
                            binding, self.world.ns.midi.controllerNumber, None
                        )
                        channel = self.world.get(binding, self.world.ns.midi.channel, None)
                        if (controller_num is not None) and (channel is not None):
                            binding = "%d:%d" % (
                                self.world.new_int(channel),
                                self.world.new_int(controller_num),
                            )
                            LOGGER.debug("  MIDI CC binding %s" % binding)
                    path = str(port)
                    symbol = os.path.basename(path)
                    value = None
                    if param_value is not None:
                        if param_value.is_float():
                            value = float(self.world.new_float(param_value))
                        elif param_value.is_int():
                            value = int(self.world.new_int(param_value))
                        else:
                            value = str(value)
                    # Bypass "parameter" is a special case without an entry in the plugin definition
                    if symbol == Token.COLON_BYPASS:
                        info = {
                            "shortName": "bypass",
                            "symbol": symbol,
                            "ranges": {"minimum": 0, "maximum": 1},
                        }  # TODO tokenize
                        v = False if value == 0 else True
                        param = Parameter(info, v, binding)
                        parameters[symbol] = param
                        continue  # don't try to find matching symbol in plugin_dict

                    # Try to find a matching symbol in plugin_dict to obtain the remaining param details
                    plugin_params = plugin_info.get(Token.PORTS, {}).get(Token.CONTROL, {}).get(Token.INPUT, [])
                    for pp in plugin_params:
                        sym = pp.get(Token.SYMBOL)
                        if sym == symbol:
                            # logging.debug("PARAM: %s %s %s" % (util.DICT_GET(pp, 'name'), info[uri], category))
                            param = Parameter(pp, value, binding)
                            # logging.debug("Param: %s %s %4.2f %4.2f %s" % (param.name, param.symbol, param.minimum, value, binding))
                            parameters[symbol] = param

                    # logging.debug("  Label: %s" % label)
            inst = Plugin(instance_id, parameters, category)

            try:
                index = plugin_order.index(block)
                plugins_unordered[index] = inst
            except:
                plugins_extra.append(inst)
            # logging.debug("dump: %s" % inst.to_json())

        # Add "extra" plugins (those not part of the tail_chase order) to the plugins_unordered dict
        max_index = len(plugins_unordered)
        for e in plugins_extra:
            plugins_unordered[max_index] = e
            max_index = max_index + 1

        # Sort the dictionary based on their order index and add to the pedalboard.plugin list
        # TODO improve the creation (tail chasing, sorting, dict>list conversion)
        if max_index > 0:
            sorted_dict = dict(sorted(plugins_unordered.items(), key=operator.itemgetter(0)))
            for i in range(0, len(sorted_dict)):
                val = sorted_dict.get(i)
                if val is not None:
                    self.plugins.append(val)

        # Done obtaining relevant lilv for the pedalboard
        return plugin_dict

    def to_json(self):
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)
