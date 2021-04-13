# coding=utf-8

# This module replies to PING messages from the server


'''
Copyright (C) 2020 drastik.org

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


class Module:
    def __init__(self):
        self.irc_commands = ['PING']


def main(i, irc):
    m = " ".join(i.params)
    irc.send(("PONG", m))
