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

import os
import sys
import signal
import argparse
import traceback
from pathlib import Path

from dbot_tools import Logger
from irc.worker import Main

# Get the project's root directory
proj_path = os.path.dirname(os.path.abspath(__file__))


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
    logger.info('\nDrastikbot: Starting...\n')
    return conf_dir


if __name__ == "__main__":
    conf_dir = parser()
    c = Main(conf_dir, proj_path)
    try:
        signal.signal(signal.SIGINT, c.sigint_hdl)
        c.main()
    except Exception as e:
        logger = Logger(conf_dir, 'runtime.log')
        logger.debug(f'Exception on startIRC(): {e} {traceback.print_exc()}')
