# coding=utf-8

# Module that provides an interface for managing the bot over IRC.

'''
Copyright (C) 2018-2019 drastik.org

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

import datetime

from dbot_tools import Config
from user_auth import user_auth


class Module:
    def __init__(self):
        self.commands = ["join", "part", "privmsg", "notice",
                         "acl_add", "acl_del", "acl_list",
                         "mod_import",
                         "mod_whitelist_add", "mod_whitelist_del",
                         "mod_blacklist_add", "mod_blacklist_del",
                         "mod_list",
                         "mod_global_prefix_set", "mod_channel_prefix_set",
                         "admin_help"]


# --- Settings --- #
user_modes = ['~', '&', '@', '%']
####################


#
# Permission Checks
#
def is_bot_owner(irc, nickname):
    if nickname in irc.var.owners:
        return True
    else:
        return False


def is_channel_mod(irc, nickname, channel):
    try:
        for m in irc.var.namesdict[channel][1][nickname]:
            if m in user_modes:
                return True
        return False
    except Exception:
        return False


def is_allowed(i, irc, nickname, channel=""):
    if is_bot_owner(irc, nickname):
        if user_auth(i, irc, i.nickname):
            return True
        elif channel and is_channel_mod(irc, nickname, channel):
            return True
        else:
            return False
    elif channel and is_channel_mod(irc, nickname, channel):
        return True
    else:
        return False


#
# Channel Management
#
def _join(irc, channel, password=""):
    chan_dict = {channel: password}
    conf_r = Config(irc.cd).read()
    conf_r['irc']['channels'][channel] = password
    Config(irc.cd).write(conf_r)
    irc.var.config_load()
    irc.join(chan_dict)


def join(i, irc):
    if not i.msg_nocmd:
        m = f"Usage: {i.cmd_prefix}join <channel> [password]"
        return irc.notice(i.nickname, m)

    if not is_allowed(i, irc, i.nickname):
        m = "\x0304You are not authorized. Are you logged in?"
        return irc.notice(i.nickname, m)

    args = i.msg_nocmd.split(" ", 1)
    channel = args[0]
    try:
        password = args[1]
    except IndexError:
        password = ""

    if channel in irc.var.channels:
        m = f"\x0303The bot has already joined the channel: {channel}"
        return irc.notice(i.nickname, m)

    _join(irc, channel, password)
    irc.notice(i.nickname, f"\x0303Joined {channel}")


def _part(irc, channel, message=""):
    conf_r = Config(irc.cd).read()
    if channel not in conf_r['irc']['channels']:
        return False
    del conf_r['irc']['channels'][channel]
    Config(irc.cd).write(conf_r)
    irc.var.config_load()
    irc.part(channel, message)
    return True


def part(i, irc):
    if not i.msg_nocmd:
        m = f"Usage: {i.cmd_prefix}part <channel> [message]"
        return irc.notice(i.nickname, m)

    args = i.msg_nocmd.split(" ", 1)
    channel = args[0]
    try:
        message = args[1]
    except IndexError:
        message = ""

    if channel not in irc.var.channels:
        m = f"\x0304The bot has not joined the channel: {channel}"
        return irc.notice(i.nickname, m)

    if not is_allowed(i, irc, i.nickname, channel):
        m = f"\x0304You are not authorized. Are you an operator of {channel}?"
        return irc.notice(i.nickname, m)

    if _part(irc, channel, message):
        irc.notice(i.nickname, f"\x0303Left {channel}")
    else:
        irc.notice(i.nickname, f"\x0304{channel} not joined")


def privmsg(i, irc):
    m = f"Usage: {i.cmd_prefix}privmsg <channel> <message>"
    if not i.msg_nocmd:
        return irc.notice(i.nickname, m)

    args = i.msg_nocmd.split(" ", 1)
    if len(args) < 2:
        return irc.notice(i.nickname, m)

    channel = args[0]
    message = args[1]

    if channel not in irc.var.channels:
        m = f"\x0304The bot has not joined the channel: {channel}"
        return irc.notice(i.nickname, m)

    if not is_allowed(i, irc, i.nickname, channel):
        m = f"\x0304You are not authorized. Are you an operator of {channel}?"
        return irc.notice(i.nickname, m)

    irc.privmsg(channel, message)
    irc.notice(i.nickname, "\x0303Message sent")


def notice(i, irc):
    m = f"Usage: {i.cmd_prefix}notice <channel> <message>"
    if not i.msg_nocmd:
        return irc.notice(i.nickname, m)

    args = i.msg_nocmd.split(" ", 1)
    if len(args) < 2:
        return irc.notice(i.nickname, m)

    channel = args[0]
    message = args[1]

    if channel not in irc.var.channels:
        m = f"\x0304The bot has not joined the channel: {channel}"
        return irc.notice(i.nickname, m)

    if not is_allowed(i, irc, i.nickname, channel):
        m = f"\x0304You are not authorized. Are you an operator of {channel}?"
        return irc.notice(i.nickname, m)

    irc.notice(channel, message)
    irc.notice(i.nickname, "\x0303Message sent")


#
# User ACL
#
def _get_future_unix_timestamp_from_str(duration_str):
    seconds = 0

    tmp = 0
    for i in duration_str:
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
            return False

        now = datetime.datetime.now(datetime.timezone.utc).timestamp()
        return now + seconds


def _check_usermask(usermask):
    try:
        t = usermask.split("!", 1)
        t[0]
        t = t[1].split("@", 1)
        t[0]
        t[1]
        return True
    except Exception:
        return False


def _acl_add(irc, mask):
    c = Config(irc.cd).read()
    if mask in c['irc']['user_acl']:
        return False  # The mask already exists
    c['irc']['user_acl'].append(mask)
    Config(irc.cd).write(c)
    irc.var.config_load()
    return len(c['irc']['user_acl']) - 1


def acl_add(i, irc):
    m = (f"Usage: {i.cmd_prefix}acl_add "
         "<channel> <nickname>!<username>@<hostname> <duration> "
         f"<module1,module2,...> | See {i.cmd_prefix}admin_help for details.")
    if not i.msg_nocmd:
        return irc.notice(i.nickname, m)

    args = i.msg_nocmd.split(" ", 3)
    if len(args) < 4:
        return irc.notice(i.nickname, m)
    channel = args[0]
    usermask = args[1]
    duration = args[2]
    modules = args[3].replace(" ", "")

    if channel not in irc.var.channels and channel != '*':
        m = f"\x0304The bot has not joined the channel: {channel}"
        return irc.notice(i.nickname, m)

    if not _check_usermask:
        m = f"\x0304Invalid usermask: '{usermask}' given"
        return irc.notice(i.nickname, m)

    if duration != '0':
        duration = _get_future_unix_timestamp_from_str(duration)
        if not duration:
            m = "\x0304Error while parsing the duration string"
            return irc.notice(i.nickname, m)

    if modules != '*':
        module_list = modules.split(",")
        for mod in module_list:
            if mod not in i.modules:
                m = f"\x0304Error: Module {mod} is not loaded"

    if channel == '*':
        if not is_allowed(i, irc, i.nickname):
            m = f"\x0304You are not authorized. Are you logged in?"
            return irc.notice(i.nickname, m)
    else:
        if not is_allowed(i, irc, i.nickname, channel):
            m = ("\x0304You are not authorized. "
                 f"Are you an operator of {channel}?")
            return irc.notice(i.nickname, m)

    _acl_add(irc, i.msg_nocmd)
    irc.notice(i.nickname, f"\x0303User mask added in the ACL")


def _acl_del(irc, idx):
    c = Config(irc.cd).read()
    if len(c['irc']['user_acl']) - 1 <= idx:
        del c['irc']['user_acl'][idx]
        Config(irc.cd).write(c)
        irc.var.config_load()
        return True
    else:
        return False  # Index out of range


def acl_del(i, irc):
    m = f"Usage: {i.cmd_prefix}acl_del <mask ID>"
    if not i.msg_nocmd:
        return irc.notice(i.nickname, m)

    if len(i.msg_nocmd.split()) > 1:
        return irc.notice(i.nickname, m)

    idx = int(i.msg_nocmd)

    c = Config(irc.cd).read()
    mask = c['irc']['user_acl'][idx]
    channel = mask.split(" ", 1)[0]
    if channel == '*':
        if not is_allowed(i, irc, i.nickname):
            m = f"\x0304You are not authorized. Are you logged in?"
            return irc.notice(i.nickname, m)
    else:
        if not is_allowed(i, irc, i.nickname, channel):
            m = ("\x0304You are not authorized. "
                 f"Are you an operator of {channel}?")
            return irc.notice(i.nickname, m)

    if _acl_del(irc, idx):
        m = f"\x0303Deleted mask: '{mask}' from the ACL"
        irc.notice(i.nickname, m)
    else:
        m = "\x0304 This mask does not exist"
        irc.notice(i.nickname, m)


def acl_list(i, irc):
    for idx, mask in enumerate(irc.var.user_acl):
        irc.privmsg(i.nickname, f"{idx}: {mask}")


#
# Module Management
#
def mod_import(i, irc):
    if not is_allowed(i, irc, i.nickname):
        m = f"\x0304You are not authorized. Are you logged in?"
        return irc.notice(i.nickname, m)
    i.mod_import()
    irc.notice(i.nickname, '\x0303New module were imported.')


def _module_wb_list_add(i, irc, module, channel, mode):
    if mode == "whitelist":
        edom = "blacklist"
    elif mode == "blacklist":
        edom = "whitelist"
    else:
        raise ValueError("'mode' can only be 'whitelist' or 'blacklist'.")

    c = Config(irc.cd).read()
    ls = c["irc"]["modules"][mode]

    if module not in i.modules:
        return 1  # This module is not loaded
    elif (module in c["irc"]["modules"][edom]
          and channel in c["irc"]["modules"][edom][module]):
        return 2  # This module has a {edom}list set
    elif module not in ls:
        ls.update({module: []})
    elif channel in ls[module]:
        return 3  # This channel has already been added.

    ls[module].append(channel)
    Config(irc.cd).write(c)
    irc.var.config_load()
    return 0


def mod_whitelist_add(i, irc):
    m = f"Usage: {i.cmd_prefix}mod_whitelist_add <module> <channel>"
    if not i.msg_nocmd:
        return irc.notice(i.nickname, m)

    args = i.msg_nocmd.split(" ", 1)
    if len(args) < 2:
        return irc.notice(i.nickname, m)

    module = args[0]
    channel = args[1]

    if channel not in irc.var.channels:
        m = f"\x0304The bot has not joined the channel: {channel}"
        return irc.notice(i.nickname, m)

    if not is_allowed(i, irc, i.nickname, channel):
        m = f"\x0304You are not authorized. Are you an operator of {channel}?"
        return irc.notice(i.nickname, m)

    ret = _module_wb_list_add(i, irc, module, channel, "whitelist")
    if ret == 1:
        irc.notice(i.nickname, f"\x0304The module: {module} is not loaded")
    elif ret == 2:
        m = (f"\x0304The module: {module} has a blacklist set. "
             "Clear the blacklist and try again.")
        irc.notice(i.nickname, m)
    elif ret == 3:
        m = f"\x0304{channel} has already been added in {module}'s whitelist"
        irc.notice(i.nickname, m)
    else:
        m = f"\x0303{channel} added in {module}'s whitelist"
        irc.notice(i.nickname, m)


def mod_blacklist_add(i, irc):
    m = f"Usage: {i.cmd_prefix}mod_blacklist_add <module> <channel>"
    if not i.msg_nocmd:
        return irc.notice(i.nickname, m)

    args = i.msg_nocmd.split(" ", 1)
    if len(args) < 2:
        return irc.notice(i.nickname, m)

    module = args[0]
    channel = args[1]

    if channel not in irc.var.channels:
        m = f"\x0304The bot has not joined the channel: {channel}"
        return irc.notice(i.nickname, m)

    if not is_allowed(i, irc, i.nickname, channel):
        m = f"\x0304You are not authorized. Are you an operator of {channel}?"
        return irc.notice(i.nickname, m)

    ret = _module_wb_list_add(i, irc, module, channel, "blacklist")
    if ret == 1:
        irc.notice(i.nickname, f"\x0304The module: {module} is not loaded")
    elif ret == 2:
        m = (f"\x0304The module: {module} has a whitelist set. "
             "Clear the whitelist and try again.")
        irc.notice(i.nickname, m)
    elif ret == 3:
        m = f"\x0304{channel} has already been added in {module}'s blacklist"
        irc.notice(i.nickname, m)
    else:
        m = f"\x0303{channel} added in {module}'s blacklist"
        irc.notice(i.nickname, m)


def _module_wb_list_del(irc, module, channel, mode):
    if mode != "whitelist" and mode != "blacklist":
        raise ValueError("'mode' can only be 'whitelist' or 'blacklist'.")

    c = Config(irc.cd).read()
    ls = c["irc"]["modules"][mode]
    if module in ls and channel in ls[module]:
        ls[module].remove(channel)
        Config(irc.cd).write(c)
        irc.var.config_load()
        return True
    else:
        return False  # This channel has not been added.


def mod_whitelist_del(i, irc):
    m = f"Usage: {i.cmd_prefix}mod_whitelist_del <module> <channel>"
    if not i.msg_nocmd:
        return irc.notice(i.nickname, m)

    args = i.msg_nocmd.split(" ", 1)
    if len(args) < 2:
        return irc.notice(i.nickname, m)

    module = args[0]
    channel = args[1]

    if channel not in irc.var.channels:
        m = f"\x0304The bot has not joined the channel: {channel}"
        return irc.notice(i.nickname, m)

    if not is_allowed(i, irc, i.nickname, channel):
        m = f"\x0304You are not authorized. Are you an operator of {channel}?"
        return irc.notice(i.nickname, m)

    if _module_wb_list_del(irc, module, channel, "whitelist"):
        m = f"\x0303{channel} removed from {module}'s whitelist"
        return irc.notice(i.nickname, m)
    else:
        m = f"\x0304This channel has not been added in {module}'s whitelist"
        return irc.notice(i.nickname, m)


def mod_blacklist_del(i, irc):
    m = f"Usage: {i.cmd_prefix}mod_blacklist_del <module> <channel>"
    if not i.msg_nocmd:
        return irc.notice(i.nickname, m)

    args = i.msg_nocmd.split(" ", 1)
    if len(args) < 2:
        return irc.notice(i.nickname, m)

    module = args[0]
    channel = args[1]

    if channel not in irc.var.channels:
        m = f"\x0304The bot has not joined the channel: {channel}"
        return irc.notice(i.nickname, m)

    if not is_allowed(i, irc, i.nickname, channel):
        m = f"\x0304You are not authorized. Are you an operator of {channel}?"
        return irc.notice(i.nickname, m)

    if _module_wb_list_del(irc, module, channel, "blacklist"):
        m = f"\x0303{channel} removed from {module}'s blacklist"
        return irc.notice(i.nickname, m)
    else:
        m = f"\x0304This channel has not been added in {module}'s blacklist"
        return irc.notice(i.nickname, m)


def _module_wb_list_list(i, irc, channel=""):
    c = Config(irc.cd).read()
    wl = c["irc"]["modules"]["whitelist"]
    bl = c["irc"]["modules"]["blacklist"]

    wl_message = "\x0301,00WHITELIST\x0F :"
    if channel:
        wl_message += f" {channel} :"
    for module in wl:
        if not channel:
            wl_message += f" {module}: {wl['module']} /"
        else:
            if channel in wl[module]:
                wl_message += F" {module} /"

    bl_message = "\x0300,01BLACKLIST\x0F :"
    if channel:
        bl_message += f" {channel} :"
    for module in bl:
        if not channel:
            bl_message += f" {module}: {wl['module']} /"
        else:
            if channel in wl[module]:
                bl_message += F" {module} /"

    irc.privmsg(i.nickname, wl_message)
    irc.privmsg(i.nickname, bl_message)


def mod_list(i, irc):
    if not i.msg_nocmd:
        if not is_allowed(i, irc, i.nickname):
            m = (f"\x0304You are not authorized.\x0F "
                 "Usage: {i.cmd_prefix}mod_list <channel> | "
                 "Bot owners can ommit the <channel> argument.")
            return irc.notice(i.nickname, m)
        else:
            return _module_wb_list_list(i, irc)

    if len(i.msg_nocmd.split(" ")) > 1:
        m = (f"Usage: {i.cmd_prefix}mod_list <channel> | "
             "Bot owners can ommit the <channel> argument.")
        if not is_allowed(i, irc, i.nickname):
            m = (f"\x0304You are not authorized. "
                 "Are you an operator of {i.msg_nocmd}?")
            return irc.notice(i.nickname, m)
        else:
            return _module_wb_list_list(i, irc, i.msg_nocmd)


def _mod_global_prefix_set(irc, prefix):
    c = Config(irc.cd).read()
    c['irc']['modules']['global_prefix'] = prefix
    Config(irc.cd).write(c)
    irc.var.config_load()


def mod_global_prefix_set(i, irc):
    if not is_allowed(i, irc, i.nickname):
        m = f"\x0304You are not authorized. Are you logged in?"
        return irc.notice(i.nickname, m)

    m = f"Usage: {i.cmd_prefix}mod_global_prefix_set <prefix>"
    if not i.msg_nocmd:
        irc.notice(i.nickname, m)
    elif len(i.msg_nocmd.split(" ")) > 1:
        irc.notice(i.nickname, m)
    else:
        _mod_global_prefix_set(irc, i.msg_nocmd)
        m = f"\x0303Successfully changed the global_prefix to {i.msg_nocmd}"
        irc.notice(i.nickname, m)


def _mod_channel_prefix_set(irc, channel, prefix):
    c = Config(irc.cd).read()
    c['irc']['modules']['channel_prefix'][channel] = prefix
    Config(irc.cd).write(c)
    irc.var.config_load()


def mod_channel_prefix_set(i, irc):
    m = f"Usage: {i.cmd_prefix}mod_channel_prefix_set <channel> <prefix>"
    if not i.msg_nocmd:
        return irc.notice(i.nickname, m)

    args = i.msg_nocmd.split(" ", 1)
    if len(args) != 2:
        return irc.notice(i.nickname, m)

    channel = args[0]
    prefix = args[1]

    if channel not in irc.var.channels:
        m = f"\x0304The bot has not joined the channel: {channel}"
        return irc.notice(i.nickname, m)

    if not is_allowed(i, irc, i.nickname, channel):
        m = f"\x0304You are not authorized. Are you an operator of {channel}?"
        return irc.notice(i.nickname, m)

    _mod_channel_prefix_set(irc, channel, prefix)
    m = ("\x0303Successfully changed the channel_prefix for "
         f"{channel} to {prefix}")
    irc.notice(i.nickname, m)


#
# Help
#
def admin_help(i, irc):
    join = [
        f"Usage: {i.cmd_prefix}join <channel> [password]",
        " Permission: Owners",
        "Join a channel."
    ]
    part = [
        f"Usage: {i.cmd_prefix}part <channel> [message]",
        " Permission: Channel Operators",
        "Leave a channel. Channel Operators can only use this command on"
        " channels where they have operator privilages."
    ]
    privmsg = [
        f"Usage: {i.cmd_prefix}privmsg <channel> <message>",
        " Permission: Channel Operators",
        "Have the bot send a private message to a channel or a person. You"
        " must be an operator of the channel you want to send a private"
        " message to. Only bot owners can use this command to send messages to"
        " other users."
    ]
    notice = [
        f"Usage: {i.cmd_prefix}notice <channel> <message>",
        " Permission: Channel Operators",
        "Have the bot send a notice to a channel or a person. You must be an"
        " operator of the channel you want to send a notice to. Only bot"
        " owners can use this command to send notices to other users."
    ]
    acl_add = [
        f"Usage: {i.cmd_prefix}acl_add <channel> "
        "<nickname>!<username>@<hostname> <duration> <module1,module2,...>",
        " Permission: Channel Operators",
        "Add a user access list rule.",
        "Explanation:",
        "<channel> : This can be a single channel or '*'. Users can only set"
        " this to a channel where they have operator privilages. '*' means all"
        " channels and can only be used by bot owners.",
        "<nickname>: This can be the exact nickname of an IRC user or '*'."
        "  '*' means any nickname.",
        "<username>: This can be the exact username of an IRC user or '*' or"
        " or '*<word>'. '*' means match any username. '*<word>' would match"
        " everything that has <word> in the end. Note that using the *"
        " character in the  middle or in the end of <word> would exactly"
        " match <word>* and won't expand to other usernames.",
        "<hostname>: It can be the exact hostname of an IRC user, '*',"
        " '*<word>' or '<word>*'. '*' means match any hostname. '*<word>' and"
        " '<word>*' would match everything that has <word> in the end or in"
        " the beginning. Every other placement of the * character would be an"
        " exact match.",
        "<duration>: Duration is used to specify for how long the rule should"
        " be in effect. The syntax used is yMwdhms. No spaces should be used."
        " To have the rule in effect forever set this to '0'."
        " Example: 1y2M3m would mean 1 year, 2 Months, 3 minutes.",
        "<mod1,...>: This is a list of modules that the rule will apply to."
        " The list is comma seperated. Use '*' to have the rule apply for all"
        " modules.",
        "Examples:",
        "#bots nick!*@* 0 * : Rule to block the user with the nickname 'nick'"
        " from using any module in the channel #bots forever.",
        "#bots *!*@*isp.IP 1M1w3h tell : This rule will block any user with"
        " the domain 'isp.IP' from using the tell module for 1 Month 1 week"
        " and 3 hours in the channel #bots."
    ]
    acl_del = [
        f"Usage: {i.cmd_prefix}acl_del <mask ID>",
        " Permission: Channel Operators",
        "Remove a rule from the user access list using its ID. The ID can be"
        " retrieved using the command: {i.cmd_prefix}acl_list. Note that the"
        " IDs might change everytime a rule is deleted. Users can only delete"
        " delete rules for channels where they have Operator rights. Rules"
        " that have their channel part set to '*' can only be deleted by the"
        " bot's owners."
    ]
    acl_list = [
        f"Usage: {i.cmd_prefix}acl_list",
        " Permission: Everyone",
        "Get a list of every rule set. Rules are numbered. This number is"
        " their current ID and can be used in the acl_del command."
    ]
    mod_import = [
        f"Usage: {i.cmd_prefix}mod_import",
        " Permission: Owners",
        "Import any new modules specified in the configuration file and reload"
        " the currently imported ones."
    ]
    mod_whitelist_add = [
        f"Usage: {i.cmd_prefix}mod_whitelist_add <module> <channel>",
        " Permission: Channel Operators",
        "Add a channel to a module's whitelist. This will make the module only"
        " respond to the channels added in this whitelist. You cannot add a"
        " channel to a modules whitelist if a blacklist is already in place."
    ]
    mod_blacklist_add = [
        f"Usage: {i.cmd_prefix}mod_blacklist_add <module> <channel>",
        " Permission: Channel Operators",
        "Add a channel to a module's blacklist. This will make the module not"
        " respond to the channels added in this blacklist. You cannot add a"
        " channel to a modules blacklist if a whitelist is already in place."
    ]
    mod_whitelist_del = [
        f"Usage: {i.cmd_prefix}mod_whitelist_del <module> <channel>",
        " Permission: Channel Operators",
        "Delete a channel from a module's whitelist."
    ]
    mod_blacklist_del = [
        f"Usage: {i.cmd_prefix}mod_blacklist_del <module> <channel>",
        " Permission: Channel Operators",
        "Delete a channel from a module's blacklist."
    ]
    mod_list = [
        f"Usage: {i.cmd_prefix}mod_list <channel>",
        " Permission: Channel Operators",
        "Get a list of every module that has <channel> in its whitelist or"
        " blacklist. Bot owners can omit the <channel argument> and get a list"
        " of all channels that have been in a whitelist or a blacklist."
    ]
    mod_global_prefix_set = [
        f"Usage: {i.cmd_prefix}mod_global_prefix_set <prefix>",
        " Permission: Owners",
        "Set the default prefix used for commands. This is the character used"
        " before a command name. E.g.: .command  '.' is the prefix here."
    ]
    mod_channel_prefix_set = [
        f"Usage: {i.cmd_prefix}mod_channel_prefix_set <channel> <prefix>",
        " Permission: Channel Operators",
        "Set the default prefix used for commands in a specific channel. This"
        " is the character used before a command name. E.g.: .command  '.' is"
        " the prefix here. This prefix overrides the default value."
    ]

    help_d = {
        "join": join,
        "part": part,
        "privmsg": privmsg,
        "notice": notice,
        "acl_add": acl_add,
        "acl_del": acl_del,
        "acl_list": acl_list,
        "mod_import": mod_import,
        "mod_whitelist_add": mod_whitelist_add,
        "mod_blacklist_add": mod_blacklist_add,
        "mod_whitelist_del": mod_whitelist_del,
        "mod_blacklist_del": mod_blacklist_del,
        "mod_list": mod_list,
        "mod_global_prefix_set": mod_global_prefix_set,
        "mod_channel_prefix_set": mod_channel_prefix_set,
        "admin_help": admin_help
    }
    try:
        cmd_help_list = help_d[i.msg_nocmd]
    except KeyError:
        avail_cmd = ""
        for cmd in help_d:
            avail_cmd += f"{cmd}, "
        avail_cmd = avail_cmd[:-3]
        m = f"Usage: {i.cmd_prefix}admin_help <admin command>"
        irc.notice(i.nickname, m)
        m = f"Available commands are: {avail_cmd}"
        irc.notice(i.nickname, m)
        return

    for line in cmd_help_list:
        irc.notice(i.nickname, line)


def main(i, irc):
    func_d = {
        "join": join,
        "part": part,
        "privmsg": privmsg,
        "notice": notice,
        "acl_add": acl_add,
        "acl_del": acl_del,
        "acl_list": acl_list,
        "mod_import": mod_import,
        "mod_whitelist_add": mod_whitelist_add,
        "mod_blacklist_add": mod_blacklist_add,
        "mod_whitelist_del": mod_whitelist_del,
        "mod_blacklist_del": mod_blacklist_del,
        "mod_list": mod_list,
        "mod_global_prefix_set": mod_global_prefix_set,
        "mod_channel_prefix_set": mod_channel_prefix_set,
        "admin_help": admin_help
    }
    func_d[i.cmd](i, irc)
