# coding=utf-8

# Module that provides an interface for managing the bot over IRC.

'''
Copyright (C) 2018-2019, 2021 drastik.org

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

import irc.modules as modmgmt
from dbotconf import parse_uacl
from user_auth import user_auth


class Module:
    bot_commands = [
        "join", "part", "privmsg", "notice",
        "acl_add", "acl_del", "acl_list",
        "mod_import", "mod_reload",
        "mod_whitelist_add", "mod_whitelist_del",
        "mod_blacklist_add", "mod_blacklist_del",
        "mod_list",
        "mod_global_prefix_set", "mod_channel_prefix_set",
        "admin_help"
    ]


# --- Settings --- #
user_modes = ['~', '&', '@', '%']
####################


#
# Permission Checks
#
def is_bot_owner(irc, nickname):
    if nickname in irc.conf.get_owners():
        return True
    else:
        return False


def is_channel_mod(irc, nickname, channel):
    try:
        for m in irc.names[channel][nickname]:
            if m[0] in user_modes:
                return True
        return False
    except Exception:
        return False


def is_allowed(i, irc, nickname, channel=""):
    if is_bot_owner(irc, nickname):
        if user_auth(i, irc, i.msg.get_nickname()):
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
def join(i, irc):
    nickname = i.msg.get_nickname()
    args = i.msg.get_args()

    if not args:
        m = f"Usage: {i.msg.get_botcmd_prefix()}join <channel> [password]"
        return irc.out.notice(nickname, m)

    if not is_allowed(i, irc, nickname):
        m = "\x0304You are not authorized. Are you logged in?"
        return irc.out.notice(nickname, m)

    args = args.split(" ", 1)
    channel = args[0]
    try:
        password = args[1]
    except IndexError:
        password = ""

    if irc.conf.has_channel(channel):
        m = f"\x0303I am already in {channel}"
        return irc.out.notice(nickname, m)

    irc.conf.set_channel(channel, password)
    irc.out.join({channel: password})
    irc.out.notice(nickname, f"\x0303+ Joined {channel}")


def part(i, irc):
    nickname = i.msg.get_nickname()
    args = i.msg.get_args()

    if not args:
        m = f"Usage: {i.msg.get_botcmd_prefix()}part <channel> [message]"
        return irc.out.notice(nickname, m)

    args = args.split(" ", 1)
    channel = args[0]
    try:
        message = args[1]
    except IndexError:
        message = i.bot["conf"].get_quitmsg()

    if not irc.conf.has_channel(channel):
        m = f"\x0304I am not in {channel}"
        return irc.out.notice(nickname, m)

    if not is_allowed(i, irc, nickname, channel):
        m = f"\x0304You are not authorized. Are you an operator of {channel}?"
        return irc.out.notice(nickname, m)

    irc.conf.del_channel(channel)
    irc.out.part(channel, message)
    irc.out.notice(nickname, f"\x0303- Left {channel}")


def privmsg(i, irc):
    nickname = i.msg.get_nickname()
    args = i.msg.get_args()

    m = f"Usage: {i.msg.get_botcmd_prefix()}privmsg <channel> <message>"
    if not args:
        return irc.out.notice(nickname, m)

    args = args.split(" ", 1)
    if len(args) < 2:
        return irc.out.notice(nickname, m)

    channel = args[0]
    message = args[1]

    if not irc.conf.has_channel(channel):
        m = f"\x0304The bot has not joined the channel: {channel}"
        return irc.out.notice(nickname, m)

    if not is_allowed(i, irc, nickname, channel):
        m = f"\x0304You are not authorized. Are you an operator of {channel}?"
        return irc.out.notice(nickname, m)

    irc.privmsg(channel, message)
    irc.out.notice(nickname, "\x0303Message sent")


def notice(i, irc):
    nickname = i.msg.get_nickname()
    args = i.msg.get_args()

    m = f"Usage: {i.msg.get_botcmd_prefix()}notice <channel> <message>"
    if not args:
        return irc.out.notice(nickname, m)

    args = args.split(" ", 1)
    if len(args) < 2:
        return irc.out.notice(nickname, m)

    channel = args[0]
    message = args[1]

    if  not irc.conf.has_channel(channel):
        m = f"\x0304The bot has not joined the channel: {channel}"
        return irc.out.notice(nickname, m)

    if not is_allowed(i, irc, nickname, channel):
        m = f"\x0304You are not authorized. Are you an operator of {channel}?"
        return irc.out.notice(nickname, m)

    irc.out.notice(channel, message)
    irc.out.notice(nickname, "\x0303Message sent")


#
# User ACL
#
def acl_add(i, irc):
    nickname = i.msg.get_nickname()
    args = i.msg.get_args()
    prefix = i.msg.get_botcmd_prefix()

    modules = i.bot["modules"]
    conf = i.bot["conf"]

    m = (f"Usage: {prefix}acl_add "
         "<channel> <nickname>!<username>@<hostname> <duration> "
         f"<module1, ...> | See {prefix}admin_help for details.")

    if not args:
        return irc.out.notice(nickname, m)

    status, tokens = parse_uacl(args)

    if status == 1:  # Not enough args
        irc.out.notice(nickname, m)
        return
    elif status == 2:  # Invalid usermask
        m = f"\x0304Invalid usermask ``{tokens}'' given."
        irc.out.notice(nickname, m)
        return
    elif status == 3:  # Invalid duration
        m = f"\x0304Invalid duration ``{tokens}'' given."
        irc.out.notice(nickname, m)
        return
    elif status == 4: # Invalid modules
        m = f"\x0304Invalid modules ``{tokens}'' given."
        irc.out.notice(nickname, m)
        return

    t_channel = tokens["channel"]
    if not conf.has_channel(t_channel) and t_channel != '*':
        m = f"\x0304I am not in {t_channel}"
        irc.out.notice(nickname, m)
        return

    if t_channel == '*':
        if not is_allowed(i, irc, nickname):
            m = f"\x0304You are not authorized. Are you logged in?"
            return irc.out.notice(nickname, m)
    else:
        if not is_allowed(i, irc, nickname, t_channel):
            m = ("\x0304You are not authorized. "
                 f"Are you an operator of {t_channel}?")
            return irc.out.notice(nickname, m)

    t_modules = tokens["modules"]
    if t_modules != '*':
        for module_name in t_modules:
            if modmgmt.get_object_from_name(modules, module_name) is None:
                m = f"\x0304Module `{module_name}' not loaded"
                irc.out.notice(nickname, m)
                return

    conf.add_user_access_list(tokens)
    irc.out.notice(nickname, f"\x0303Mask added in the ACL")


def acl_del(i, irc):
    nickname = i.msg.get_nickname()
    args = i.msg.get_args()

    m = f"Usage: {i.msg.get_botcmd_prefix()}acl_del <mask ID>"

    if not args:
        return irc.out.notice(nickname, m)

    if len(args.split()) > 1:
        return irc.out.notice(nickname, m)

    try:
        index = int(args)
    except ValueError:
        return irc.out.notice(nickname, m)

    if not irc.conf.has_index_user_access_list(index):
        irc.out.notice(nickname, "\x0304 This mask does not exist")
        return

    irc.conf.del_user_access_list(index)
    m = f"\x0303Deleted mask {args} from the ACL"
    irc.out.notice(nickname, m)


def acl_list(i, irc):
    nickname = i.msg.get_nickname()

    uacl = irc.conf.get_user_access_list()
    if not uacl:
        irc.out.notice(nickname, "No masks in the ACL")
        return

    out = ""
    for index, mask in enumerate(uacl):
        out += ("{"
                f"{index}: {mask['channel']}"
                f" {mask['nick']}!{mask['user']}@{mask['host']}"
                f" {mask['timestamp']} {mask['modules']}"
                "}")

    irc.out.notice(nickname, out)


#
# Module Management
#
def mod_import(i, irc):
    nickname = i.msg.get_nickname()
    if not is_allowed(i, irc, nickname):
        m = f"\x0304You are not authorized. Are you logged in?"
        return irc.out.notice(nickname, m)

    # Reload the configuration file to see any user changes.
    i.bot["conf"].load()

    # Reimport the modules
    i.bot["modules"] = modmgmt.mod_import(i.bot)

    irc.out.notice(nickname, '\x0303Modules imported')


def mod_reload(i, irc):
    nickname = i.msg.get_nickname()
    if not is_allowed(i, irc, nickname):
        m = f"\x0304You are not authorized. Are you logged in?"
        return irc.out.notice(nickname, m)

    # Reload the modules
    i.bot["modules"] = modmgmt.reload_all(i.bot)

    irc.out.notice(nickname, '\x0303Modules reloaded')


def mod_whitelist_add(i, irc):
    nickname = i.msg.get_nickname()
    args = i.msg.get_args()
    prefix = i.msg.get_botcmd_prefix()

    modules = i.bot["modules"]
    conf = i.bot["conf"]

    m = f"Usage: {prefix}mod_whitelist_add <module> <channel>"
    if not args:
        return irc.out.notice(nickname, m)

    args = args.split(" ", 1)
    if len(args) < 2:
        return irc.out.notice(nickname, m)

    module = args[0]
    channel = args[1]

    if not conf.has_channel(channel):
        m = f"\x0304I am not in {channel}"
        return irc.out.notice(nickname, m)

    if not is_allowed(i, irc, nickname, channel):
        m = f"\x0304You are not authorized. Are you an operator of {channel}?"
        irc.out.notice(nickname, m)
        return

    if modmgmt.get_object_from_name(modules, module_name) is None:
        m = f"\x0304Error: Module ``{module_name}'' not loaded"
        return irc.out.notice(nickname, m)

    if not conf.is_allowed_module_whitelist(module):
        m = (f"\x0304The module: {module} has a blacklist set. "
             "Clear the blacklist and try again.")
        irc.out.notice(nickname, m)
        return

    if conf.has_channel_module_whitelist(module, channel):
        m = f"\x0304{channel} has already been added in {module}'s whitelist"
        irc.out.notice(nickname, m)
        return

    conf.add_channel_module_whitelist(module, channel)
    m = f"\x0303{channel} added in {module}'s whitelist"
    irc.out.notice(nickname, m)


def mod_blacklist_add(i, irc):
    nickname = i.msg.get_nickname()
    args = i.msg.get_args()
    prefix = i.msg.get_botcmd_prefix()

    modules = i.bot["modules"]
    conf = i.bot["conf"]

    m = f"Usage: {prefix}mod_blacklist_add <module> <channel>"
    if not args:
        return irc.out.notice(nickname, m)

    args = args.split(" ", 1)
    if len(args) < 2:
        return irc.out.notice(nickname, m)

    module = args[0]
    channel = args[1]

    if not conf.has_channel(channel):
        m = f"\x0304I am not in {channel}"
        return irc.out.notice(nickname, m)

    if not is_allowed(i, irc, nickname, channel):
        m = f"\x0304You are not authorized. Are you an operator of {channel}?"
        irc.out.notice(nickname, m)
        return

    if modmgmt.get_object_from_name(modules, module_name) is None:
        m = f"\x0304Error: Module ``{module_name}'' not loaded"
        return irc.out.notice(nickname, m)

    if not conf.is_allowed_module_blacklist(module):
        m = (f"\x0304The module: {module} has a whitelist set. "
             "Clear the whitelist and try again.")
        irc.out.notice(nickname, m)
        return

    if conf.has_channel_module_blacklist(module, channel):
        m = f"\x0304{channel} has already been added in {module}'s blacklist"
        irc.out.notice(nickname, m)
        return

    conf.add_channel_module_blacklist(module, channel)
    m = f"\x0303{channel} added in {module}'s blacklist"
    irc.out.notice(nickname, m)


def mod_whitelist_del(i, irc):
    nickname = i.msg.get_nickname()
    args = i.msg.get_args()
    prefix = i.msg.get_botcmd_prefix()

    m = f"Usage: {prefix}mod_whitelist_del <module> <channel>"
    if not args:
        return irc.out.notice(nickname, m)

    args = args.split(" ", 1)
    if len(args) < 2:
        return irc.out.notice(nickname, m)

    module = args[0]
    channel = args[1]

    if channel not in irc.conf.get_channels():
        m = f"\x0304The bot has not joined the channel: {channel}"
        return irc.out.notice(nickname, m)

    if not is_allowed(i, irc, nickname, channel):
        m = f"\x0304You are not authorized. Are you an operator of {channel}?"
        return irc.out.notice(nickname, m)

    if not irc.conf.has_channel_module_whitelist(module, channel):
        m = f"\x0304This channel has not been added in {module}'s whitelist"
        return irc.out.notice(nickname, m)

    irc.conf.del_channel_module_whitelist(module, channel)
    m = f"\x0303{channel} removed from {module}'s whitelist"
    irc.out.notice(nickname, m)


def mod_blacklist_del(i, irc):
    nickname = i.msg.get_nickname()
    args = i.msg.get_args()
    prefix = i.msg.get_botcmd_prefix()

    m = f"Usage: {prefix}mod_blacklist_del <module> <channel>"
    if not args:
        return irc.out.notice(nickname, m)

    args = args.split(" ", 1)
    if len(args) < 2:
        return irc.out.notice(nickname, m)

    module = args[0]
    channel = args[1]

    if channel not in irc.conf.get_channels():
        m = f"\x0304The bot has not joined the channel: {channel}"
        return irc.out.notice(nickname, m)

    if not is_allowed(i, irc, nickname, channel):
        m = f"\x0304You are not authorized. Are you an operator of {channel}?"
        return irc.out.notice(nickname, m)

    if not irc.conf.has_channel_module_blacklist(module, channel):
        m = f"\x0304This channel has not been added in {module}'s blacklist"
        return irc.out.notice(nickname, m)

    irc.conf.del_channel_module_blacklist(module, channel)
    m = f"\x0303{channel} removed from {module}'s blacklist"
    irc.out.notice(nickname, m)


def _module_wb_list_list(i, irc, channel=""):
    nickname = i.msg.get_nickname()

    wl = irc.conf.conf["irc"]["modules"]["whitelist"]
    bl = irc.conf.conf["irc"]["modules"]["blacklist"]

    wl_message = "\x0301,00WHITELIST\x0F :"
    if channel:
        wl_message += f" {channel} :"
    for module in wl:
        if not channel and wl[module]:
            wl_message += f" {module}: {wl[module]} /"
        else:
            if channel in wl[module]:
                wl_message += F" {module} /"

    bl_message = "\x0300,01BLACKLIST\x0F :"
    if channel:
        bl_message += f" {channel} :"
    for module in bl:
        if not channel and bl[module]:
            bl_message += f" {module}: {bl[module]} /"
        else:
            if channel in wl[module]:
                bl_message += F" {module} /"

    irc.out.notice(nickname, wl_message)
    irc.out.notice(nickname, bl_message)


def mod_list(i, irc):
    nickname = i.msg.get_nickname()
    args = i.msg.get_args().strip()
    args_len = len(args.split(" "))
    prefix = i.msg.get_botcmd_prefix()

    auth = is_allowed(i, irc, nickname)

    if not args and auth:
        _module_wb_list_list(i, irc)
    elif args_len == 1 and auth:
        _module_wb_list_list(i, irc, args)
    elif args_len == 1 and not auth:
        m = f"\x0304You are not authorized. Are you an operator of {args}?"
        irc.out.notice(nickname, m)
    else:
        m = (f"Usage: {prefix}mod_list <channel> | "
             "Bot owners can ommit the <channel> argument.")
        irc.out.notice(nickname, m)


def mod_global_prefix_set(i, irc):
    nickname = i.msg.get_nickname()
    args = i.msg.get_args().strip()
    args_len = len(args.split(" "))
    prefix = i.msg.get_botcmd_prefix()

    if not is_allowed(i, irc, nickname):
        m = f"\x0304You are not authorized. Are you logged in?"
        return irc.out.notice(nickname, m)

    m = f"Usage: {i.cmd_prefix}mod_global_prefix_set <prefix>"

    if len(args_len) != 1:
        irc.out.notice(nickname, m)
        return

    irc.conf.set_global_prefix(args)
    m = f"\x0303Changed the global_prefix to {args}"
    irc.out.notice(nickname, m)


def mod_channel_prefix_set(i, irc):
    nickname = i.msg.get_nickname()
    args = i.msg.get_args().strip()
    prefix = i.msg.get_botcmd_prefix()

    m = f"Usage: {prefix}mod_channel_prefix_set <channel> <prefix>"
    if not args:
        return irc.out.notice(nickname, m)

    args = args.split(" ", 1)
    if len(args) != 2:
        return irc.out.notice(i.nickname, m)

    channel = args[0]
    prefix = args[1]

    if channel not in irc.conf.get_channels():
        m = f"\x0304I am not in {channel}"
        return irc.out.notice(nickname, m)

    if not is_allowed(i, irc, nickname, channel):
        m = f"\x0304You are not authorized. Are you an operator of {channel}?"
        return irc.out.notice(nickname, m)

    irc.conf.set_channel_prefix(channel, prefix)
    m = (f"\x0303Changed the channel_prefix for {channel} to {prefix}")
    irc.out.notice(nickname, m)


#
# Help
#
def admin_help(i, irc):
    prefix = i.msg.get_botcmd_prefix()

    join = [
        f"Usage: {prefix}join <channel> [password]",
        " Permission: Owners",
        "Join a channel."
    ]
    part = [
        f"Usage: {prefix}part <channel> [message]",
        " Permission: Channel Operators",
        "Leave a channel. Channel Operators can only use this command on"
        " channels where they have operator privilages."
    ]
    privmsg = [
        f"Usage: {prefix}privmsg <channel> <message>",
        " Permission: Channel Operators",
        "Have the bot send a private message to a channel or a person. You"
        " must be an operator of the channel you want to send a private"
        " message to. Only bot owners can use this command to send messages to"
        " other users."
    ]
    notice = [
        f"Usage: {prefix}notice <channel> <message>",
        " Permission: Channel Operators",
        "Have the bot send a notice to a channel or a person. You must be an"
        " operator of the channel you want to send a notice to. Only bot"
        " owners can use this command to send notices to other users."
    ]
    acl_add = [
        f"Usage: {prefix}acl_add <channel> "
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
        f"Usage: {prefix}acl_del <mask ID>",
        " Permission: Channel Operators",
        "Remove a rule from the user access list using its ID. The ID can be"
        f" retrieved using the command: {prefix}acl_list. Note that the"
        " IDs might change everytime a rule is deleted. Users can only delete"
        " delete rules for channels where they have Operator rights. Rules"
        " that have their channel part set to '*' can only be deleted by the"
        " bot's owners."
    ]
    acl_list = [
        f"Usage: {prefix}acl_list",
        " Permission: Everyone",
        "Get a list of every rule set. Rules are numbered. This number is"
        " their current ID and can be used in the acl_del command."
    ]
    mod_import = [
        f"Usage: {prefix}mod_import",
        " Permission: Owners",
        "Import any new modules specified in the configuration file and reload"
        " the currently imported ones."
    ]
    mod_reload = [
        f"Usage: {prefix}mod_reload",
        " Permission: Owners",
        "Reload the currently imported modules."
    ]
    mod_whitelist_add = [
        f"Usage: {prefix}mod_whitelist_add <module> <channel>",
        " Permission: Channel Operators",
        "Add a channel to a module's whitelist. This will make the module only"
        " respond to the channels added in this whitelist. You cannot add a"
        " channel to a modules whitelist if a blacklist is already in place."
    ]
    mod_blacklist_add = [
        f"Usage: {prefix}mod_blacklist_add <module> <channel>",
        " Permission: Channel Operators",
        "Add a channel to a module's blacklist. This will make the module not"
        " respond to the channels added in this blacklist. You cannot add a"
        " channel to a modules blacklist if a whitelist is already in place."
    ]
    mod_whitelist_del = [
        f"Usage: {prefix}mod_whitelist_del <module> <channel>",
        " Permission: Channel Operators",
        "Delete a channel from a module's whitelist."
    ]
    mod_blacklist_del = [
        f"Usage: {prefix}mod_blacklist_del <module> <channel>",
        " Permission: Channel Operators",
        "Delete a channel from a module's blacklist."
    ]
    mod_list = [
        f"Usage: {prefix}mod_list <channel>",
        " Permission: Channel Operators",
        "Get a list of every module that has <channel> in its whitelist or"
        " blacklist. Bot owners can omit the <channel argument> and get a list"
        " of all channels that have been in a whitelist or a blacklist."
    ]
    mod_global_prefix_set = [
        f"Usage: {prefix}mod_global_prefix_set <prefix>",
        " Permission: Owners",
        "Set the default prefix used for commands. This is the character used"
        " before a command name. E.g.: .command  '.' is the prefix here."
    ]
    mod_channel_prefix_set = [
        f"Usage: {prefix}mod_channel_prefix_set <channel> <prefix>",
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
        "mod_reload": mod_reload,
        "mod_whitelist_add": mod_whitelist_add,
        "mod_blacklist_add": mod_blacklist_add,
        "mod_whitelist_del": mod_whitelist_del,
        "mod_blacklist_del": mod_blacklist_del,
        "mod_list": mod_list,
        "mod_global_prefix_set": mod_global_prefix_set,
        "mod_channel_prefix_set": mod_channel_prefix_set,
        "admin_help": admin_help
    }

    nickname = i.msg.get_nickname()
    args = i.msg.get_args().strip()
    prefix = i.msg.get_botcmd_prefix()

    try:
        cmd_help_list = help_d[args]
    except KeyError:
        avail_cmd = ""
        for cmd in help_d:
            avail_cmd += f"{cmd}, "
        avail_cmd = avail_cmd[:-3]
        m = f"Usage: {prefix}admin_help <admin command>"
        irc.out.notice(nickname, m)
        m = f"Available commands are: {avail_cmd}"
        irc.out.notice(nickname, m)
        return

    for line in cmd_help_list:
        irc.out.notice(nickname, line)


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
        "mod_reload": mod_reload,
        "mod_whitelist_add": mod_whitelist_add,
        "mod_blacklist_add": mod_blacklist_add,
        "mod_whitelist_del": mod_whitelist_del,
        "mod_blacklist_del": mod_blacklist_del,
        "mod_list": mod_list,
        "mod_global_prefix_set": mod_global_prefix_set,
        "mod_channel_prefix_set": mod_channel_prefix_set,
        "admin_help": admin_help
    }
    func_d[i.msg.get_botcmd()](i, irc)
