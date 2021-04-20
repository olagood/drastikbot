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
import importlib
import traceback
import inspect
import collections
import sqlite3
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

import irc.message as parser
from dbot_tools import Logger


# Constants. Initialized with the module.
irc_command_tpool = ThreadPoolExecutor()

# Variables. They are to be initialized by init once.
log = None
var_memory = None
db_memory = None
db_disk = None


# ====================================================================
# Initialization
# ====================================================================

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


# ====================================================================
# Module state
# ====================================================================

def _new_module_state():
    return {
        "modules_d": {},  # {module_object: module_path}
        "startup_l": [],  # [module_object]
        "irc_command_d": {},  # {irc_command: [module_object]}
        "bot_command_d": {}  # {bot_command: [module_object]}
    }


def get_object_from_name(bot, module_name):
    return _get_object_from_name(bot["modules"], module_name)


def _get_object_from_name(s, module_name):
    for module_object, module_path in s["modules_d"].items():
        if module_path.stem == module_name:
            return module_object
    return None


# ====================================================================
# Module importing, loading and reloading functions
# ====================================================================

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
        module_class = module_object.Module
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

    print("")  # Pretty stdout

    return s


def reload_all(bot):
    old_modules_d = bot["modules"]["modules_d"]
    s = _new_module_state()

    for module_object in old_modules_d:
        path = old_modules_d[module_object]
        try:
            importlib.reload(module_object)
        except Exception:
            # Print the exeption but add the old references in the state,
            # so that we can retry reloading it the next time.
            # It's only added in ``modules_d'' because we don't want to
            # make the module look like it works (because of the old
            # reference) and confuse the developer.
            tc = traceback.format_exc()
            log.debug(f"- Module load exception:``{path}''\n{tc}")
            s["modules_d"][module_object] = path
            continue

        read_module_class(s, path, module_object)

    return s


def mod_import(bot):
    # System modules: Required core modules
    path = Path(bot["program_path"], "irc/modules")
    import_l = candidates_from_path(bot, path, force=True)
    s = import_from_list(import_l, log_import=bot["devmode"])

    # User modules: Third party modules provided by the user
    for path in bot["conf"].get_modules_paths():
        path = Path(path).expanduser()
        import_l = candidates_from_path(bot, path)
        s = import_from_list(import_l, state=s)

    return s


# ====================================================================
# Message dispatchers
# ====================================================================

CallbackData = collections.namedtuple(
    "CallbackData", [
        "msg", "db_memory", "db_disk", "bot", "varget", "varset"
    ]
)


def callback_data(bot, msg):
    return CallbackData(
        msg=msg,
        db_memory=db_memory,
        db_disk=db_disk,
        varget=var_memory.varget,
        varset=var_memory.varset,
        bot=bot
    )


def mod_call(module_name, fn, /, *args, **kwargs):
    try:
        fn(*args, **kwargs)
    except Exception:
        tc = traceback.format_exc()
        log.debug(f"Module ``{module_name}'' error:\n{tc}")


def bot_command_dispatch(s, bot, irc, msg):
    conf = bot["conf"]
    data = callback_data(bot, msg)
    channel = msg.get_msgtarget()

    for module_object in s["bot_command_d"].get(msg.get_botcmd(), []):
        module_name = s["modules_d"][module_object].stem

        # Is the channel blacklisted/whitelisted ?
        if not conf.check_channel_module_access(module_name, channel):
            continue

        # Is the user restricted by the user access list ?
        if conf.is_banned_user_access_list(msg, module_name):
            continue

        mod_call(module_name, module_object.main, data, irc)


def bot_command_maybe(s, bot, irc, msg):
    if msg.get_command() != "PRIVMSG":
        return

    prefix = msg.get_botcmd_prefix()
    receiver = msg.get_msgtarget()

    if bot["conf"].get_channel_prefix(receiver) == prefix:
        bot_command_dispatch(s, bot, irc, msg)


def irc_command_dispatch(s, bot, irc, msg):
    conf = bot["conf"]
    data = callback_data(bot, msg)

    for module_object in s["irc_command_d"].get(msg.get_command(), []):
        module_name = s["modules_d"][module_object].stem

        if msg.get_command() == "PRIVMSG":
            channel = msg.get_msgtarget()

            # Is the channel blacklisted/whitelisted ?
            if not conf.check_channel_module_access(module_name, channel):
                continue

            # Is the user restricted by the user access list ?
            if conf.is_banned_user_access_list(msg, module_name):
                continue

        irc_command_tpool.submit(
            mod_call, module_name, module_object.main, data, irc)


def dispatch(bot, irc, msg):
    s = bot["modules"]
    irc_command_tpool.submit(irc_command_dispatch, s, bot, irc, msg)

    try:
        bot_command_maybe(s, bot, irc, msg)
    except Exception:
        tc = traceback.format_exc()
        log.debug(f"- Module ``maybe'' error:\n{tc}")


StartupMsg = collections.namedtuple("StartupMsg", ["get_command"])


def startup(bot, irc):
    '''
    Run modules configured with the "self.startup = True" option.
    The bot doesn't manage the modules after they get started.
    This could be problematic for modules that are blocking and so they
    should periodically check the bot's connection bot_state (e.g. by checking
    the value of "irc.conn_bot_state") and handle a possible disconnect.
    The bot's whitelist/blacklist is not being taken into account.
    '''
    s = bot["modules"]
    data = callback_data(bot, StartupMsg(lambda: "__STARTUP"))

    for module_object in s["startup_l"]:
        try:
            module_object.main(data, irc)
        except Exception:
            module_name = s["modules_d"][module_object]
            tc = traceback.format_exc()
            log.debug(f"- Module ``{module_name}'' error:\n{tc}")


# ====================================================================
# VariableMemory: maintain state between module calls
# ====================================================================

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
            if defval is not False and not raw:
                self.varset(name, defval)
                return defval
            else:
                m = (f"``{name}'' has no value set. Try passing a default"
                     " value or set ``raw=False''")
                raise AttributeError(m)
