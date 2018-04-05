#!/usr/bin/env python3
# coding=utf-8

# Methods for importing, reloading and calling drastikbot modules.

'''
Copyright (C) 2018 drastik.org

This file is part of drastikbot.

Drastikbot is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

Drastikbot is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Drastikbot. If not, see <http://www.gnu.org/licenses/>.
'''

import sys
from pathlib import Path, PurePath
import importlib
import traceback
import sqlite3
from dbot_tools import Config, Logger


class Info:
    __slots__ = ['cmd', 'channel', 'nickname', 'username', 'hostname', 'msg',
                 'msg_nocmd', 'cmd_prefix', 'msgtype', 'msg_raw', 'db', 'mem']


class Modules:
    def __init__(self, conf_dir, irc):
        self.cd = conf_dir
        self.irc = irc
        self.log = Logger(self.cd, 'modules.log')

        self.modules = {}   # {Module Name : Module Callable}
        self.cmd_dict = {}  # {Module Name :
        #                      {commands: [], auto: True,
        #                       sysmode: True, msgtypes: []}}
        # Databases #
        self.dbmem = sqlite3.connect(':memory:', check_same_thread=False)
        self.dbdisk = sqlite3.connect('{}/drastikbot.db'.format(self.cd),
                                      check_same_thread=False)
        self.mod_settings = {}  # {Module Name : {setting : value}}

    def mod_import(self):
        # import modules specified in the configuration file
        self.log.info('\n - Loading Modules:\n')
        importlib.invalidate_caches()
        module_dir = self.cd + '/modules'
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
            if (suffix == '.py') and (prefix in load):
                modimp_list.append(prefix)
        for m in modimp_list:
            try:
                modimp = importlib.import_module(m)
                # Dictionary with the module name and it's callable
                self.modules[m] = modimp
                # Read the module's "Module()" class to
                # get the required runtime information,
                # such as: commands, sysmode
                mod = modimp.Module()
                msgtypes = [m.upper() for m in getattr(
                    mod, 'msgtypes', ['PRIVMSG'])]
                self.cmd_dict[m] = {'auto':     getattr(mod, 'auto', False),
                                    'sysmode':  getattr(mod, 'system', False),
                                    'startup':  getattr(mod, 'startup', False),
                                    'commands': getattr(mod, 'commands', []),
                                    'msgtypes': msgtypes}
                self.log.info('- Loaded module: {}'.format(m))
            except Exception as e:
                print(e)
                self.log.debug('-- Module "{}" failed to load: '
                               'See modules.log for details'.format(m))

    def mod_reload(self):
        '''
        Reload the already imported modules.
        WARNING: Changes in the module() class are
        not being taken into account by the bot
        when reloaded using this method.
        '''
        for value in self.modules.values():
            importlib.reload(value)

    def blacklist(self, module, channel):
        '''
        Read the configuration file and get the
        blacklist for the given module.
        Then return False if the module is not blacklisted
        in the given channel or True if it is blacklisted.
        '''
        try:
            blacklist = self.irc.var.modules_obj[
                'settings'][module]['blacklist']
        except KeyError as e:
            if e.args[0] == 'settings':
                self.irc.var.modules_obj.update(
                    {'settings': {module: {'blacklist': []}}})
            elif e.args[0] == module:
                self.irc.var.modules_obj['settings'].update(
                    {module: {'blacklist': []}})
            elif e.args[0] == 'blacklist':
                self.irc.var.modules_obj['settings'][module].update(
                    {'blacklist': []})
            return False
        if not blacklist:
            return False
        elif channel in blacklist:
            return True
        else:
            return False

    def whitelist(self, module, channel):
        '''
        Read the configuration file and get the
        whitelist for the given module.
        Then return True if the module is not whitelisted
        in the given channel and the whitelist exists
        or False if it is whitelisted or the whitelist does
        not exist.
        '''
        try:
            whitelist = self.irc.var.modules_obj[
                'settings'][module]['whitelist']
        except KeyError as e:
            if e.args[0] == 'settings':
                self.irc.var.modules_obj.update(
                    {'settings': {module: {'whitelist': []}}})
            elif e.args[0] == module:
                self.irc.var.modules_obj['settings'].update(
                    {module: {'whitelist': []}})
            elif e.args[0] == 'whitelist':
                self.irc.var.modules_obj['settings'][module].update(
                    {'whitelist': []})
            return False
        if not whitelist:
            return True
        elif channel in whitelist:
            return True
        else:
            return False

    def info_prep(self, info, db, msgtype):
        i = Info()
        i.cmd = ''
        i.channel = info[0]
        i.nickname = info[1][0]
        i.username = info[1][1]
        i.hostname = info[1][2]
        i.msg = info[2][0]
        i.msg_nocmd = info[2][1]
        i.cmd_prefix = info[3]
        i.msgtype = msgtype
        i.msg_raw = info[4]
        i.db = db
        i.mem = False
        return i

    def mod_init(self, cmd, cmdset, command, args):
        if cmdset['auto']:
            try:
                self.modules[cmd].main(*args)
            except Exception:
                self.log.debug(' -- Module "{}" exitted with error: {}'
                               .format(cmd, traceback.print_exc()))
        for c in cmdset['commands']:
            try:
                if command == args[0].cmd_prefix + c:
                    args[0].cmd = c  # Set the i.cmd variable
                    self.modules[cmd].main(*args)
            except Exception:
                self.log.debug(' -- Module "{}" exitted with error: {}'
                               .format(cmd, traceback.print_exc()))

    def mod_main(self, irc, info, command, msgtype):
        self.mod_reload()
        db = [self.dbmem, self.dbdisk]
        for cmd, cmdset in self.cmd_dict.items():
            if self.blacklist(cmd, info[0]):
                continue
            if not self.whitelist(cmd, info[0]):
                continue
            if msgtype not in cmdset['msgtypes']:
                continue
            i = self.info_prep(info, db, msgtype)
            if cmdset['sysmode']:
                self.mod_init(cmd, cmdset, command,
                              (i, irc, [self.modules, self.mod_import]))
            else:
                self.mod_init(cmd, cmdset, command, (i, irc))

    def mod_startup(self, irc):
        '''
        Run modules configured with the "self.startup = True"
        option.
        The bot doesn't manage the modules after they get started.
        This could be problematic for module that are blocking and
        so they should periodically check the bot's connection
        state (e.g. by checking the value of "irc.var.conn_state") and
        handle a possible disconnect.
        The bot's whitelist/blacklist is not being taken into account.
        The "msgtype" and "cmd" passed to the modules is "STARTUP".
        The "info" tuple is perfectly matched by blank strings.
        '''
        self.mod_reload()
        db = [self.dbmem, self.dbdisk]
        info = ("", ("", "", ""), ("", ""), "", "")
        for cmd, cmdset in self.cmd_dict.items():
            if not cmdset['startup']:
                continue
            i = self.info_prep(info, db, "STARTUP")
            if cmdset['sysmode']:
                self.mod_init(cmd, cmdset, "STARTUP",
                              (i, irc, [self.modules, self.mod_import]))
            else:
                self.mod_init(cmd, cmdset, "STARTUP", (i, irc))
