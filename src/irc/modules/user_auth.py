# coding=utf-8

# This is a core module for Drastikbot.
# It provides functions for checking a user's authentication status.

'''
Copyright (C) 2018-2019 drastik.org

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

import time


class Module:
    def __init__(self):
        self.msgtypes = ['NOTICE']
        self.commands = ['whois']
        self.auto = True


def user_auth(i, irc, nickname, timeout=10):
    to = time.time() + timeout
    irc.privmsg("NickServ", f"ACC {nickname}")
    irc.privmsg("NickServ", f"STATUS {nickname}")
    i.varset(nickname, "_pending")
    while True:
        time.sleep(.5)
        auth = i.varget(nickname)
        if auth != "_pending":
            return auth
        if time.time() > to:
            return False


def nickserv_handler(i):
    ls = i.msg_params.split()
    if ls[1] == 'ACC' and i.varget(ls[0]) == "_pending":
        if '3' in i.msg_params:
            i.varset(ls[0], True)
        else:
            i.varset(ls[0], False)
    elif ls[0] == 'STATUS' and i.varget(ls[1]) == "_pending":
        if '3' in i.msg_params:
            i.varset(ls[1], True)
        else:
            i.varset(ls[1], False)


def main(i, irc):
    if i.nickname == 'NickServ':
        nickserv_handler(i)
