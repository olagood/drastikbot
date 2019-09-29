# coding=utf-8

# This file implements checks for user access list rules.

'''
Copyright (C) 2019 drastik.org

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


def _m_user(m, user):
    if m == user or m == "*":
        return True
    elif "*" == m[0] and m[1:] == user[-len(m[1:]):]:
        return True
    else:
        return False


def _m_host(m, hostmask):
    if m == hostmask or m == "*":
        return True
    elif "*" == m[0] and m[1:] == hostmask[-len(m[1:]):]:
        return True
    elif "*" == m[-1] and m[:-1] == hostmask[:len(m[:-1])]:
        return True
    else:
        return False


def _check_time(timestamp):
    if timestamp == 0:
        return True
    now = datetime.datetime.now(datetime.timezone.utc).timestamp()
    if timestamp > now:
        return True
    else:
        return False


def _check_module(m, module):
    if m == '*':
        return True
    ls = m.split(',')
    if module in ls:
        return True
    else:
        return False


def _is_banned(mask, channel, nick, user, hostmask, module):
        '''
        Check if a user is banned from using the bot.
        mask : is a mask following the following format:
                  channel nickname!username@hostmask time modules.
                  The mask allows for the * wildcard in frond of
                  the username and hostmask.

        '''
        tmp = mask.split(" ", 1)
        c = tmp[0]
        tmp = tmp[1].split("!", 1)
        n = tmp[0]
        tmp = tmp[1].split("@", 1)
        u = tmp[0]
        tmp = tmp[1].split(" ", 1)
        h = tmp[0]
        tmp = tmp[1].split(" ", 1)
        t = int(tmp[0])
        m = tmp[1]

        # Bans are not case sensitive
        if (c.lower() == channel.lower() or c == '*') \
           and (n.lower() == nick.lower() or n == '*') \
           and _m_user(u.lower(), user.lower()) and _check_time(t) \
           and _m_host(h, hostmask) \
           and _check_module(m, module):
            return True
        else:
            return False


def is_banned(user_acl, channel, nick, user, hostmask, module):
    for i in user_acl:
        if _is_banned(i, channel, nick, user, hostmask, module):
            return True
    return False


def is_expired(mask):
    tmp = mask.split(" ", 1)
    tmp = tmp[1].split("!", 1)
    tmp = tmp[1].split("@", 1)
    tmp = tmp[1].split(" ", 1)
    tmp = tmp[1].split(" ", 1)
    t = int(tmp[0])
    if t == 0:
        return False
    now = datetime.datetime.now(datetime.timezone.utc).timestamp()
    if t < now:
        return True
    else:
        return False
