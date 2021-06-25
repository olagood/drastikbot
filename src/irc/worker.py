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


irc_client = None
state = None

sigint = False


def run(state0):
    global state, irc_client
    state = state0

    irc.modules.init(state)

    while True:
        if sigint:
            return

        state["modules"] = irc.modules.mod_import(state)

        irc_client = Drastikbot(state)
        irc_client.connect()

        signal.signal(signal.SIGINT, sigint_handler)

        irc_client.conn_state = 1

        with ThreadPoolExecutor() as tpool:
            loop = tpool.submit(receive, tpool)
            tpool.submit(irc.modules.startup, state, irc_client)

            # Wait for the receive loop to return
            loop.result()


def receive(tpool):
    log = state["runlog"]

    data = b""
    while irc_client.conn_state != 0:
        try:
            data += irc_client.irc_socket.recv(4096)
        except BlockingIOError:
            continue  # No data on non blocking socket.
        except Exception:
            tc = traceback.format_exc()
            log.debug(f'! Exception on receive(). \n{tc}')
            return connection_lost()

        if not data:
            log.info('! recieve() exiting...')
            return connection_lost()

        while True:
            data_l = data.split(b'\n', 1)
            if len(data_l) == 1:
                break    # No lines yet, wait for more data

            line, data = data_l
            message = irc.message.parse(irc_client, line)

            # Reload modules in developer mode
            if state["devmode"]:
                state["modules"] = irc.modules.reload_all(state)

            tpool.submit(irc.modules.dispatch, state, irc_client, message)


def connection_lost():
    l = state["runlog"]

    irc_client.irc_socket.close()

    if sigint:
        return

    l.info("! Connection lost. Retrying in"
           f" {irc_client.reconnect_delay} seconds.")
    l.info('! Reconnecting.')


def sigint_handler(signum, frame):
    global sigint

    log = state["runlog"]

    if not sigint:
        print("")  # Pretty stdout
        log.info("<- Quiting...")
        sigint = True
        irc_client.conn_state = 0
        irc_client.out.quit(state["conf"].get_quitmsg())
    else:
        print("")  # Pretty stdout
        log.info("<--- Force Quit.")
        os._exit(1)
