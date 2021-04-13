# coding=utf-8

'''
Copyright (C) 2021 drastik.org

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

import base64


class Module:
    def __init__(self):
        self.irc_commands = ["CAP", "AUTHENTICATE", "903", "904", "433", "376"]
        self.startup = True


def init(i, irc):
    nickname = i.bot["conf"].get_nickname()
    user = i.bot["conf"].get_user()
    realname = i.bot["conf"].get_realname()

    irc.send(('CAP', 'LS', irc.ircv3_ver))
    irc.send(('USER', user, '0', '*', f':{realname}'))
    irc.nick(nickname)

    irc.curr_nickname = nickname


def cap(i, irc):
    if i.params[1] == "LS":  # CAP * LS
        cap_ls(i, irc)
    elif i.params[1] == "ACK":
        cap_ack(i, irc)


def cap_ls(i, irc):
    irc.ircv3_cap_ls = [x for x in i.params[-1].split(" ") if x]
    cap_req = [x for x in irc.ircv3_cap_ls if x in irc.ircv3_cap_req]

    # If the server does not support any of the capabilities the bot supports,
    # end the registration here.
    if not cap_req:
        irc.send(('CAP', 'END'))
        return

    irc.send(('CAP', 'REQ', ':{}'.format(' '.join(cap_req))))


def cap_ack(i, irc):
    irc.ircv3_cap_ack = i.params[-1].split()

    if i.bot["conf"].is_auth_method("sasl") and "sasl" in irc.ircv3_cap_ack:
        irc.send(('AUTHENTICATE', 'PLAIN'))
    else:
        irc.send(('CAP', 'END'))


def authenticate(i, irc):
    user = i.bot["conf"].get_user()
    password = i.bot["conf"].get_auth_password()
    m = f'{user}\0{user}\0{password}'
    m = m.encode("utf-8")
    m = base64.b64encode(m)
    irc.send(('AUTHENTICATE', m))


def sasl_success_903(i, irc):
    irc.send(('CAP', 'END'))


def sasl_fail_904(i, irc):
    i.bot["log"].info("! SASL authentication failed.")
    irc.send(("CAP", "END"))


def err_nicnameinuse_433(self):
    irc.curr_nickname = irc.curr_nickname + '_'
    irc.alt_nickname = True
    irc.nick(irc.curr_nickname)


def rpl_endofmotd_376(i, irc):
    # TODO: check what the actual nickname is. Aka see for +r mode
    if irc.alt_nickname and i.bot["conf"].get_auth_method():
        irc.privmsg("NickServ", f"GHOST {nickname} {password}")
        irc.privmsg("NickServ", f"RECOVER {nickname} {password}")
    elif i.bot["conf"].is_auth_method("nickserv"):
        irc.privmsg("NickServ", f"IDENTIFY {nickname} {password}")

    irc.join(i.bot["conf"].get_channels())


def main(i, irc):
    {
        "__STARTUP": init,
        "CAP": cap,
        "AUTHENTICATE": authenticate,
        "903": sasl_success_903,
        "904": sasl_fail_904,
        "433": err_nicnameinuse_433,
        "376": rpl_endofmotd_376
    }[i.command](i, irc)
