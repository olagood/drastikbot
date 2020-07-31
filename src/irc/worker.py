# coding=utf-8

# Functionality for connecting, reconnecting, registering and pinging to the
# IRC server. Recieving messages from the server and calling the module handler
# is also done in this file.

'''
Copyright (C) 2017-2020 drastik.org

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

from threading import Thread
import os
import re
import base64
import traceback

from irc.message import Message
from dbot_tools import Logger
from irc.irc import Drastikbot
from irc.modules import Modules


class Register:
    def __init__(self, irc):
        self.irc = irc
        self.msg = ''
        # self.cap is used to indicate the status IRCv3 capability
        # negotiation.
        # Values:
        # -1: Check for IRCv3 | 0: Ended or none
        #  1: In progress | 2: Send CAP END
        self.cap = -1
        self.nickserv_ghost_status = 0  # 0: None | 1: In progress
        self.nickserv_recover_status = 0  # 0: None | 1: In progress
        self.motd = False

    # --- IRCv3 --- #
    def cap_ls(self):
        self.irc.var.ircv3_serv = True
        self.cap = 1
        self.irc.var.ircv3_cap_ls = re.search(r"(?:CAP .* LS :)(.*)",
                                              self.msg.msg).group(1).split(' ')
        cap_req = [i for i in self.irc.var.ircv3_cap_ls
                   if i in self.irc.var.ircv3_cap_req]

        # If the server doesnt support any capabilities we support end the
        # registration now
        if cap_req == []:
            self.cap_end()
            return

        self.irc.send(('CAP', 'REQ', ':{}'.format(' '.join(cap_req))))

    def cap_ack(self):
        cap_ack = re.search(r"(?:CAP .* ACK :)(.*)", self.msg.msg).group(1)
        self.irc.var.ircv3_cap_ack = cap_ack.split()

    def cap_end(self):
        self.irc.send(('CAP', 'END'))
        self.cap = 0

    # -- SASL #
    def sasl_succ(self):
        self.irc.var.sasl_state = 1
        self.cap = 2

    def sasl_fail(self):
        self.irc.var.sasl_state = 2
        self.cap = 2

    def sasl_init(self):
        if not self.irc.var.authentication.lower() == 'sasl' \
           or 'sasl' not in self.irc.var.ircv3_cap_ack:
            self.sasl_fail()
        else:
            self.irc.send(('AUTHENTICATE', 'PLAIN'))
            self.irc.var.sasl_state = 3

    def sasl_auth(self):
        username = self.irc.var.username
        password = self.irc.var.auth_password
        sasl_pass = f'{username}\0{username}\0{password}'
        self.irc.send(('AUTHENTICATE',
                       base64.b64encode(sasl_pass.encode('utf-8'))))

    # --- NickServ --- #
    def nickserv_identify(self):
        nickname = self.irc.var.nickname
        password = self.irc.var.auth_password
        self.irc.privmsg('NickServ', f'IDENTIFY {nickname} {password}')

    def nickserv_recover(self):
        nickname = self.irc.var.nickname
        password = self.irc.var.auth_password
        if self.irc.var.authentication and self.irc.var.auth_password \
           and self.nickserv_recover_status == 0:
            self.irc.privmsg('NickServ', f'RECOVER {nickname} {password}')
            self.nickserv_recover_status = 1
        elif "You have regained control" in self.msg.msg:
            self.nickserv_recover_status = 0
            self.irc.var.curr_nickname = nickname
            self.irc.var.alt_nickname = False

    def nickserv_ghost(self):
        nickname = self.irc.var.nickname
        password = self.irc.var.auth_password
        if self.irc.var.authentication and self.irc.var.auth_password \
           and self.nickserv_ghost_status == 0:
            self.irc.privmsg('NickServ', f'GHOST {nickname} {password}')
            self.nickserv_ghost_status = 1
        elif "has been ghosted" in self.msg.params \
             and self.nickserv_ghost_status == 1:
            self.irc.nick(nickname)
            self.nickserv_identify()
            self.nickserv_ghost_status = 0
            self.irc.var.curr_nickname = nickname
            self.irc.var.alt_nickname = False
        elif "/msg NickServ help" in self.msg.msg or \
             "/msg NickServ HELP" in self.msg.msg:
            self.nickserv_ghost_status = 0
            self.nickserv_recover()
        elif "is not a registered nickname" in self.msg.msg:
            self.nickserv_ghost_status = 0

    # --- Error Handlers --- #
    def err_nicnameinuse_433(self):
        self.irc.var.curr_nickname = self.irc.var.curr_nickname + '_'
        self.irc.nick(self.irc.var.curr_nickname)
        self.irc.var.alt_nickname = True

    # --- Registration Handlers --- #
    def reg_init(self):
        self.irc.send(('CAP', 'LS', self.irc.var.ircv3_ver))
        self.irc.send(('USER', self.irc.var.username, '0', '*',
                       f':{self.irc.var.realname}'))
        self.irc.var.curr_nickname = self.irc.var.nickname
        self.irc.nick(self.irc.var.nickname)

    def ircv3_fn_caller(self):
        a = len(self.msg.cmd_ls)
        cmd_ls = self.msg.cmd_ls
        if a > 2 and 'CAP LS' == f'{cmd_ls[0]} {cmd_ls[2]}':
            self.cap_ls()
        elif a > 2 and 'CAP ACK' == f'{cmd_ls[0]} {cmd_ls[2]}':
            self.cap_ack()
        # ERR_NICKNAMEINUSE
        if '433' in self.msg.cmd_ls[0]:
            self.err_nicnameinuse_433()
        # SASL
        if self.irc.var.ircv3_cap_ack and self.irc.var.sasl_state == 0:
            self.sasl_init()
        elif 'AUTHENTICATE' in self.msg.msg:  # AUTHENTICATE +
            self.sasl_auth()
        elif '903' == cmd_ls[0]:  # SASL authentication successful
            self.sasl_succ()
        elif '904' == cmd_ls[0]:  # SASL authentication failed
            self.sasl_fail()
        # End capability negotiation.
        if self.cap == 2:
            self.cap_end()

    def reg_fn_caller(self):
        if '433' in self.msg.cmd_ls[0]:  # ERR_NICKNAMEINUSE
            self.err_nicnameinuse_433()
        if '376' in self.msg.cmd_ls[0]:  # RPL_ENDOFMOTD
            self.motd = True

        if self.motd and self.irc.var.alt_nickname \
           and self.irc.var.authentication and self.nickserv_ghost_status == 0\
           and self.nickserv_recover_status == 0:
            self.nickserv_ghost()
        if self.motd and self.irc.var.authentication.lower() == 'nickserv':
            self.nickserv_identify()
        if self.nickserv_ghost_status == 1:
            self.nickserv_ghost()
        if self.nickserv_recover_status == 1:
            self.nickserv_recover()
        if self.motd and not self.nickserv_ghost_status == 1 \
           and not self.nickserv_recover_status == 1:
            self.irc.var.conn_state = 2
            self.irc.join(self.irc.var.channels)

    def reg_main(self, msg):
        self.msg = msg
        if self.cap != 0:
            # Check for IRCv3 methods
            self.ircv3_fn_caller()
        else:
            # Run normal IRC registration methods
            self.reg_fn_caller()


class Main:
    def __init__(self, conf_dir, proj_path, mod=False):
        self.irc = Drastikbot(conf_dir)
        self.irc.var.proj_path = proj_path
        if mod:
            self.mod = mod
            mod.irc = self.irc  # Update the irc variable
        else:
            self.mod = Modules(self.irc)
        self.reg = Register(self.irc)
        self.log = Logger(conf_dir, 'runtime.log')
        self.irc.var.log = self.log

    def conn_lost(self):
        if self.irc.var.sigint:
            return
        self.log.info('<!> Connection Lost. Retrying in {} seconds.'
                      .format(self.irc.var.reconnect_delay))
        self.irc.irc_socket.close()
        self.irc.var.conn_state = 0
        self.irc.reconn_wait()  # Wait before next reconnection attempt.
        self.log.info('> Reconnecting...')
        # Reload the class
        self.__init__(self.irc.cd, self.irc.var.proj_path, mod=self.mod)
        self.main(reconnect=True)  # Restart the bot

    def recieve(self):
        while self.irc.var.conn_state != 0:
            try:
                msg_raw = self.irc.irc_socket.recv(4096)
            except Exception:
                self.log.debug('<!!!> Exception on recieve().'
                               f'\n{traceback.format_exc()}')
                self.conn_lost()
                break

            msg_raw_ls = msg_raw.split(b'\r\n')
            for line in msg_raw_ls:
                if line:
                    msg = Message(line)
                    if self.irc.var.conn_state == 2:
                        self.service(msg)
                    if 'PING' == msg.cmd_ls[0]:
                        self.irc.send(('PONG', msg.params))
                    elif self.irc.var.conn_state == 1:
                        self.service(msg)
                        self.reg.reg_main(msg)

            if len(msg_raw) == 0:
                self.log.info('<!> recieve() exiting...')
                self.conn_lost()
                break

    def service(self, msg):
        msg.channel_prep(self.irc)
        self.thread_make(self.mod.mod_main,
                         (self.irc, msg, msg.params.split(' ')[0]))

    def thread_make(self, target, args='', daemon=False):
        thread = Thread(target=target, args=(args))
        thread.daemon = daemon
        thread.start()
        return thread

    def sigint_hdl(self, signum, frame):
        if self.irc.var.sigint == 0:
            self.log.info("\n> Quiting...")
            self.irc.var.sigint += 1
            self.irc.var.conn_state = 0
            self.irc.quit()
        else:
            self.log.info("\n Force Quit.")
            os._exit(1)

    def main(self, reconnect=False):
        self.irc.connect()
        if not reconnect:
            self.mod.mod_import()
        if self.irc.var.sigint:
            return
        self.irc.var.conn_state = 1
        self.thread_make(self.recieve)
        reg_t = self.thread_make(self.reg.reg_init)
        reg_t.join()  # wait until registered
        self.log.info(f"\nNickname: {self.irc.var.curr_nickname}")
        if not reconnect:
            self.thread_make(self.mod.mod_startup, (self.irc,))
