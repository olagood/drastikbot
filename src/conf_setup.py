# coding=utf-8

# Build the configuration file with interactive user input

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


def verify(conf):
    if "sys" not in conf:
        return "sys"
    if "log_level" not in conf["sys"]:
        return "sys:log_level"
    if "irc" not in conf:
        return "irc"
    if "owners" not in conf["irc"]:
        return "irc:owners"
    if "connection" not in conf["irc"]:
        return "irc:connection"
    if "channels" not in conf["irc"]:
        return "irc:channels"
    if "modules" not in conf["irc"]:
        return "irc:modules"
    if "load" not in conf["irc"]["modules"]:
        return "irc:modules:load"
    if "global_prefix" not in conf["irc"]["modules"]:
        return "irc:modules:global_prefix"
    if "channel_prefix" not in conf["irc"]["modules"]:
        return "irc:modules:channel_prefix"
    if "blacklist" not in conf["irc"]["modules"]:
        return "irc:modules:blacklist"
    if "whitelist" not in conf["irc"]["modules"]:
        return "irc:modules:whitelist"
    if "user_acl" not in conf["irc"]:
        return "irc:user_acl"

    return 0  # Verification passed


def interactive_verify(conf):
    dispatch = {
        "sys": lambda c: c.update({"sys": {}}),
        "sys:log_level": lambda c: c["sys"].update({"log_level": "info"}),
        "irc": lambda c: c.update({"irc": {}}),
        "irc:owners": irc_owners,
        "irc:connection": irc_connection,
        "irc:channels": irc_channels,
        "irc:modules": lambda c: c["irc"].update({"modules": {}}),
        "irc:modules:load": irc_modules_load,
        "irc:modules:global_prefix": irc_modules_global_prefix,
        "irc:modules:channel_prefix": lambda c: c["irc"]["modules"].update({
            "channel_prefix": {}}),
        "irc:modules:blacklist": lambda c: c["irc"]["modules"].update({
            "blacklist": {}}),
        "irc:modules:whitelist": lambda c: c["irc"]["modules"].update({
            "whitelist": {}}),
        "irc:user_acl": lambda c: c["irc"]["user_acl"].update([])
    }

    i = conf.verify()
    while i != 0:
        dispatch[i](conf.conf)
        conf.save()
        i = conf.verify()


def irc_owners(c):
    print("""
Owner setup:
Insert a comma seperated list of the bot owners' IRC nicknames.
The nicknames must be registered with nickserv.""")
    o = input("> ")
    o.replace(" ", "")
    ls = o.split(",")
    c["irc"].update({"owners": ls})


def irc_connection(c):
    print("\nIRC connection setup:")
    network = input("Hostname [chat.freenode.net]: ").replace(" ", "")
    if not network:
        network = "chat.freenode.net"

    while True:
        port = input("Port [6697]: ").replace(" ", "")
        if not port:
            port = 6697
            break
        else:
            try:
                port = int(port)
                break
            except ValueError:
                print("- Invalid port given.")

    while True:
        ssl = input("SSL: (true, false) [true]").replace(" ", "").lower()
        if not ssl or ssl == "true":
            ssl = True
            break
        elif ssl == "false":
            ssl = False
            break
        print("- Invalid SSL setting.")

    net_password = input("Network password: ")

    nickname = input("Nickname [drastikbot]: ").replace(" ", "")
    if not nickname:
        nickname = "drastikbot"

    username = input("Username [drastikbot]: ").replace(" ", "")
    if not username:
        username = "drastikbot"

    realname = input("Realname [drastikbot]: ")
    if not realname:
        realname = "drastikbot"

    m = "Authentication method (nickserv, sasl) [sasl]: "
    while (1):
        auth_method = input(m).replace(" ", "").lower()
        if not auth_method or auth_method == "sasl":
            auth_method = "sasl"
            break
        elif auth_method == "nickserv":
            break
        print("- Invalid authentication method.")

    auth_password = input("Authentication Password []: ")
    c["irc"].update({"connection": {"network": network,
                                    "port": port,
                                    "ssl": ssl,
                                    "net_password": net_password,
                                    "nickname": nickname,
                                    "username": username,
                                    "realname": realname,
                                    "authentication": auth_method,
                                    "auth_password": auth_password}})


def irc_channels(c):
    print("\nChannel setup:")
    channel_d = {}
    cm = "Channel name (with #) (RET to exit): "
    pm = "Channel password (RET if there is none): "
    while True:
        channel = input(cm).replace(" ", "")
        if not channel:
            break
        password = input(pm)
        channel_d[channel] = password

    if not self.conf["irc"]["channels"]:
        return "irc:channels=empty"

    c["irc"].update({"channels": {}})
    c["irc"]["channels"].update(channel_d)


def irc_modules_load(c):
    m = """
Module setup:
No modules will be loaded. Edit the configuration file to load modules.
Edit the section  "irc.modules.load"  with the modules you  want to use
and restart the bot."""
    print(m)
    c["irc"]["modules"].update({"load": []})


def irc_modules_global_prefix(c):
    while True:
        prefix = input("Default command prefix [.]: ").replace(" ", "")
        if not prefix:
            prefix = "."
            break
        if len(prefix) == 1:
            break
        print("- Invalid prefix. It must be a single character.")

    c["irc"]["modules"].update({"global_prefix": prefix})
