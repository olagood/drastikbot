# coding=utf-8

# Parse messages recieved by the IRC server and pack them in
# variables suitable for usage by the bot's functions.

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

import sys, timeit

class Message:
    """
    Class used to parse IRC messages sent by the server and turn them into
    objects useable by the bot and its modules.
    """
    def __init__(self, msg_raw):
        self.msg_raw = msg_raw
        # Decode utf-8 and remove CR and LR from 'self.msg_raw'.
        # self.msg = text_fix(self.msg_raw)  # Prefer this if errors happen.
        self.msg = self.msg_raw.decode('utf8', errors='ignore')
        self.msg = ''.join(self.msg.splitlines())
        # Split the message in a list
        self.msg_ls = self.msg.split()
        # Split the message in [Prefix Command] and [Params]
        msg_sp = self.msg.split(" :", 1)
        # Split [Prefix Command] in [Prefix] [Command]
        prefcmd_sp = msg_sp[0].split(" ", 1)
        # Remove ":" from the prefix
        self.prefix = prefcmd_sp[0][1:]
        # Split the irc commands in a list
        try:
            self.cmd_ls = prefcmd_sp[1].split()
        except IndexError:
            self.cmd_ls = prefcmd_sp[0].split()
        # Get the params
        try:
            self.params = msg_sp[1]
        except IndexError:
            self.params = ''
        # Get the msgtype (PRIVMSG, NOTICE, JOIN)
        self.msgtype = self.cmd_ls[0]
        # Get user information.
        try:
            prefix_list = self.prefix.split('!', 1)
            self.nickname = prefix_list[0]
            self.username = prefix_list[1].split('@', 1)[0]
            self.hostname = prefix_list[1].split('@', 1)[1]
        except IndexError:
            # self.nickname = prefix_list[0]  # Should be set in the try:
            self.username = ''
            self.hostname = ''

    def channel_prep(self, irc):
        """
        The channel is placed in different positions depending on the IRC
        command sent. For parsing we use a dictionary with the various
        commands and we call the matching sub-function to parse the channel.
        """
        def _join():
            return self.msg_ls[2].lstrip(":")

        def _353():
            return self.cmd_ls[3]

        def _privmsg():
            return self.cmd_ls[1]

        def __rest():
            '''
            This is used for msgtypes not specified in the 'self.channel'
            dict below.
            '''
            try:
                c = self.cmd_ls[1]
            except IndexError:
                c = ""
            return c

        self.channel = {
            'JOIN': _join,
            '353': _353,
            'PRIVMSG': _privmsg
            }.get(self.msgtype, __rest)()

        if self.channel == irc.curr_nickname:
            self.channel = self.nickname

        try:
            self.params_nocmd = self.params.split(' ', 1)[1].strip()
        except IndexError:
            self.params_nocmd = ''
        try:
            self.chn_prefix = irc.state["conf"].get_channel_prefix(
                self.channel)
        except KeyError:
            self.chn_prefix = irc.state["conf"].get_global_prefix()
