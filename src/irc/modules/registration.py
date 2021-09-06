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

import constants


class Module:
    irc_commands = ["CAP", "AUTHENTICATE", "903", "904", "433", "376"]
    startup = True


def init(i, irc):
    nickname = i.bot["conf"].get_nickname()
    user = i.bot["conf"].get_user()
    realname = i.bot["conf"].get_realname()

    irc.send(('CAP', 'LS', constants.ircv3_version))
    irc.send(('USER', user, '0', '*', f':{realname}'))
    irc.out.nick(nickname)

    irc.curr_nickname = nickname


def cap(i, irc):
    subcmd = i.msg.get_subcommand()
    if str(subcmd) == "LS":
        cap_ls(subcmd, irc)
    elif str(subcmd) == "ACK":
        cap_ack(i, subcmd, irc)


def cap_ls(ls, irc):
    req = ls.get_req()

    # If the server does not support any of the capabilities the bot supports,
    # end the registration here.
    if not req:
        irc.send(('CAP', 'END'))
        return

    req_s = " ".join(req)
    irc.send(('CAP', 'REQ', f':{req_s}'))


def cap_ack(i, ack, irc):
    irc.ircv3_enabled = ack.get_enabled()

    if i.bot["conf"].is_auth_method("sasl") and "sasl" in irc.ircv3_enabled:
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
    i.bot["runlog"].info("! SASL authentication failed.")
    irc.send(("CAP", "END"))


def err_nicknameinuse_433(i, irc):
    irc.curr_nickname = irc.curr_nickname + '_'
    irc.alt_nickname = True
    irc.out.nick(irc.curr_nickname)


def rpl_endofmotd_376(i, irc):
    # TODO: check what the actual nickname is. Aka see for +r mode
    nickname = i.bot["conf"].get_nickname()
    password = i.bot["conf"].get_auth_password()
    if irc.alt_nickname and i.bot["conf"].get_auth_method():
        irc.out.privmsg("NickServ", f"GHOST {nickname} {password}")
        irc.out.privmsg("NickServ", f"RECOVER {nickname} {password}")
    elif i.bot["conf"].is_auth_method("nickserv"):
        irc.out.privmsg("NickServ", f"IDENTIFY {nickname} {password}")

    irc.out.join(i.bot["conf"].get_channels())


def main(i, irc):
    {
        "__STARTUP": init,
        "CAP": cap,
        "AUTHENTICATE": authenticate,
        "903": sasl_success_903,
        "904": sasl_fail_904,
        "433": err_nicknameinuse_433,
        "376": rpl_endofmotd_376
    }[i.msg.get_command()](i, irc)
