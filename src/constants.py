# coding=utf-8

# A module to centralize all the constant values of the bot

'''
Copyright (C) 2021 drastik.org

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


from pathlib import Path


progname = "drastikbot"
version = "2.2.1"
codename = ""

# The default bot directory to use if the user does not specify one
botdir = "~/.drastikbot"

# The name of the log directory
logdir = "logs"

# The name of the configuration file
config = "config.json"


# Get the path to the configuration file as a pathlib Path object
def get_config_path(botdir):
    return Path(botdir, config).expanduser().resolve()


def get_log_dir(botdir):
    return Path(botdir, logdir).expanduser().resolve()


# Helper functions

# Get a pathlib Path object from the directory string
def get_directory_path(directory):
    return Path(directory).expanduser().resolve()


# IRCv3
ircv3_version = "301"
ircv3_req = ("sasl")
