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
        self.state["modules"] = irc.modules.mod_import(state)

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

    def receive(self):
        data = b""
        while self.irc.conn_state != 0:
            try:
                data += self.irc.irc_socket.recv(4096)
            except BlockingIOError:
                continue  # No data on non blocking socket.
            except Exception:
                tc = traceback.format_exc()
                self.log.debug(f'! Exception on receive(). \n{tc}')
                self.conn_lost()
                break

            if not data:
                self.log.info('! recieve() exiting...')
                self.conn_lost()
                break

            while True:
                data_l = data.split(b'\n', 1)
                if len(data_l) == 1:
                    break    # No lines yet, wait for more data

                line, data = data_l
                message = irc.message.parse(self.irc, line)

                # Reload modules in developer mode
                if self.state["devmode"]:
                    self.state["modules"] = irc.modules.reload_all(self.state)

                self.tpool.submit(irc.modules.dispatch,
                                  self.state, self.irc, message)

    def thread_make(self, target, args='', daemon=False):
        thread = Thread(target=target, args=(args))
        thread.daemon = daemon
        thread.start()
        return thread

    def sigint_hdl(self, signum, frame):
        if self.irc.sigint == 0:
            print("")  # Pretty stdout
            self.log.info("<- Quiting...")
            self.irc.sigint += 1
            self.irc.conn_state = 0
            self.irc.out.quit(self.state["conf"].get_quitmsg())
        else:
            print("")  # Pretty stdout
            self.log.info("<--- Force Quit.")
            os._exit(1)

    def main(self, reconnect=False):
        self.irc.connect()

        if self.irc.sigint:
            return
        self.irc.conn_state = 1
        self.thread_make(self.receive)
        self.thread_make(irc.modules.startup, (self.state, self.irc))
