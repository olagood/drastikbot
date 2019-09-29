
#!/usr/bin/env python3
# coding=utf-8

# This is the initialization file used to start the bot.
# It parses command line arguments, verifies the state of the configuration.
# file and calls the main bot functions.

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

import os
import sys
import signal
import argparse
import traceback
from pathlib import Path

from toolbox import config_check
from dbot_tools import Logger
from irc.worker import Main

# Get the project's root directory
proj_path = os.path.dirname(os.path.abspath(__file__))


def print_banner():
    banner = [
        "---------------------------------------------------------------",
        " Drastikbot 2.1",
        "    An IRC bot focused on its extensibility and personalization",
        "",
        " License: GNU AGPLv3 only",
        " Drastikbot 2.1 comes WITHOUT ANY WARRANTY",
        ""
        " Welcome!",
        "---------------------------------------------------------------"
    ]
    for i in banner:
        print(i)


def parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--conf', nargs='?',
                        type=str, help='Specify the configuration directory')
    args = parser.parse_args()

    # Check if a configuration directory is given or use the default one
    # "~/.drastikbot"
    if args.conf:
        path = Path(args.conf)
        if not path.is_dir():
            try:
                path.mkdir(parents=True, exist_ok=False)
            except FileExistsError:
                sys.exit("[Error] Making configuration directory at"
                         f" '{args.conf}' failed. Another file with that name"
                         " already exists.")
        conf_dir = str(path.expanduser().resolve())
    else:
        path = Path('~/.drastikbot').expanduser()
        if not path.is_dir():
            try:
                path.mkdir(parents=True, exist_ok=False)
            except FileExistsError:
                sys.exit("[Error] Making configuration directory at"
                         " '~/.drastikbot' failed. Another file with that name"
                         " already exists.")
        conf_dir = str(path)

    config_check.config_check(conf_dir)
    logger = Logger(conf_dir, 'runtime.log')
    logger.info('\nStarting up...\n')
    return conf_dir


if __name__ == "__main__":
    print_banner()
    conf_dir = parser()
    c = Main(conf_dir, proj_path)
    try:
        signal.signal(signal.SIGINT, c.sigint_hdl)
        c.main()
    except Exception as e:
        logger = Logger(conf_dir, 'runtime.log')
        logger.debug(f'Exception on startIRC(): {e} {traceback.print_exc()}')
