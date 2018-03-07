#!/usr/bin/env python3
# coding=utf-8

# This file parses command line arguments and starts the bot.

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
import argparse
import traceback
from pathlib import Path

from dbot_tools import Logger
from irc.worker import Main


def parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--conf', nargs='?',
                        type=str, help='Specify the configuration directory')
    args = parser.parse_args()
    if args.conf:
        # Check if a configuration directory is given
        # or use the default one "~/drastikbot".
        path = Path(args.conf)
        if not path.is_dir():
            sys.exit("[Error] Config directory does not exist.")
        conf_dir = str(path.expanduser().resolve())
    else:
        path = Path('~/.drastikbot').expanduser()
        if not path.is_dir():
            sys.exit("[Error] Config directory does not exist.")
        else:
            conf_dir = str(path)

    logger = Logger(conf_dir, 'runtime.log')
    logger.info('\nDrastikbot v2\n')
    startIRC(conf_dir)


def startIRC(conf_dir):
    c = Main(conf_dir)
    try:
        c.main()
    except Exception as e:
        Logger(conf_dir, 'runtime.log').debug('Exception on startIRC(): {}'
                                              .format(e))
        print(e, traceback.print_exc())


parser()
