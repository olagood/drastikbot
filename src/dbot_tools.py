# coding=utf-8

# Common tools used by the bot and it's modules.
# Tools: - text_fix: decode message and remove whitespace
#        - p_truncate: Truncate text messages by percentage
#        - Logger  : Logger functions

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
import json
import sys
from pathlib import Path
from dbotconf import Configuration


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


class Logger:
    """
    This class provides minimal logging functionality.
    It supports two logging modes: INFO, DEBUG.
    """

    def __init__(self, level, logdir, logname):
        self.log_mode = level
        self.log_dir = logdir

        if not Path(log_dir).exists():
            Path(log_dir).mkdir(parents=True, exist_ok=True)

        self.log_file = Path('{}/{}'.format(log_dir, log_filename))

    def log_write(self, msg, line):
        with open(self.log_file, 'a+') as log:
            log.write(line + '\n')

    def info(self, msg):
        if self.log_mode == 'info' or self.log_mode == 'debug':
            dt = datetime.datetime.now()
            line = f"{dt} - INFO - {msg}"
            print(msg)
            self.log_write(msg, line)

    def debug(self, msg):
        if self.log_mode == 'debug':
            caller_name = sys._getframe(1).f_code.co_name
            dt = datetime.datetime.now()
            line = f"{dt} - DEBUG - {caller_name} - {msg}"
            print(line)
            self.log_write(msg, line)
