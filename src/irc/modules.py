# coding=utf-8

# Methods for importing, reloading and calling drastikbot modules.
# Features for modules such as Variable Memory, SQLite databases.

'''
Copyright (C) 2017-2019, 2021 drastik.org

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

import sys
from pathlib import Path
import importlib
import traceback
import inspect
import collections
import sqlite3

from dbot_tools import Logger
from toolbox import user_acl


# Immutables. They are to be initialized by init once.
log = None
var_memory = None
db_memory = None
db_disk = None


def init(bot):
    global log
    log = Logger(bot["loglevel"], Path(bot["logdir"], "modules.log"))

    global var_memory
    var_memory = VariableMemory()

    global db_memory
    db_memory = sqlite3.connect(':memory:', check_same_thread=False)

    global db_disk
    path = f"{bot['botdir']}/drastikbot.db"
    db_disk = sqlite3.connect(path, check_same_thread=False)


def _new_module_state():
    return {
        "modules_d": {},  # {module_object: module_path}
        "startup_l": [],  # [module_object]
        "irc_command_d": {},  # {irc_command: [module_object]}
        "bot_command_d": {}  # {bot_command: [module_object]}
    }


def candidates_from_path(bot, path, force=False):
    """Search a directory for modules to import. Only the modules whose
    names are found in the configuration file are returned.

    :param bot_state: A dictionary that holds runtime data.
    :param path: The directory to search.
    :param force: If True return every module without checking the config.
    :returns: An iterator of paths to modules that should be imported.
    """
    load = bot["conf"].get_modules_load()

    # Check if the module directory exists under the configuration
    # directory and make it otherwise.
    if not path.is_dir():
        path.mkdir(exist_ok=True)
        log.info(f"- Module directory created at: {path}")

    # Check if the module directory is in the Python sys.path
    if str(path) not in sys.path:
        sys.path.append(str(path))

    # Return .py files (whose names are in `load' if `force' is False)
    return filter(lambda x: x.is_file() and x.suffix == ".py"
                  and (force or x.stem in load),
                  path.iterdir())


def read_module_class(s, path, module_object):
    s["modules_d"][module_object] = path

    # Module(): Check if the module has such a class
    try:
        module_class = module_object.Module()
    except AttributeError:
        log.debug(f"Module() class not found for: ``{path.stem}''")
        return s

    # Module(): Handle bot_commands
    for bot_c in getattr(module_class, "bot_commands", []):
        s["bot_command_d"].setdefault(bot_c, []).append(module_object)

    # Deprecated 2.2
    # Module(): Handle commands (legacy usage of bot_commands)
    for bot_c in getattr(module_class, "commands", []):
        s["bot_command_d"].setdefault(bot_c, []).append(module_object)

    # Module(): Handle irc_commands
    for irc_c in getattr(module_class, "irc_commands", []):
        s["irc_command_d"].setdefault(irc_c, []).append(module_object)

    # Module(): Handle startup
    if getattr(module_class, "startup", False):
        s["startup_l"].append(module_object)

    return s


def import_from_list(modules, log_import=True, state=None):
    """Imports every module in ``modules'' and returns the mod_state"""
    if state is None:
        s = _new_module_state()
    else:
        s = state

    importlib.invalidate_caches()

    for path in modules:
        try:
            module_object = importlib.import_module(str(path.stem))
        except Exception:
            tc = traceback.format_exc()
            log.debug(f"- Module load exception:``{path}''\n{tc}")
            continue

        read_module_class(s, path, module_object)

        if log_import:
            log.info(f"| Loaded module: {path.stem}")

    return s


def reload_all(s):
    old_modules_d = s["modules_d"]
    s = _new_module_state()

    for module_object in old_modules_d:
        importlib.reload(module_object)
        path = old_modules_d[module_object]
        read_module_class(s, path, module_object)

    return s


def mod_import(bot):
    # System modules: Required core modules
    path = Path(bot["program_path"], "irc/modules")
    import_l = candidates_from_path(bot, path, force=True)
    s = import_from_list(import_l, log_import=bot["devmode"])

    # User modules: Third party modules provided by the user
    path = Path(bot["botdir"], "modules")
    import_l = candidates_from_path(bot, path)
    s = import_from_list(import_l, state=s)

    return s


BotCommandData = collections.namedtuple(
    "BotCommandData", [
        "cmd", "nickname", "username", "hostname", "msg_raw", "msg_full",
        "msg", "msg_nocmd", "msg_ls", "cmd_prefix", "msgtype", "db",
        "bot_command", "message", "prefix", "command", "params", "is_pm",
        "channel", "db_memory", "db_disk", "varset", "varget", "modules_state",
        "bot", "mod_import", "mod_reload"
    ])


def bot_command_data(s, bot, irc, message, bot_command):
    message, prefix, command, params = message
    is_pm = params[0] != irc.curr_nickname

    msg_nocmd = params[-1].split(" ", 1)
    if len(msg_nocmd) == 2:
        msg_nocmd = msg_nocmd[1]
    else:
        msg_nocmd = msg_nocmd[0]

    return BotCommandData(
        cmd=bot_command[1:],  # Deprecated 2.2
        nickname=prefix["nickname"],  # Deprecated 2.2
        username=prefix["user"],  # Deprecated 2.2
        hostname=prefix["host"],  # Deprecated 2.2
        msg_raw=message,  # Deprecated 2.2
        msg_full=message.decode("utf-8", errors="ignore"),  # Deprecated 2.2
        msg=params[-1],  # Deprecated 2.2
        msg_nocmd=msg_nocmd,  # Deprecated 2.2
        msg_ls=msg_nocmd.split(" "),  # Deprecated 2.2
        # msg_prefix has been removed in 2.2 without a deprecation period
        # msg_params has been removed in 2.2 without a deprecation period
        # cmd_ls has been removed in 2.2 without a deprecation period
        cmd_prefix=bot_command[:1],  # Deprecated 2.2
        msgtype=command,  # Deprecated 2.2
        db=[db_memory, db_disk],  # Deprecated 2.2
        # modules has been removed in 2.2 without a deprecation period
        # command_dict has been removed in 2.2 without a deprecation period
        # auto_list has been removed in 2.2 without a deprecation period
        # blacklist has been removed in 2.2 without a deprecation period
        # whitelist has been removed in 2.2 without a deprecation period
        bot_command=bot_command,
        message=message,
        prefix=prefix,
        command=command,
        params=params,
        is_pm=is_pm,
        channel=params[0] if is_pm else prefix["nickname"],
        db_memory=db_memory,
        db_disk=db_disk,
        varset=var_memory.varset,
        varget=var_memory.varget,
        modules_state=s,
        bot=bot,
        mod_import=mod_import,
        mod_reload=reload_all
    )


def bot_command_dispatch(s, bot, irc, message, bot_command):
    data = bot_command_data(s, bot, irc, message, bot_command)
    nickname = data.prefix["nickname"]
    user = data.prefix["user"]
    host = data.prefix["host"]
    channel = data.channel

    for module_object in s["bot_command_d"].get(data.cmd, []):
        module_name = s["modules_d"][module_object].stem

        # Is the channel blacklisted/whitelisted ?
        if not bot["conf"].check_channel_module_access(module_name, channel):
            continue

        # Is the user restricted by the user access list ?
        uacl = bot["conf"].get_user_access_list()
        if user_acl.is_banned(uacl, channel, nickname,
                              user, host, module_name):
            continue

        try:
            module_object.main(data, irc)
        except Exception:
            tc = traceback.format_exc()
            log.debug(f"Module ``{module_name}'' error:\n{tc}")


IrcCommandData = collections.namedtuple(
    "IrcCommandData", [
        "message", "prefix", "command", "params",
        "db_memory", "db_disk", "module", "mod_import", "mod_reload",
        "bot", "varget", "varset"
    ])


def irc_command_data(s, bot, message):
    return IrcCommandData(
        message=message[0],
        prefix=message[1],
        command=message[2],
        params=message[3],
        db_memory=db_memory,
        db_disk=db_disk,
        varget=var_memory.varget,
        varset=var_memory.varset,
        module=s,
        bot=bot,
        mod_import=mod_import,
        mod_reload=reload_all
    )


def irc_command_dispatch(s, bot, irc, message):
    data = irc_command_data(s, bot, message)

    for module_object in s["irc_command_d"].get(data.command, []):
        module_name = s["modules_d"][module_object].stem

        if data.command == "PRIVMSG":
            channel = data.params[0]
            nickname = data.prefix["nickname"]
            user = data.prefix["user"]
            host = data.prefix["host"]

            # Is the channel blacklisted/whitelisted ?
            if not bot["conf"].check_channel_module_access(
                    module_name, channel):
                continue

            # Is the user restricted by the user access list ?
            uacl = bot["conf"].get_user_access_list()
            if user_acl.is_banned(uacl, channel, nickname,
                                  user, host, module_name):
                continue

        try:
            module_object.main(data, irc)
        except Exception:
            tc = traceback.format_exc()
            log.debug(f"Module ``{module_name}'' error:\n{tc}")


def dispatch(s, bot, irc, message):
    raw, prefix, command, params = message

    irc_command_dispatch(s, bot, irc, message)

    if command == "PRIVMSG":
        channel = params[0]
        bot_command = params[-1].split(" ", 1)[0]
        bot_command_prefix = bot_command[:1]
        if bot["conf"].get_channel_prefix(channel) == bot_command_prefix:
            bot_command_dispatch(s, bot, irc, message, bot_command)


def startup(s, bot, irc):
    '''
    Run modules configured with the "self.startup = True" option.
    The bot doesn't manage the modules after they get started.
    This could be problematic for modules that are blocking and so they
    should periodically check the bot's connection bot_state (e.g. by checking
    the value of "irc.conn_bot_state") and handle a possible disconnect.
    The bot's whitelist/blacklist is not being taken into account.
    '''
    data = irc_command_data(s, bot, ("", "", "__STARTUP", ""))

    for module_object in s["startup_l"]:
        try:
            module_object.main(data, irc)
        except Exception:
            module_name = s["modules_d"][module_object]
            tc = traceback.format_exc()
            log.debug(f"- Module ``{module_name}'' error:\n{tc}")


class VariableMemory:
    def varset(self, name, value):
        """
        Set a variable to be kept in the bot's memory.

        'name' is the name of the variable.
        'value' is the variable's value.

        The name of the actual saved variable is not the actual name given, but
        <calling module's name>_<'name'>. e.g sed_msgdict.
        This is to allow different modules have any variable and make accessing
        those variables easier.
        """
        # Get the caller module's name:
        frm = inspect.stack()[1]
        mod = inspect.getmodule(frm[0]).__name__
        # Check if it's a call from this module. (modules.py)
        if mod == __loader__.name:
            return

        name = f"{mod}_{name}"
        setattr(self, name, value)

    def varget(self, name, defval=False, raw=False):
        """
        Get a variable from the bot's memory.
        'name' is the name of the variable.
        'defval' is the default to set if no variable is already set.
        'raw' if True will not append the module's name in frond of 'name'.
              This is to access variables from other modules.

        If both 'defval' and 'raw' are non False but the variable cannon be
        found an AttributeError is raised.
        """
        if not raw:
            # Get the caller module's name:
            frm = inspect.stack()[1]
            mod = inspect.getmodule(frm[0]).__name__
            # Check if it's a call from this module. (modules.py)
            if mod == __loader__.name:
                return
            name = f"{mod}_{name}"

        try:
            return getattr(self, name)
        except AttributeError:
            if defval and not raw:
                self.varset(name, defval)
                return defval
            else:
                raise AttributeError(f"'{name}' has no value set. "
                                     "Try passing a default value"
                                     " or set 'raw=False'")
