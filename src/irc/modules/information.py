# coding=utf-8

# This is a core module for Drastikbot.
# It returns information about the bot to it's users.

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


class Module:
    def __init__(self):
        self.commands = ['bots', 'source']


def main(i, irc):
    if i.cmd == "bots":
        m = (f"\x0305,01drastikbot {irc.var.version}\x0F"
             " | \x0305Python 3.6\x0F"
             " | \x0305GNU AGPLv3 ONLY\x0F"
             " | \x0311http://drastik.org/drastikbot")
        irc.privmsg(i.channel, m)
    elif i.cmd == "source":
        if not i.msg_nocmd or i.msg_nocmd == irc.var.curr_nickname:
            m = ("\x0305,01drastikbot\x0F"
                 " : \x0311https://github.com/olagood/drastikbot\x0F"
                 " | \x0305,01Modules\x0F"
                 " : \x0311https://github.com/olagood/drastikbot_modules\x0F")
            irc.privmsg(i.channel, m)
