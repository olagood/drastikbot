#!/usr/bin/env python3
# coding=utf-8

# This file handles registering, reconnecting, pinging,
# and other methods and functions required for the bot
# to operate.

'''
Copyright (C) 2018 drastik.org

This file is part of drastikbot.

Drastikbot is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

Drastikbot is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Drastikbot. If not, see <http://www.gnu.org/licenses/>.
'''

from threading import Thread
from queue import Queue
import re
import time
import base64

from dbot_tools import Message, Logger
from irc.irc import Drastikbot
from irc.modules import Modules


class Register:
    def __init__(self, irc):
        self.irc = irc

    # AUTHENTICATION #
    def sasl(self, rawqueue):
        if not (self.irc.var.authentication.lower() == 'sasl'
                or 'sasl' in self.irc.var.ircv3_cap_ack):
            self.irc.var.sasl_state = 2
            self.irc.var.ircv3_cap_end = 1
            return
        self.irc.send(('AUTHENTICATE', 'PLAIN'))
        while self.irc.var.conn_state == 1:
            msg = Message(rawqueue.get())
            msg.msg_handler()
            if 'AUTHENTICATE +' in msg.msg:
                sasl_pass = '{}\0{}\0{}'.format(self.irc.var.username,
                                                self.irc.var.username,
                                                self.irc.var.auth_password)
                self.irc.send(('AUTHENTICATE',
                               base64.b64encode(sasl_pass.encode('utf-8'))))
            elif '903' == msg.cmd_ls[0]:  # SASL authentication successful
                self.irc.var.sasl_state = 1
                self.irc.var.ircv3_cap_end = 1
                break
            elif '904' == msg.cmd_ls[0]:  # SASL authentication failed
                self.irc.var.sasl_state = 2
                self.irc.var.ircv3_cap_end = 1
                break

    def nickserv_identify(self):
        self.irc.privmsg('NickServ', 'IDENTIFY {} {}'
                         .format(self.irc.var.nickname,
                                 self.irc.var.auth_password))

    def nickserv_ghost(self, rawqueue):
        if self.irc.var.authentication.lower() and self.irc.var.auth_password:
            self.irc.privmsg('NickServ', 'GHOST {} {}'.format(
                self.irc.var.nickname, self.irc.var.auth_password))
            while self.irc.var.conn_state == 1:
                msg = Message(rawqueue.get())
                msg.msg_handler()
                if "has been ghosted" in msg.params:
                    self.irc.nick(self.irc.var.nickname)
                    self.nickserv_identify()
                    break

    # CAPABILITY NEGOTIATION #
    def cap_ls(self, msg):
        self.irc.var.ircv3_serv = True
        self.irc.var.ircv3_cap_ls = re.search(r"(?:CAP .* LS :)(.*)",
                                              msg.msg).group(1).split(' ')
        cap_req = [i for i in self.irc.var.ircv3_cap_ls if i in
                   self.irc.var.ircv3_cap_req]
        self.irc.send(('CAP', 'REQ', ':{}'.format(' '.join(cap_req))))

    def cap_ack(self, msg):
        cap_ack = re.search(r"(?:CAP .* ACK :)(.*)", msg.msg).group(1)
        self.irc.var.ircv3_cap_ack = cap_ack.split()

    def initialize(self):
        self.irc.send(('CAP', 'LS', self.irc.var.ircv3_ver))
        self.irc.send(('USER', self.irc.var.username, '0', '*',
                       ':{}'.format(self.irc.var.realname)))
        self.irc.var.curr_nickname = self.irc.var.nickname
        self.irc.nick(self.irc.var.nickname)

    def reg_handler(self, rawqueue):
        self.initialize()
        while self.irc.var.conn_state == 1:
            msg = Message(rawqueue.get())
            msg.msg_handler()
            if 'CAP' == msg.cmd_ls[0]:
                if 'LS' == msg.cmd_ls[2]:
                    self.cap_ls(msg)
                if 'ACK' == msg.cmd_ls[2]:
                    self.cap_ack(msg)
            if self.irc.var.ircv3_cap_ack and self.irc.var.sasl_state == 0:
                self.sasl(rawqueue)
            if self.irc.var.ircv3_cap_end == 1:
                self.irc.send(('CAP', 'END'))
                self.irc.var.ircv3_cap_end = 2
            if 'PING' == msg.cmd_ls[0]:
                self.irc.send(('PONG', msg.params))
            if '433' in msg.cmd_ls[0]:  # ERR_NICKNAMEINUSE
                self.irc.var.curr_nickname = self.irc.var.curr_nickname + '_'
                self.irc.nick(self.irc.var.curr_nickname)
                self.irc.var.alt_nickname = True
            if '376' in msg.cmd_ls[0]:  # RPL_ENDOFMOTD
                if self.irc.var.alt_nickname and self.irc.var.authentication:
                    self.nickserv_ghost(rawqueue)
                elif self.irc.var.authentication.lower() == 'nickserv':
                    self.nickserv_identify()
                self.irc.var.conn_state = 2  # End the loop
                self.irc.join(self.irc.var.channels)


