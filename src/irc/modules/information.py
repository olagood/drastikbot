# coding=utf-8

# This is a core module for Drastikbot.
# It returns information about the bot to it's users.

'''
Copyright (C) 2019, 2021 drastik.org

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

import constants


class Module:
    bot_commands = ["bots", "source"]


def bots(i, irc):
    m = (f"\x0305,01drastikbot {constants.version}\x0F"
         " | \x0305Python 3.8\x0F"
         " | \x0305GNU AGPLv3\x0F"
         " | \x0311http://drastik.org/drastikbot")
    irc.out.notice(i.msg.get_msgtarget(), m)


def source(i, irc):
    args = i.msg.get_args()
    if not args or args.strip() == irc.curr_nickname:
        m = ("\x0305,01drastikbot\x0F"
             " : \x0311https://github.com/olagood/drastikbot\x0F"
             " | \x0305,01Modules\x0F"
             " : \x0311https://github.com/olagood/drastikbot_modules\x0F")
        irc.out.notice(i.msg.get_msgtarget(), m)


def main(i, irc):
    if i.msg.is_botcmd("bots"):
        bots(i, irc)
    elif i.msg.is_botcmd("source"):
        source(i, irc)
