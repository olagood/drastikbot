#!/usr/bin/env python3
# coding=utf-8

# Common tools used by the bot and it's modules.
# Tools: - text_fix: decode message and remove whitespace
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
import sys
from pathlib import Path


def text_fix(line):
    if not isinstance(line, str):
        line = line.decode('utf8', errors='ignore')

    # Remove "\r\n" and all whitespace.
    #    line = line.replace("\\r", "").replace("\\n", "")
    #    line = line.replace("\r", "").replace("\n", "")
    line = ''.join(line.splitlines())
    return line


def p_truncate(text, whole, percent, ellipsis=False):
    if not isinstance(text, str):
        raise TypeError("'text' must be str, not bytes")
        return
    t = text.encode('utf-8')
    lim = int((whole * percent) / 100)
    if not len(t) > lim:
        return t.decode('utf8', errors='ignore')
    e = b'...'
    if ellipsis:
        t = t[:lim + len(e)].rsplit(b' ', 1)[0] + e
    else:
        t = t[:lim].rsplit(b' ', 1)[0]
    return t.decode('utf8', errors='ignore')


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
            log_dir = conf_dir + '/logs/'
            self.log_dir = log_dir
        if not Path(log_dir).exists():
            Path(log_dir).mkdir(parents=True, exist_ok=True)
        self.log_file = Path('{}/{}'.format(log_dir, log_filename))
        try:
            self.log_mode = config['sys']['log_level'].lower()
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
                np = (self.log_dir + self.log_file.stem +
                      str(n) + "".join(self.log_file.suffixes))
                rotate_p = Path(np)
                if rotate_p.exists():
                    n += 1
                else:
                    self.log_file.rename(rotate_p)
                    break

    def log_write(self, msg, line, debug=False):
        with open(str(self.log_file), 'a+') as log:
            log.write(line + '\n')
        if not debug:
            print(msg)
        else:
            print(line)
        self.log_rotate()

    def info(self, msg):
        if self.log_mode == 'info' or self.log_mode == 'debug':
            line = '{} - INFO - {}'.format(
                datetime.datetime.now(), msg)
            self.log_write(msg, line)

    def debug(self, msg):
        if self.log_mode == 'debug':
            caller_name = sys._getframe(1).f_code.co_name
            line = f'{datetime.datetime.now()} - DEBUG - {caller_name} - {msg}'
            self.log_write(msg, line, debug=True)