class Events:
    def __init__(self, log):
        self.log = log

    def rpl_namreply(self, irc, msg):
        channel = msg.cmd_ls[3]
        if channel not in irc.var.namesdict:
            irc.var.namesdict[channel] = [[], {}]
        namesdict = irc.var.namesdict[channel]
        namesdict[0] = [msg.cmd_ls[2]]
        modes = ['~', '&', '@', '%', '+']
        for i in msg.params.split():
            if i[:1] in modes:
                namesdict[1].update({i[1:]: [i[:1]]})
            else:
                namesdict[1].update({i: []})
        irc.send(('MODE', channel))  # Reply handled by rpl_channelmodeis

    def rpl_channelmodeis(self, irc, msg):
        '''Handle reply to: "MODE #channel" to save the channel modes'''
        channel = msg.cmd_ls[2]
        m = list(msg.cmd_ls[3][1:])
        i = len(m)
        while i != 0:
            i -= 1
            irc.var.namesdict[channel][0].append(m[i])

    def irc_join(self, irc, msg):
        nick_ls = msg.prefix_extract()
        nick = nick_ls[0]
        # We check to see if the join command was used by the bot
        # and get the hostmask and call a function to calculate and
        # set irc.var.msg_len
        if nick == irc.var.curr_nickname:
            irc.var.bot_hostmask = nick_ls[2]
            irc.set_msg_len(nick_ls)

        try:
            channel = msg.params.split()[0]
        except IndexError:
            # Some servers will pass the channel as params instead of as
            # a command.
            channel = msg.cmd_ls[1]
        try:
            irc.var.namesdict[channel][1][nick] = []
        except KeyError:
            # This should not be needed now that @rpl_namreply()
            # is fixed, but the exception will be monitored for
            # possible future reoccurance, before it is removed.
            self.log.debug('KeyError @Events.irc_part(). Err: 01')
            pass

    def irc_part(self, irc, msg):
        nick = msg.prefix_extract()[0]
        try:
            channel = msg.cmd_ls[1]
            del irc.var.namesdict[channel][1][nick]
        except KeyError:
            # This should not be needed now that @rpl_namreply()
            # is fixed, but the exception will be monitored for
            # possible future reoccurance, before it is removed.
            self.log.debug('KeyError @Events.irc_part(). Err: 01')
            pass

    def irc_quit(self, irc, msg):
        nick = msg.prefix_extract()[0]
        for chan in irc.var.namesdict:
            try:
                del chan[1][nick]
            except Exception as e:
                # This should not be needed now that @rpl_namreply()
                # is fixed, but the exception will be monitored for
                # possible future reoccurance, before it is removed.
                # We will also log the Exception here to make sure there
                # isn't another bug possible.
                self.log.debug(f'KeyError @Events.irc_part(). Err: 01 | {e}')
                pass

    def irc_nick(self, irc, msg):
        nick = msg.prefix_extract()[0]
        for chan in irc.var.namesdict:
            try:
                k = irc.var.namesdict[chan][1]
                k[msg.params] = k.pop(nick)
            except KeyError:
                # This should not be needed now that @rpl_namreply()
                # is fixed, but the exception will be monitored for
                # possible future reoccurance, before it is removed.
                self.log.debug('KeyError @Events.irc_part(). Err: 01')
                pass

    def irc_mode(self, irc, msg):
        if len(msg.cmd_ls) > 3:
            # MODE used on a user
            m_dict = {'q': '~', 'a': '&', 'o': '@', 'h': '%', 'v': '+'}
            channel = msg.cmd_ls[1]
            m = msg.cmd_ls[2]    # '+ooo' or '-vvv'
            modes = list(m[1:])  # [o,o,o,o]
            i = len(modes)
            if m[:1] == '+':
                while i != 0:
                    i -= 1
                    nick = msg.cmd_ls[3+i]
                    try:
                        irc.var.namesdict[channel][1][nick].append(
                            m_dict[modes[i]])
                    except KeyError:
                        # This should not be needed now that @rpl_namreply()
                        # is fixed, but the exception will be monitored for
                        # possible future reoccurance, before it is removed.
                        self.log.debug('KeyError @Events.irc_mode(). Err: 01')
                        irc.var.namesdict[channel][1].update({nick: modes[i]})
            else:
                while i != 0:
                    i -= 1
                    irc.var.namesdict[channel][1][msg.cmd_ls[3+i]].remove(
                        m_dict[modes[i]])
        else:
            # MODE used on a channel
            if msg.cmd_ls[1] == irc.var.curr_nickname:
                try:
                    irc.var.botmodes.extend(list(msg.cmd_ls[2][1:]))
                except IndexError:
                    # Some servers will pass the modes as params instead of as
                    # a command. A better solution would be to have the
                    # response as a list.
                    irc.var.botmodes.extend(list(msg.params.split()[0][1:]))
                return
            channel = msg.cmd_ls[1]
            m = msg.cmd_ls[2]    # '+ooo' or '-vvv'
            modes = list(m[1:])  # [o,o,o,o]
            i = len(modes)
            if m[:1] == '+':
                while i != 0:
                    i -= 1
                    irc.var.namesdict[channel][0].append(modes[i])
            else:
                while i != 0:
                    i -= 1
                    irc.var.namesdict[channel][0].remove(modes[i])


