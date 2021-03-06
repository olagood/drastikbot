# coding=utf-8

# This file provides methods for connecting to and sending message
# to an IRC server. Additionally it keeps track of every vital
# runtime variable the bot needs for its connection to the IRC server
# and the management of its features.

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

import socket
import ssl
import time
import traceback

import dbot_tools


class Output:
    def __init__(self, irc):
        self.irc = irc

    def away(self, msg=''):
        self.irc.send('AWAY', msg)

    def invite(self, nick, channel):
        self.irc.send(('INVITE', nick, channel))

    def join(self, channels):
        for key, value in channels.items():
            self.irc.send(('JOIN', key, value))

    def kick(self, channel, nick, msg):
        self.irc.send(('KICK', channel, nick, msg))

    def names(self, channels, server=""):
        m = ["NAMES"]
        m.extend(channels)
        m.append(server)
        self.irc.send(m)

    def nick(self, nick):
        self.irc.send(('NICK', nick))

    def notice(self, target, msg):
        self.irc.send(('NOTICE', target), msg)

    def part(self, channel, msg):
        self.irc.send(('PART', channel), msg)

    def pong(self, server1, server2=""):
        if server2:
            self.irc.send(("PONG", server1, server2))
        else:
            self.irc.send(("PONG", server1))

    def privmsg(self, target, msg):
        self.irc.send(('PRIVMSG', target), msg)

    def quit(self, msg):
        self.irc.send(('QUIT',), msg)


class Drastikbot():
    def __init__(self, state):
        self.state = state
        self.conf = state["conf"]
        self.log = state["runlog"]

        # IRC command messages
        self.out = Output(self)

        self.reconnect_delay = 0
        self.sigint = 0
        # Message length used by irc.send
        # (TODO: The bot should dynamically change it based on the bot's
        # nickname and hostmask length)
        self.msg_len = 400
        self.msg_delay = 1  # 1 second

        # Runtime Variables
        self.curr_nickname = ''        # Nickname currently used
        self.bot_hostmask = ''         # Hostmask issued by the server
        self.alt_nickname = False      # Alternative nickname used
        self.connected_ip = ''         # IP of the connected IRC server
        self.connected_host = ''       # Hostname of the connected server
        self.ircv3_enabled = []  # IRCv3 Server Capabilities Acknowledged
        # sasl_state = 0: Not tried | 1: Success | 2: Fail | 3: In progress
        self.sasl_state = 0
        self.conn_state = 0  # 0: Disconnected | 1: Registering | 2: Connected
        self.botmodes = []   # [x,I] Modes returned after registration

        # Connection Status
        self.channels = {}  # {"channel": ["mode"]}
        self.names = {}  # {"channel": [{"name": ["mode"]}]}

        # IRC server features
        # They are to be set by RPL_ISUPPORT or other mechanisms.
        # The default values provided are set for max compatibility.
        self.prefix = {"q": "~", "a": "&", "o": "@", "h": "%", "v": "+"}
        self.chantypes = {"#", "&", "+", "!"}  # RFC 2812 channel types
        self.chanmodes = {"A": [], "B": [], "C": [], "D": []}

    def set_msg_len(self, nick_ls):
        u = f"{nick_ls[0]}!{nick_ls[1]}@{nick_ls[2]} "
        c = len(u.encode('utf-8'))
        self.msg_len = 512 - c

    def send(self, cmds, text=None):
        cmds = [dbot_tools.text_fix(cmd) for cmd in cmds]
        if text:
            text = dbot_tools.text_fix(text)
            # https://tools.ietf.org/html/rfc2812.html#section-2.3
            # NOTE: 2) IRC messages are limited to 512 characters in length.
            # With CR-LF we are left with 510 characters to use
            tosend = f"{' '.join(cmds)} :{text}"
        else:
            tosend = ' '.join(cmds)  # for commands
        try:
            tosend = tosend.encode('utf-8')
            multipart = False
            remainder = 0
            if len(tosend) + 2 > self.msg_len:
                # Handle messages that are too long to fit in one message.
                # Truncate messages at the last space found to avoid breaking
                # utf-8.
                tosend = tosend[:self.msg_len].rsplit(b' ', 1)
                remainder = len(tosend[1])
                multipart = True
                tosend = tosend[0]

            tosend = tosend + b'\r\n'
            self.irc_socket.send(tosend)
        except Exception:
            self.log.debug(f'Exception on send() @ irc.py:'
                           f'\n{traceback.format_exc()}')
            return self.irc_socket.close()
        # If the input text is longer than 510 send the rest.
        # "limit" decrements after every message and is used to control
        # the amount of messages the bot is allowed to send. The value
        # is set to -1 by default, which means it can send an infinite
        # amount of messages, since zero will never be met in the if
        # statement below.
        if multipart:
            time.sleep(self.msg_delay)
            irc_msg_len = len(' '.join(cmds).encode('utf-8'))
            tr = self.msg_len - 2 - irc_msg_len - remainder
            t = text.encode('utf-8')[tr:]
            self.send(cmds, t)

    def reconn_wait(self):
        '''
        Incrementally Wait before reconnection to the server. The initial delay
        is zero, then it is set to ten seconds and keeps doubling after each
        attempt until it reaches ten minutes.
        '''
        time.sleep(self.reconnect_delay)
        if self.reconnect_delay == 0:
            self.reconnect_delay = 10  # 10 sec.
        elif self.reconnect_delay < 60 * 10:  # 10 mins.
            self.reconnect_delay *= 2
        # Because the previous statement will end up with 640 seconds,
        # we set it to 600 seconds and keep it there until we connect:
        if self.reconnect_delay > 60 * 10:  # 10 mins.
            self.reconnect_delay = 60 * 10

    def connect(self):
        host = self.conf.get_host()
        port = self.conf.get_port()
        try:
            # Timeout on socket.create_connection should be above the irc
            # server's ping timeout setting
            self.irc_socket = socket.create_connection((host, port), 300)
            if self.conf.get_ssl():
                self.irc_socket = ssl.wrap_socket(self.irc_socket)
        except OSError:
            if self.sigint:
                return
            self.log.debug('Exception on connect() @ irc_sock.connect()'
                           f'\n{traceback.format_exc()}')
            self.log.info(' - No route to host. Retrying in {} seconds'.format(
                self.reconnect_delay))
            try:
                self.irc_socket.close()
            except Exception:
                pass
            self.reconn_wait()  # Wait before next reconnection attempt.
            return self.connect()
        except IOError:
            try:
                self.irc_socket.close()
            except Exception:
                pass
            self.log.debug(f'Exception on connect() @ irc_sock.connect():'
                           f'\n{traceback.format_exc()}')
            self.reconn_wait()
            return self.connect()

        # SOCKET OPTIONS
        # self.irc_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

        if self.conf.get_network_passoword():
            # Authenticate if the server is password protected
            self.send(('PASS', self.conf.get_network_password()))

        # Set the connected variables, to inform the bot where exactly we are
        # connected
        try:
            # There is a possibility that an Exception is raised here.
            # Because they are not vital to the bot's operation we will just
            # ignore them.
            # Consider adding them to dbot_tools as functions.
            self.connected_ip = self.irc_socket.getpeername()[0]
            self.connected_host = socket.gethostbyaddr(
                self.connected_ip)[0]
        except Exception:
            pass
