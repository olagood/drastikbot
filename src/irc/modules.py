# coding=utf-8

# Methods for importing, reloading and calling drastikbot modules.
# Features for modules such as Variable Memory, SQLite databases,
# channel blacklist and whitelist checks and user access list checks
# are defined here.

'''
Copyright (C) 2017-2019 drastik.org

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
from pathlib import Path, PurePath
import importlib
import traceback
import inspect
import sqlite3
from dbot_tools import Config, Logger
from toolbox import user_acl


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
        else:
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


class Info:
    """
    This class is used for setting up message and runtime variables by
    Modules.info_prep() and is passed to the modules.
    """
    __slots__ = ['cmd', 'channel', 'nickname', 'username', 'hostname', 'msg',
                 'msg_nocmd', 'cmd_prefix', 'msgtype', 'is_pm', 'msg_raw',
                 'db', 'msg_ls', 'msg_prefix', 'cmd_ls', 'msg_full', 'modules',
                 'command_dict', 'auto_list', 'mod_import', 'blacklist',
                 'whitelist', 'msg_params', 'varget', 'varset']


class Modules:
    def __init__(self, irc):
        self.irc = irc
        self.cd = self.irc.var.cd
        self.log = Logger(self.cd, 'modules.log')
        self.varmem = VariableMemory()

        self.modules = {}   # {Module Name : Module Callable}

        self.msgtype_dict = {}  # {msgtype: [module1, ...]}
        self.auto_list = []  # [module1, ...]
        self.startup_list = []  # [module1, ...]
        self.command_dict = {}  # {command1: module}
        # Databases #
        self.dbmem = sqlite3.connect(':memory:', check_same_thread=False)
        self.dbdisk = sqlite3.connect('{}/drastikbot.db'.format(self.cd),
                                      check_same_thread=False)
        self.mod_settings = {}  # {Module Name : {setting : value}}

    def mod_imp_prep(self, module_dir, auto=False):
        '''
        Search a directory for modules, check if they are listed in the config
        file and return a list of the modules.
        If 'auto' is True load all the modules without checking the config
        file (used for core modules needed for the bot's operation).
        '''
        path = Path(module_dir)
        load = Config(self.cd).read()['irc']['modules']['load']
        if not path.is_dir():
            # Check if the module directory exists under the
            # configuration directory and make it otherwise.
            path.mkdir(exist_ok=True)
            self.log.info(' - Module directory created at: {}'
                          .format(module_dir))
        # Append the module directory in the sys.path variable
        sys.path.append(module_dir)
        files = [f for f in path.iterdir() if Path(
            PurePath(module_dir).joinpath(f)).is_file()]
        modimp_list = []
        for f in files:
            suffix = PurePath(f).suffix
            prefix = PurePath(f).stem
            if suffix == '.py':
                if auto:
                    modimp_list.append(prefix)
                elif prefix in load:
                    modimp_list.append(prefix)
        return modimp_list

    def mod_import(self):
        """
        Import modules specified in the configuration file.
        Check for values specified in the Module() class of every module and
        set the variables declared in __init__() for later use.
        """
        self.log.info('\n> Loading Modules:\n')

        importlib.invalidate_caches()

        modimp_list = []
        module_dir = self.cd + '/modules'
        modimp_list.extend(self.mod_imp_prep(module_dir))
        module_dir = self.irc.var.proj_path + '/irc/modules'
        modimp_list.extend(self.mod_imp_prep(module_dir, auto=True))

        # Empty variabled from previous import:
        self.modules = {}  # {Module Name : Module Callable}
        self.msgtype_dict = {}  # {msgtype: [module1, ...]}
        self.auto_list = []  # [module1, ...]
        self.startup_list = []  # [module1, ...]
        self.command_dict = {}  # {command1: module}

        for m in modimp_list:
            try:
                modimp = importlib.import_module(m)
                # Dictionary with the module name and it's callable
                self.modules[m] = modimp
                # Read the module's "Module()" class to
                # get the required runtime information,
                # such as: commands, sysmode
                try:
                    mod = modimp.Module()
                except AttributeError:
                    self.log.info(f'<!> Module "{m}" does not have a Module() '
                                  'class and was not loaded.')

                commands = [c for c in getattr(mod, 'commands', [])]
                for c in commands:
                    if c in self.command_dict:
                        self.log.info(f'<!> Command "{c}" is already used by '
                                      f'"{self.command_dict[c]}.py", but is '
                                      f'also requested by "{m}.py".')
                        sys.exit(1)
                    self.command_dict[c] = m
                msgtypes = [m.upper() for m in getattr(
                    mod, 'msgtypes', ['PRIVMSG'])]
                for i in msgtypes:
                    self.msgtype_dict.setdefault(i, []).append(m)
                if getattr(mod, 'auto', False):
                    self.auto_list.append(m)
                if getattr(mod, 'startup', False):
                    self.startup_list.append(m)

                self.log.info('> Loaded module: {}'.format(m))
            except Exception:
                self.log.debug(f'<!> Module "{m}" failed to load: '
                               f'\n{traceback.format_exc()}')

    def mod_reload(self):
        '''
        Reload the already imported modules.
        WARNING: Changes in the Module() class are not reloaded using this
        method. Reimport the modules (with self.mod_import()) to do that.
        '''
        for value in self.modules.values():
            importlib.reload(value)

    def blacklist(self, module, channel):
        '''
        Read the configuration file and get the blacklist for the given module.
        [returns]
            True : if the channel is in the blacklist
            False: if the channel is not in the blacklist or if the blacklist
                   is empty
        '''
        try:
            blacklist = self.irc.var.modules_obj['blacklist'][module]
        except KeyError as e:
            if e.args[0] == module:
                self.irc.var.modules_obj['blacklist'].update({module: []})
            return False
        if not blacklist:
            return False
        elif channel in blacklist:
            return True
        else:
            return False

    def whitelist(self, module, channel):
        '''
        Read the configuration file and check if the channel is in the
        blacklist of the given module.
        [returns]
            True : if the channel is in the module's whitelist or if the
                   whitelist is empty and
            False: if the whitelist is not empty and the channel is not in it.
        '''
        try:
            whitelist = self.irc.var.modules_obj['whitelist'][module]
        except KeyError as e:
            if e.args[0] == module:
                self.irc.var.modules_obj['whitelist'].update({module: []})
            return True
        if not whitelist:
            return True
        elif channel in whitelist:
            return True
        else:
            return False

    def info_prep(self, msg):
        """
        Set values in the Info() class and return that class.

        --Notes:
        i.cmd :: The module command without the prefix.
                 Values are set by mod_main() before calling the module.
                 In "Auto" modules this will remain as an empty string.
        i.msg :: Instead of setting the msg.msg value, we set msg.params,
                 to achieve a better looking API. Instead "i.msg_full" is
                 set to msg.msg
        i.msg_params :: It is the same as i.msg, we use this to match the
                        RFC's terminology.
        """
        i = Info()
        i.cmd = ''
        i.channel = msg.channel
        i.nickname = msg.nickname
        i.username = msg.username
        i.hostname = msg.hostname
        i.msg_raw = msg.msg_raw
        i.msg_full = msg.msg
        i.msg = msg.params
        i.msg_nocmd = msg.params_nocmd
        i.msg_ls = msg.msg_ls
        i.msg_prefix = msg.prefix
        i.msg_params = msg.params
        i.cmd_ls = msg.cmd_ls
        i.cmd_prefix = msg.chn_prefix
        i.msgtype = msg.msgtype
        i.is_pm = i.channel == i.nickname
        i.db = [self.dbmem, self.dbdisk]
        i.varset = self.varmem.varset
        i.varget = self.varmem.varget
        i.modules = self.modules
        i.command_dict = self.command_dict
        i.auto_list = self.auto_list
        i.blacklist = self.blacklist
        i.whitelist = self.whitelist
        i.mod_import = self.mod_import
        return i

    def mod_main(self, irc, msg, command):
        def cmd_modules():
            try:
                module = self.command_dict[command[1:]]
            except KeyError:
                return
            if self.blacklist(module, i.channel):
                return
            if not self.whitelist(module, i.channel):
                return
            if user_acl.is_banned(self.irc.var.user_acl, i.channel, i.nickname,
                                  i.username, i.hostname, module):
                return
            if module in md:
                # We set i.cmd to the command's name.
                i.cmd = command[1:]
                try:
                    self.modules[module].main(*args)
                except Exception:
                    self.log.debug(f'<!> Module "{module}" exitted with error:'
                                   f'\n{traceback.format_exc()}')

        self.mod_reload()  # Reload the bot's modules.
        i = self.info_prep(msg)
        args = (i, irc)

        try:
            md = self.msgtype_dict[msg.msgtype]
        except KeyError:
            # No modules use this message type, return.
            return

        if command[:1] == i.cmd_prefix:
            cmd_modules()

        for m in list(set(self.auto_list).intersection(md)):
            if self.blacklist(m, i.channel):
                continue
            if not self.whitelist(m, i.channel):
                continue
            if user_acl.is_banned(self.irc.var.user_acl, i.channel, i.nickname,
                                  i.username, i.hostname, m):
                continue
            try:
                # We set i.cmd to False to indicate that it's an auto call.
                i.cmd = ""
                self.modules[m].main(*args)
            except Exception:
                self.log.debug(f'<!> Module "{m}" exitted with error: '
                               f'\n{traceback.format_exc()}')

    def mod_startup(self, irc):
        '''
        Run modules configured with the "self.startup = True" option.
        The bot doesn't manage the modules after they get started.
        This could be problematic for modules that are blocking and so they
        should periodically check the bot's connection state (e.g. by checking
        the value of "irc.var.conn_state") and handle a possible disconnect.
        The bot's whitelist/blacklist is not being taken into account.
        The "msgtype" and "cmd" passed to the modules is "STARTUP".
        The "info" tuple is perfectly matched by blank strings.
        '''
        def info_prep_startup():
            '''
            Special use of the Info class that includes only the variables
            available at startup.
            '''
            i = Info()
            i.cmd = ''
            i.msgtype = "STARTUP"  # Indicate that this is a startup call.
            i.db = [self.dbmem, self.dbdisk]
            i.varget = self.varmem.varget
            i.varset = self.varmem.varset
            i.modules = self.modules
            i.mod_import = self.mod_import
            return i

        self.mod_reload()  # Reload the bot's modules.
        i = info_prep_startup()
        args = (i, irc)

        for m in self.startup_list:
            try:
                # We set i.cmd to False to indicate that it's an auto call.
                i.cmd = ""
                self.modules[m].main(*args)
            except Exception:
                self.log.debug(f'<!> Module "{m}" exitted with error: '
                               f'\n{traceback.format_exc()}')