class Main:
    def __init__(self, conf_dir):
        self.irc = Drastikbot(conf_dir)
        self.mod = Modules(conf_dir, self.irc)
        self.reg = Register(self.irc)
        self.log = Logger(conf_dir, 'runtime.log')
        self.rawqueue = Queue()

    def conn_lost(self):
        self.log.info('[INFO] Connection Lost... Retrying in {} seconds'
                      .format(self.irc.var.reconnect_delay))
        self.irc.irc_socket.close()
        self.irc.var.conn_state = 0
        time.sleep(self.irc.var.reconnect_delay)
        self.log.info(' - Reconnecting')
        self.__init__(self.irc.cd)  # Reload the class
        self.main()  # Restart the bot

    def recieve(self):
        while self.irc.var.conn_state != 0:
            try:
                msg_raw = self.irc.irc_socket.recv(4096)
            except Exception:
                self.log.debug('Exception on recieve().')
                self.conn_lost()
                break
            if len(msg_raw) == 0:
                self.log.info('[INFO] recieve() exiting...')
                self.conn_lost()
                break
            msg_raw = msg_raw.split(b'\r\n')
            for l in msg_raw:
                if l:
                    self.rawqueue.put(l)

    def service(self):
        def mod_call(msgtype):
            self.thread_make(self.mod.mod_main,
                             (self.irc, msg.module_args_prep(self.irc),
                              msg.params.split(' ')[0], msgtype))
        e = Events(self.log)
        while self.irc.var.conn_state == 2:
            msg = Message(self.rawqueue.get())
            msg.msg_handler()

            # User blacklist (this should be moved to recieve() along with all
            # the msg parsing when the dataclass is implemented.)
            # Add support for hostmasks.
            if msg.prefix_extract()[0].lower() in self.irc.var.user_blacklist:
                continue

            if 'PRIVMSG' == msg.cmd_ls[0]:
                mod_call('PRIVMSG')
            elif 'NOTICE' == msg.cmd_ls[0]:
                mod_call('NOTICE')
            elif 'PING' == msg.cmd_ls[0]:
                self.irc.send(('PONG', msg.params))
            elif 'JOIN' == msg.cmd_ls[0]:
                e.irc_join(self.irc, msg)
                mod_call('JOIN')
            elif 'QUIT' == msg.cmd_ls[0]:
                e.irc_quit(self.irc, msg)
                mod_call('QUIT')
            elif 'PART' == msg.cmd_ls[0]:
                e.irc_part(self.irc, msg)
                mod_call('PART')
            elif 'MODE' == msg.cmd_ls[0] and\
                 msg.cmd_ls[1] in self.irc.var.namesdict:
                e.irc_mode(self.irc, msg)
                mod_call('MODE')
            elif ('324' or 'MODE') == msg.cmd_ls[0]:  # RPL_CHANNELMODEIS
                e.rpl_channelmodeis(self.irc, msg)
            elif '353' == msg.cmd_ls[0]:  # RPL_NAMREPLY
                e.rpl_namreply(self.irc, msg)

    def thread_make(self, target, args='', daemon=False):
        thread = Thread(target=target, args=(args))
        thread.daemon = daemon
        thread.start()
        return thread

    def main(self):
        self.irc.connect()
        self.mod.mod_import()
        self.irc.var.conn_state = 1
        self.thread_make(self.recieve)
        regiT = self.thread_make(self.reg.reg_handler, (self.rawqueue,))
        regiT.join()  # wait until registered
        self.thread_make(self.service)  # control server input
        self.thread_make(self.mod.mod_startup, (self.irc,))
