#!/usr/bin/env python3
# coding=utf-8

# Common tools used by the bot and it's modules.
# Tools: - text_fix: decode message and remove whitespace
#        - Message : split irc message strings
#        - Config  : config file reader and writer
#        - Logger  : Logger functions

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

import datetime
import json
from pathlib import Path


def text_fix(line):
    try:
        line = line.decode('utf8', errors='ignore')
    except Exception:
        # Catch UnicodeDecode errors and silently ignore them.
            pass
    # Remove "\r\n" and all whitespace.
    line = " ".join(line.split())
    return line


class Message:
    def __init__(self, msg_raw):
        self.msg_raw = msg_raw

    def msg_handler(self):
        self.msg = text_fix(self.msg_raw)
        print(self.msg)
        # Split the message in [Prefix Command] and [Params]
        msg_sp = self.msg.split(" :", 1)
        # Split [Prefix Command] in [Prefix] [Command]
        prefcmd_sp = msg_sp[0].split(" ", 1)
        # Remove ":" from the prefix
        self.prefix = prefcmd_sp[0][1:]
        # Split the irc commands in a list
        try:
            self.cmd_ls = prefcmd_sp[1].split()
        except IndexError:
            self.cmd_ls = prefcmd_sp[0].split()
        # Get the params
        try:
            self.params = msg_sp[1]
        except IndexError:
            self.params = ''

    def prefix_extract(self):
        try:
            prefix_list = self.prefix.split('!', 1)
            nickname = prefix_list[0]
            username = prefix_list[1].split('@', 1)[0]
            hostname = prefix_list[1].split('@', 1)[1]
            return (nickname, username, hostname)
        except IndexError:
            return (nickname, '', '')

    def module_args_prep(self, irc):
        user_info = self.prefix_extract()
        try:
            channel = self.cmd_ls[1]
        except IndexError:
            channel = ''
        if channel == irc.var.curr_nickname:
            channel = user_info[0]
        try:
            self.params_nocmd = self.params.split(' ', 1)[1].strip()
        except IndexError:
            self.params_nocmd = ''
        try:
            chn_prefix = irc.var.mod_chn_prefix[channel]
        except KeyError:
            chn_prefix = irc.var.mod_glb_prefix
        return (channel, user_info, (self.params, self.params_nocmd),
                chn_prefix, self.msg_raw)


class Config:
    """
    The Config class provides easy reading and writing to the
    bot's configuration file.
    conf_dir : should be the configuration directory.
    """
    def __init__(self, conf_dir):
        self.config_file = '{}/config.json'.format(conf_dir)

    def read(self):
            with open(self.config_file, 'r') as f:
                return json.load(f)

    def write(self, value):
        """
        value : must be the whole configuration and not just a
        setting, because the config file's contents are being
        replaced with 'value'
        """
        with open(self.config_file, 'w') as f:
            json.dump(value, f, indent=4)


class Logger:
    """
    This class provides minimal logging functionality.
    It supports log rotation and two logging states: INFO, DEBUG.
    - Todo:
    - add gzip compression of rotated logs
    - IF PROBLEMS OCCURE: make it thread safe
    """
    def __init__(self, conf_dir, log_filename):
        config = Config(conf_dir).read()
        try:
            log_dir = config['sys']['log_dir']
        except KeyError:
            log_dir = conf_dir + '/logs'
        if not Path(log_dir).exists():
            Path(log_dir).mkdir(parents=True, exist_ok=True)
        self.log_file = Path('{}/{}'.format(log_dir, log_filename))
        try:
            self.log_mode = config['sys']['log_mode'].lower()
        except KeyError:
            self.log_mode = 'info'
        try:
            self.log_size = config['sys']['log_size'].lower()
        except KeyError:
            self.log_size = 5 * 1000000

    def log_rotate(self):
        current_log_size = self.log_file.stat().st_size
        if current_log_size > self.log_size:
            while True:
                n = 1
                rotate_p = Path(self.log_file.stem + n + "".join(
                    self.log_file.suffixes))
                if rotate_p.exists():
                    n += 1
                else:
                    self.log_file.rename(rotate_p)
                    break

    def log_write(self, msg, line):
        with open(str(self.log_file), 'a+') as log:
            log.write(line + '\n')
        print(msg)
        self.log_rotate()

    def info(self, msg):
        if self.log_mode == ('info' or 'debug'):
            line = '{} - INFO - {}'.format(
                datetime.datetime.now(), msg)
            self.log_write(msg, line)

    def debug(self, msg):
        if self.log_mode == 'debug':
            getframe = 'sys._getframe({}).f_code.co_name'
            caller_name = getframe.format(2)
            line = '{} - DEBUG - {} - {}'.format(
                datetime.datetime.now(), caller_name, msg)
            self.log_write(msg, line)
