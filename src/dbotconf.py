# coding=utf-8

# Utilities for working with the configuration file

'''
Copyright (C) 2021 drastik.org

This file is part of drastikbot.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published
by the Free Software Foundation, version 3 only.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
'''

import json


class Configuration:
    """
    The Config class provides easy reading and writing to the
    bot's configuration file.
    path : should be a pathlib.Path to the configuration file.
    """
    def __init__(self, path):
        self.path = path
        self.conf = {}

        # Check if the config file exists
        if not path.is_file():
            self.save()  # Create the file
            return

        self.load()  # Load the configuration into self.conf

    def load(self):
        with open(self.path, "r") as f:
            self.conf = json.load(f)

    def save(self):
        with open(self.path, "w") as f:
            json.dump(self.conf, f, indent=4)

    def get_sys_log_level(self):
        try:
            return self.conf["sys"]["log_level"]
        except KeyError:
            return "info"

    def get_sys_log_dir(self):
        try:
            return self.conf["sys"]["log_dir"]
        except KeyError:
            return None

    def get_owners(self):
        return self.conf["irc"]["owners"]

    def get_host(self):
        return self.conf["irc"]["connection"]["network"]

    def get_port(self):
        return self.conf["irc"]["connection"]["port"]

    def get_ssl(self):
        return self.conf["irc"]["connection"].get("ssl", False)

    def get_nickname(self):
        return self.conf["irc"]["connection"]["nickname"]

    def get_user(self):
        return self.conf["irc"]["connection"]["username"]

    def get_realname(self):
        return self.conf["irc"]["connection"]["realname"]

    def get_auth_method(self):
        return self.conf["irc"]["connection"].get("authentication", "")

    def is_auth_method(self, method):
        # Plain ASCII comparison is enough.
        # The bot will never use non-ASCII string values.
        return self.get_auth_method().lower() == method.lower()

    def get_auth_password(self):
        return self.conf["irc"]["connection"]["auth_password"]

    def get_network_passoword(self):
        return self.conf["irc"]["connection"].get("net_passoword", "")

    def get_quitmsg(self):
        m = f"drastikbot2 - drastik.org"
        return self.conf["irc"]["connection"].get("quitmsg", m)

    def get_msg_delay(self):
        return self.conf["irc"]["connection"].get("msg_delay", 1)

    def get_channels(self):
        return self.conf["irc"]["channels"]

    def set_channel(self, channel, password):
        self.conf["irc"]["channels"][channel] = password
        self.save()

    def del_channel(self, channel):
        del self.conf['irc']['channels'][channel]
        self.save()

    def has_channel(self, channel):
        if channel not in self.conf['irc']['channels']:
            return False
        return True

    def get_modules_load(self):
        return self.conf["irc"]["modules"]["load"]

    def get_module_blacklist(self, module):
        try:
            return self.conf["irc"]["modules"]["blacklist"][module]
        except KeyError:
            return None

    def is_allowed_module_blacklist(self, module):
        wl = self.get_module_whitelist(module)
        return wl is None or not wl

    def has_channel_module_blacklist(self, module, channel):
        bl = self.get_module_blacklist(module)
        if bl is None:
            return False
        return channel in bl

    def add_channel_module_blacklist(self, module, channel):
        if not self.is_allowed_module_blacklist(module):
            return
        bl = self.get_module_blacklist(module)
        if bl is None:
            self.conf["irc"]["modules"]["blacklist"][module] = [channel]
            self.save()
        elif channel in bl:
            return  # already exists
        else:
            bl.append(channel)
            self.save()

    def del_channel_module_blacklist(self, module, channel):
        if not self.has_channel_module_blacklist(module, channel):
            return
        self.get_module_blacklist(module).remove(channel)
        self.save()

    def get_module_whitelist(self, module):
        try:
            return self.conf["irc"]["modules"]["whitelist"][module]
        except KeyError:
            return None

    def is_allowed_module_whitelist(self, module):
        bl = self.get_module_blacklist(module)
        return bl is None or not bl

    def has_channel_module_whitelist(self, module, channel):
        wl = self.get_module_whitelist(module)
        if wl is None:
            return False
        return channel in wl

    def add_channel_module_whitelist(self, module, channel):
        if not self.is_allowed_module_whitelist(module):
            return
        wl = self.get_module_whitelist(module)
        if wl is None:
            self.conf["irc"]["modules"]["whitelist"][module] = [channel]
            self.save()
        elif channel in wl:
            return  # already exists
        else:
            wl.append(channel)
            self.save()

    def del_channel_module_whitelist(self, module, channel):
        if not self.has_channel_module_whitelist(module, channel):
            return
        self.get_module_whitelist(module).remove(channel)
        self.save()

    def check_channel_module_access(self, module, channel):
        """Check if the the given module/channel combination is allowed
        according to the configured access list (blacklist/whitelist)
        rules.

        It returns True if one of the following conditions are met:
        - There is no blacklist and no whitelist set for this module.
        - The channel is not in a blacklist and it is in a whitelist.
        Otherwise it returns False.

        @returns True If the module can be applied in this channel
                 False Otherwise
        """
        bl = self.get_module_blacklist(module)
        wl = self.get_module_whitelist(module)
        if (not bl or channel not in bl) and (not wl or channel in wl):
            return True
        return False

    def get_global_prefix(self):
        return self.conf["irc"]["modules"]["global_prefix"]

    def set_global_prefix(self, prefix):
        self.conf["irc"]["modules"]["global_prefix"] = prefix
        self.save()

    def get_channel_prefix(self, channel):
        chp_d = self.conf["irc"]["modules"]["channel_prefix"]
        return chp_d.get(channel, self.get_global_prefix())

    def set_channel_prefix(self, channel, prefix):
        self.conf["irc"]["modules"]["channel_prefix"][channel] = prefix
        self.save()

    def get_user_access_list(self):
        try:
            return self.conf["irc"]["user_acl"]
        except KeyError:
            return None

    def has_user_access_list(self, mask):
        return mask in self.conf["irc"]["user_acl"]

    def has_index_user_access_list(self, index):
        try:
            self.get_user_access_list()[index]
            return True
        except IndexError:
            return False

    def add_user_access_list(self, mask):
        if self.has_user_access_list(mask):
            return  # The mask already exists
        self.conf["irc"]["user_acl"].append(mask)
        self.save()

    def del_user_access_list(self, index):
        del self.conf["irc"]["user_acl"][index]
        self.save()
