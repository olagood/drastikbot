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
import datetime

from dbothelper import is_ascii_cl


# ====================================================================
# User ACL: Helper functions to parser user_acl masks
# ====================================================================

# Parser

def parse_uacl(mask):
    args = mask.split(" ", 3)
    if len(args) < 4:
        return 1, len(args) # Not enough arguments given

    channel = args[0]

    usermask = _parse_usermask_uacl(args[1])
    if not usermask:
        return 2, args[1]  # Invalid usermask

    nick, user, host = usermask

    timestamp = _get_future_unix_timestamp_uacl(args[2])
    if timestamp is None:
        return 3, args[2]  # Invalid duration

    modules = _parse_modules_uacl(args[3])
    if not modules:
        return 4, args[3]  # Invalid modules

    return {
        "channel": channel,
        "nick": nick,
        "user": user,
        "host": host,
        "timestamp": timestamp,
        "modules": modules
    }


def _parse_usermask_uacl(usermask):
    try:
        t = usermask.split("!", 1)
        nick = t[0]
        user, host = t[1].split("@", 1)
        return nick, user, host
    except Exception:
        return False


def _get_future_unix_timestamp_uacl(duration_s):
    if duration_s == "0":
        return 0

    seconds = 0
    tmp = 0
    for i in duration_s:
        if i.isdigit():
            tmp *= 10
            tmp += int(i)
        elif i == 'y':
            seconds += 31536000 * tmp  # 365days * 24hours * 60mins * 60secs
            tmp = 0
        elif i == 'M':
            seconds += 2592000 * tmp  # 30days * 24hours * 60mins * 60secs
            tmp = 0
        elif i == 'w':
            seconds += 604800 * tmp  # 7days * 24hours * 60mins * 60secs
            tmp = 0
        elif i == 'd':
            seconds += 86400 * tmp  # 24hours * 60mins * 60secs
            tmp = 0
        elif i == 'h':
            seconds += 3600 * tmp  # 60mins * 60secs
            tmp = 0
        elif i == 'm':
            seconds += 60 * tmp  # 60secs
            tmp = 0
        elif i == 's':
            seconds += tmp
            tmp = 0
        else:
            return None

    now = datetime.datetime.now(datetime.timezone.utc).timestamp()
    return now + seconds


def _parse_modules_uacl(modules_s):
    if not modules_s:
        return False

    if modules_s == "*":
        return "*"

    return modules_s.replace(" ", "").split(",")


# User ACL checks

def is_joined_uacl(mask, conf):
    channel = mask["channel"]
    return conf.has_channel(channel) or channel == "*"


def is_banned_uacl(mask, channel, nick, user, host, module):
    """Check if a user is banned from using the bot.

    :param mask: A ``mask'' string in the following format:
                 channel nickname!username@hostmask time modules
    A * wildcard is allowed in front of the username and the hostmask.
    """
    tokens = parse_uacl(mask)

    m_channel = tokens["channel"]
    if not (is_ascii_cl(m_channel, channel) or m_channel == "*"):
        return False

    m_nick = tokens["nick"]
    if not (is_ascii_cl(m_nick, nick) or m_nick == "*"):
        return False

    return is_user_uacl(tokens, user) and is_host_uacl(tokens, host) \
        and is_timestamp_uacl(tokens, host) and is_module_uacl(tokens, module)


def is_user_uacl(tokens, user):
    # Usernames are not case sensitive
    u = tokens["user"].lower()
    user = user.lower()

    if u == user or u == "*":
        return True

    # If `u' is in this form: `*<text>' then check if `user' ends with <text>
    if "*" == u[0] and u[1:] == user[-len(u[1:]):]:
        return True

    return False


def is_host_uacl(tokens, host):
    h = tokens["host"]

    if h == host or h == "*":
        return True

    # If `h' is in this form: `*<text>' then check if `host' ends with <text>
    if "*" == h[0] and h[1:] == host[-len(m[1:]):]:
        return True

    # If `h' is in this form: `<text>*' then check if `host' starts with <text>
    if "*" == m[-1] and m[:-1] == hostmask[:len(m[:-1])]:
        return True

    return False


def is_timestamp_uacl(tokens):
    timestamp = tokens["timestamp"]

    if timestamp == 0:
        return True  # No timestamp set

    now = datetime.datetime.now(datetime.timezone.utc).timestamp()
    return timestamp > now


def is_module_uacl(tokens, module):
    m = tokens["modules"]

    if m == '*':
        return True

    return module in m


# ====================================================================
# Configuration: config file read/write interface
# ====================================================================

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
        return is_ascii_cl(self.get_auth_method(), method)

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

    def get_modules_paths(self):
        return self.conf["irc"]["modules"]["paths"]

    def get_module_settings(self, module):
        try:
            return self.conf["irc"]["modules"]["settings"][module]
        except KeyError:
            return {}

    def set_module_settings(self, module, settings):
        self.conf["irc"]["modules"]["settings"][module] = settings
        self.save()

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

    def is_banned_user_access_list(self, msg, module):
        uacl = self.get_user_access_list()

        if uacl is None:
            return False

        nick = msg.get_nickname()
        user = msg.get_user()
        host = msg.get_host()
        chan = msg.get_msgtarget()

        for i in uacl:
            if is_banned_uacl(i, chan, nick, user, host, module):
                return True
        return False

    def is_expired_user_access_list(self, mask):
        t = mask["timestamp"]

        if t == 0:
            return False

        now = datetime.datetime.now(datetime.timezone.utc).timestamp()
        return t < now
