# coding=utf-8

# Functionality for connecting, reconnecting, registering and pinging to the
# IRC server. Recieving messages from the server and calling the module handler
# is also done in this file.

'''
Copyright (C) 2017-2021 drastik.org

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
import signal
import traceback
from concurrent.futures import ThreadPoolExecutor

import irc.message
import irc.modules
from dbot_tools import Logger
from irc.irc import Drastikbot


class Main:
    def __init__(self, state, mod=False):
        self.state = state

        signal.signal(signal.SIGINT, self.sigint_hdl)

        self.tpool = ThreadPoolExecutor()

        self.log = state["runlog"]
        self.irc = Drastikbot(state)

        irc.modules.init(state)
        self.mod_state = irc.modules.mod_import(state)

    def conn_lost(self):
        if self.irc.sigint:
            return
        self.log.info('<!> Connection Lost. Retrying in {} seconds.'
                      .format(self.irc.reconnect_delay))
        self.irc.irc_socket.close()
        self.irc.conn_state = 0
        self.irc.reconn_wait()  # Wait before next reconnection attempt.
        self.log.info('> Reconnecting...')
        self.irc = Drastikbot(self.state)
        self.main(reconnect=True)  # Restart the bot

    def recieve(self):
        data = b""
        while self.irc.conn_state != 0:
            try:
                data += self.irc.irc_socket.recv(4096)
            except BlockingIOError:
                continue  # No data on non blocking socket.
            except Exception:
                self.log.debug('<!!!> Exception on recieve().'
                               f'\n{traceback.format_exc()}')
                self.conn_lost()
                break

            if not data:
                self.log.info('<!> recieve() exiting...')
                self.conn_lost()
                break

            while True:
                data_l = data.split(b'\n', 1)
                if len(data_l) == 1:
                    break

                data = data_l[1]
                line = data_l[0]
                message = irc.message.parse(line)

                # Auto reload modules in developer mode to make programming easier
                if self.state["devmode"]:
                    self.mod_state = irc.modules.reload_all(self.mod_state)

                self.tpool.submit(irc.modules.dispatch,
                                  self.mod_state, self.state, self.irc,
                                  message)

    def thread_make(self, target, args='', daemon=False):
        thread = Thread(target=target, args=(args))
        thread.daemon = daemon
        thread.start()
        return thread

    def sigint_hdl(self, signum, frame):
        if self.irc.sigint == 0:
            self.log.info("\n> Quiting...")
            self.irc.sigint += 1
            self.irc.conn_state = 0
            self.irc.quit()
        else:
            self.log.info("\n Force Quit.")
            os._exit(1)

    def main(self, reconnect=False):
        self.irc.connect()

        if self.irc.sigint:
            return
        self.irc.conn_state = 1
        self.thread_make(self.recieve)
        self.thread_make(irc.modules.startup,
                         (self.mod_state, self.state, self.irc))
