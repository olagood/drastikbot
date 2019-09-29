# coding=utf-8

# Check the bot's configuration file, verify it, add any missing enties
# either by requesting user input or by setting default values.

'''
Copyright (C) 2019 drastik.org

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

from pathlib import Path

from dbot_tools import Logger, Config
from toolbox import user_acl


def _check_irc(conf_dir):
    log = Logger(conf_dir, 'runtime.log')
    c = Config(conf_dir).read()
    if "irc" not in c:
        c.update({"irc": {}})
        Config(conf_dir).write(c)
        log.info("<*> Configuration: created 'irc' section.")


def _check_owners(conf_dir):
    log = Logger(conf_dir, 'runtime.log')
    c = Config(conf_dir).read()
    if "owners" not in c["irc"]:
        print("\nSetting up the bot's owners. Please enter a comma seperated "
              "list of their IRC nicknames. The nicknames must be "
              "registered with nickserv.")
        o = input("> ")
        o.replace(" ", "")
        ls = o.split(",")
        c["irc"].update({"owners": ls})
        Config(conf_dir).write(c)
        log.info("<*> Configuration: setting up 'irc.owners' ...")


def _check_connection(conf_dir):
    log = Logger(conf_dir, 'runtime.log')
    c = Config(conf_dir).read()
    if "connection" not in c["irc"]:
        print("\nSetting up the IRC server connection details.")

        network = input("Hostname [chat.freenode.net]: ").replace(" ", "")
        if not network:
            network = "chat.freenode.net"

        port = input("Port [6697]: ").replace(" ", "")
        if not port:
            port = 6697
        else:
            port = int(port)

        while (1):
            ssl = input("SSL: (true, false) [true]").replace(" ", "").lower()
            if not ssl or ssl == "true":
                ssl = True
                break
            elif ssl == "false":
                ssl = False
                break
            print("\nError Invalid input. Try again.\n")

        net_password = input("Network Password []: ")

        nickname = input("Nickname [drastikbot]: ").replace(" ", "")
        if not nickname:
            nickname = "drastikbot"

        username = input("Username [drastikbot]: ").replace(" ", "")
        if not username:
            username = "drastikbot"

        realname = input("Realname [drastikbot2]: ")
        if not realname:
            realname = "drastikbot2"

        while (1):
            authentication = input("Authentication mode (nickserv, sasl)"
                                   " [sasl]: ").replace(" ", "").lower()
            if not authentication or authentication == "sasl":
                authentication = "sasl"
                break
            elif authentication == "nickserv":
                break
            print("\nError Invalid input. Try again.\n")

        auth_password = input("Authentication Password []: ")
        c["irc"].update({"connection": {"network": network,
                                        "port": port,
                                        "ssl": ssl,
                                        "net_password": net_password,
                                        "nickname": nickname,
                                        "username": username,
                                        "realname": realname,
                                        "authentication": authentication,
                                        "auth_password": auth_password}})
        Config(conf_dir).write(c)
        log.info("<*> Configuration: setting up 'irc.connection' ...")


def _check_channels(conf_dir):
    log = Logger(conf_dir, 'runtime.log')
    c = Config(conf_dir).read()
    if "channels" not in c["irc"]:
        c["irc"].update({"channels": {}})
    if not c["irc"]["channels"]:
        chan_list = {}
        print("\nEnter the channels you want to join.")
        while True:
            ch = input("Channel (with #) (leave empty to exit): ")
            ch.replace(" ", "")
            if not ch:
                break
            ps = input("Password (leave empty if there is none): ")
            chan_list[ch] = ps
        c["irc"]["channels"].update(chan_list)
        Config(conf_dir).write(c)
        log.info("<*> Configuration: setting up 'irc.channels' ...")


def _check_modules(conf_dir):
    log = Logger(conf_dir, 'runtime.log')
    c = Config(conf_dir).read()
    conf_w = Config(conf_dir).write
    if "modules" not in c["irc"]:
        c["irc"].update({"modules": {}})
        log.info("<*> Configuration: 'irc.modules' not found. "
                 "Creating...")
    if "load" not in c["irc"]["modules"]:
        c["irc"]["modules"].update({"load": []})
        log.info("<*> Configuration: 'irc.modules.load' not found. "
                 "Creating...")
    if not c["irc"]["modules"]["load"]:
        log.info("<*> Configuration: 'irc.modules.load' is empty. "
                 "No modules will be loaded. Edit the configuration file's "
                 "'irc.modules.load' section with the modules you want "
                 "to use and restart the bot.")
    if "global_prefix" not in c["irc"]["modules"]:
        c["irc"]["modules"].update({"global_prefix": "."})
        log.info("<*> Configuration: 'irc.modules.global_prefix' not found. "
                 "Setting default prefix '.'")
    if "channel_prefix" not in c["irc"]["modules"]:
        c["irc"]["modules"].update({"channel_prefix": "."})
        log.info("<*> Configuration: creating "
                 "'irc.modules.channel_prefix' ...")
    if "blacklist" not in c["irc"]["modules"]:
        c["irc"]["modules"].update({"blacklist": {}})
        log.info("<*> Configuration: creating 'irc.modules.blacklist' ...")
    if "whitelist" not in c["irc"]["modules"]:
        c["irc"]["modules"].update({"whitelist": {}})
        log.info("<*> Configuration: creating 'irc.modules.whitelist' ...")
    conf_w(c)


def _check_user_acl(conf_dir):
    log = Logger(conf_dir, 'runtime.log')
    c = Config(conf_dir).read()
    if "user_acl" not in c["irc"]:
        c["irc"].update({"user_acl": []})
        log.info("<*> Configuration: setting up 'irc.user_acl' ...")
    for i in c["irc"]["user_acl"]:
        if user_acl.is_expired(i):
            c["irc"]["user_acl"].remove(i)
            log.info(f"<*> Configuration: removed expired mask: '{i}' from "
                     "'irc.user_acl' ...")
    Config(conf_dir).write(c)


def _check_sys(conf_dir):
    #log = Logger(conf_dir, 'runtime.log')
    c = Config(conf_dir).read()
    if "sys" not in c:
        c.update({"sys": {}})
        #log.info("<*> Configuration: created 'sys' section.")
    if "log_level" not in c["sys"]:
        c["sys"].update({"log_level": "info"})
        #log.info("<*> Configuration: created 'sys.log_level'.")
    Config(conf_dir).write(c)


def _check_exists(conf_dir):
    p = Path(f"{conf_dir}/config.json")
    if p.is_file():
        return
    with open(p, "w") as f:
        f.write("{}")


def config_check(conf_dir):
    _check_exists(conf_dir)
    _check_sys(conf_dir)
    _check_irc(conf_dir)
    _check_owners(conf_dir)
    _check_connection(conf_dir)
    _check_channels(conf_dir)
    _check_modules(conf_dir)
