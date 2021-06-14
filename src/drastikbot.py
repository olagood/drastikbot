
#!/usr/bin/env python3
# coding=utf-8

# This is the initialization file used to start the bot.
# It parses command line arguments, verifies the state of the configuration.
# file and calls the main bot functions.

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

import os
import sys
import argparse
import traceback
from pathlib import Path

import constants
import conf_setup
from dbotconf import Configuration
from dbot_tools import Logger
import irc.worker


def print_banner():
    print("""
---------------------------------------------------------------
 Drastikbot 2.2
    An IRC bot focused on its extensibility and personalization

 License: GNU AGPLv3
 Drastikbot 2.2 comes WITHOUT ANY WARRANTY

 Welcome!
---------------------------------------------------------------
""")



def ensure_dir_exists(path):
    if path.is_dir():
        return  # The configuration directory exists
    try:
        path.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        m = ("[Error] Unable to make the configuration directory at"
             f" '{path}'. A file with that name already exists.")
        print(m, file=sys.stderr)
        sys.exit(1)


def cli_arg_state():
    desc = f"{constants.progname} {constants.version} ({constants.codename})"
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument("-c", "--confdir", nargs="?", type=str,
                        default=constants.botdir,
                        help="Specify the configuration directory")
    parser.add_argument("-d", "--dev", action="store_true",
                        help="Start the bot in development mode")
    args = parser.parse_args()

    botdir = constants.get_directory_path(args.confdir)
    devmode = args.dev

    ensure_dir_exists(botdir)

    conf = Configuration(constants.get_config_path(botdir))
    # Verify the config file and prompt the user for input
    conf_setup.interactive_verify(conf)

    loglevel = conf.get_sys_log_level()
    if devmode:
        loglevel = "debug"

    logdir = conf.get_sys_log_dir()
    if logdir is None:
        logdir = constants.get_log_dir(botdir)

    runlog = Logger(loglevel, Path(logdir, "runtime.log"))

    # Get the project's root directory
    program_path = os.path.dirname(os.path.abspath(__file__))

    state = {
        "program_path": program_path,
        "botdir": botdir,
        "conf": conf,
        "devmode": devmode,
        "loglevel": loglevel,
        "logdir": logdir,
        "runlog": runlog,
        "modules": None
    }
    return state


if __name__ == "__main__":
    print_banner()
    state = cli_arg_state()
    try:
        irc.worker.run(state)
    except Exception as e:
        logger = state["runlog"]
        logger.debug(f'Startup error:\n {e} {traceback.print_exc()}')
