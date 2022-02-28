# coding=utf-8

# An RFC 2812 compliant IRC message parser. It expects that the
# message passed has already been split at the newline by the caller.
# No validation is performed and invalid input may crash it.

# Copyright (C) 2021 drastik.org
#
# This file is part of drastikbot.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, version 3 only.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import re

import constants  # type: ignore


# ====================================================================
# Helper commands
# ====================================================================

def remove_formatting(s):
    '''Remove IRC String formatting codes'''
    # - Regex -
    # Capture "x03N,M". Should be the first called:
    # (\\x03[0-9]{0,2},{1}[0-9]{1,2})
    # Capture "x03N". Catch all color codes.
    # (\\x03[0-9]{0,2})
    # Capture the other formatting codes
    s = re.sub(r'(\\x03[0-9]{0,2},{1}[0-9]{1,2})', '', s)
    s = re.sub(r'(\\x03[0-9]{1,2})', '', s)
    s = s.replace("\\x03", "")
    s = s.replace("\\x02", "")
    s = s.replace("\\x1d", "")
    s = s.replace("\\x1D", "")
    s = s.replace("\\x1f", "")
    s = s.replace("\\x1F", "")
    s = s.replace("\\x16", "")
    s = s.replace("\\x0f", "")
    s = s.replace("\\x0F", "")
    return s


# ====================================================================
# Command specific parser
# ====================================================================

class Base:
    def __init__(self, m):
        self.m = m

    def get_message(self):
        return self.m["message"]

    def get_servername(self):
        if "host" in self.m["prefix"]:
            return self.m["prefix"]["nickname"]
        return None

    def get_nickname(self):
        if "host" in self.m["prefix"]:
            return self.m["prefix"]["nickname"]
        return None

    def is_nickname(self, nickname):
        if self.get_nickname() is None:
            return False
        return self.get_nickname().lower() == nickname.lower()

    def get_user(self):
        return self.m["prefix"]["user"]

    def get_host(self):
        return self.m["prefix"]["host"]

    def get_command(self):
        return self.m["command"]

    def is_command(self, command):
        self.get_command() == command

    def get_params(self):
        return self.m["params"]


class JOIN(Base):
    def __init__(self, m):
        super().__init__(m)

    def get_channel(self):
        return self.get_params()[0]


class NICK(Base):
    def __init__(self, m):
        super().__init__(m)

    def get_new_nickname(self):
        return self.get_params()[0]


class MODE(Base):
    def __init__(self, irc, m):
        super().__init__(m)
        self.irc = irc

    def get_target(self):
        return self.get_params()[0]

    def is_channel_mode(self):
        return self.get_target()[:1] in self.irc.chantypes

    def is_user_mode(self):
        return self.get_target()[:1] not in self.irc.chantypes

    def get_modes(self):
        ret = []
        queue = []
        for i in self.get_params()[1:]:
            flag = i[:1]
            if flag == "+" or flag == "-":
                modestring = i[1:]
                queue.extend(self._parse_modes(flag, modestring))
            else:
                self._parse_args(queue, i, ret)
        # Consume any leftover modes
        ret.extend(queue)
        return ret

    def _parse_modes(self, set_flag, modestring):
        modes = []
        for mode in modestring:
            modes.append({"flag": set_flag, "mode": mode,
                          "type": self._mode_type(mode)})
        return modes

    def _parse_args(self, queue, parameter, acc):
        while queue:
            mode = queue.pop(0)
            if mode["type"] == "A":
                mode["param"] = parameter
                acc.append(mode)
                return
            elif mode["type"] == "B":
                mode["param"] = parameter
                acc.append(mode)
                return
            elif mode["type"] == "C" and mode["flag"] == "+":
                mode["param"] = parameter
                acc.append(mode)
                return
            else:
                acc.append(mode)

        # No suitable mode for this parameter, assume a mode without +/-
        acc.append({"flag": "", "mode": parameter,
                    "type": self._mode_type(parameter)})

    def _mode_type(self, mode):
        if mode in self.irc.prefix:
            return "B"  # All prefix modes are type "B".
        if mode in self.irc.chanmodes["A"]:
            return "A"  # List. Always has a parameter.
        if mode in self.irc.chanmodes["B"]:
            return "B"  # Setting. Always has a parameter.
        if mode in self.irc.chanmodes["C"]:
            return "C"  # Setting. Only has parameter when set.
        # Setting. Never has a parameter.
        return "D"  # Default


class NOTICE(Base):
    def __init__(self, irc, m):
        super().__init__(m)
        self.irc = irc

    def is_pm(self):
        return self.m["params"][0] == self.irc.curr_nickname

    def get_msgtarget(self):
        return self.get_nickname() if self.is_pm() else self.m["params"][0]

    def get_text(self):
        return " ".join(self.m["params"][1:])


class PART(Base):
    def __init__(self, m):
        super().__init__(m)

    def get_channel(self):
        return self.get_params()[0]


class KICK(Base):
    def __init__(self, m):
        super().__init__(m)

    def get_channel(self):
        return self.get_params()[0]

    def get_target_user(self):
        return self.get_params()[1]

    def get_comment(self):
        try:
            return self.get_params()[2]
        except IndexError:
            return ""


class PING(Base):
    def __init__(self, m):
        super().__init__(m)
        self.server1 = m["params"][0]
        if len(m["params"]) > 1:
            self.server2 = m["params"][1]


class PRIVMSG(Base):
    def __init__(self, irc, m):
        super().__init__(m)
        self.irc = irc

        self._prep_bot_command()

    def _prep_bot_command(self):
        text_l = self.get_text().split(" ", 1)
        bcmd = text_l[0]
        bcmd_pr = bcmd[:1]
        bcmd = bcmd[1:]
        if len(text_l) == 2:
            args = text_l[1]
        else:
            args = ""
        self.botcmd = bcmd
        self.botcmd_prefix = bcmd_pr
        self.args = args

    def is_pm(self):
        return self.m["params"][0] == self.irc.curr_nickname

    def get_msgtarget(self):
        return self.get_nickname() if self.is_pm() else self.m["params"][0]

    def get_text(self):
        return " ".join(self.m["params"][1:])

    def get_botcmd(self):
        return self.botcmd

    def is_botcmd(self, cmd):
        return self.botcmd == cmd

    def is_botcmd_prefix(self, prefix):
        return self.botcmd_prefix == prefix

    def get_botcmd_prefix(self):
        return self.botcmd_prefix

    def get_args(self):
        return self.args.strip()


class Cap(Base):
    def __init__(self, m):
        super().__init__(m)

    def get_client_id(self):
        return self.m["params"][0]

    def get_subcommand(self):
        return {
            "LS": CapLs,
            "ACK": CapAck
        }[self.m["params"][1]](self.m)


class CapLs:
    def __init__(self, m):
        self.m = m

    def __str__(self):
        return "LS"

    def get_list(self):
        # Break the string to a list and filter empty strings
        return [x for x in self.m["params"][-1].split(" ") if x]

    def get_req(self):
        return [x for x in self.get_list() if x in constants.ircv3_req]


class CapAck:
    def __init__(self, m):
        self.m = m

    def __str__(self):
        return "ACK"

    def get_list(self):
        # Break the string to a list and filter empty strings
        return [x for x in self.m["params"][-1].split(" ") if x]

    def get_enabled(self):
        return [x for x in self.get_list() if x[:1] != "-"]


class RPL_NAMREPLY_353(Base):
    def __init__(self, irc, m):
        super().__init__(m)
        self.irc = irc

    def get_client(self):
        return self.get_params()[0]

    def get_channel_mode(self):
        return self.get_params()[1]

    def get_channel(self):
        return self.get_params()[2]

    def get_names(self):
        ret = {}
        nlist = self.get_params()[3].split()
        for n in nlist:
            prefix = n[:1]
            if prefix in self.irc.prefix.values():
                nick = n[1:]
                ret[nick] = [prefix]
            else:
                ret[n] = [""]

        return ret


class RPL_ENDOFNAMES_366(Base):
    def __init__(self, m):
        super().__init__(m)

    def get_nickname(self):
        return self.get_params()[0]

    def get_channel(self):
        return self.get_params()[1]


# ====================================================================
# Basic Parser
# ====================================================================

dispatch = {
    "353": lambda irc, m: RPL_NAMREPLY_353(irc, m),
    "366": lambda irc, m: RPL_ENDOFNAMES_366(m),
    "CAP": lambda irc, m: Cap(m),
    "JOIN": lambda irc, m: JOIN(m),
    "MODE": lambda irc, m: MODE(irc, m),
    "NICK": lambda irc, m: NICK(m),
    "NOTICE": lambda irc, m: NOTICE(irc, m),
    "PART": lambda irc, m: PART(m),
    "KICK": lambda irc, m: KICK(m),
    "PING": lambda irc, m: PING(m),
    "PRIVMSG": lambda irc, m: PRIVMSG(irc, m),
}


def parse(irc, message):
    m = parse1(message)
    return dispatch.get(m["command"], lambda irc, m: Base(m))(irc, m)


def parse1(message):
    # Remove CRLF
    m = message.replace(b"\r", b"")
    # m = m.replace(b"\n", b"")

    # Decode UTF-8
    m = m.decode("utf8", errors="ignore")

    prefix = None
    if m[0] == ":":
        prefix, m = m[1:].split(" ", 1)
        prefix = parse_prefix(prefix)

    m = m.split(" ", 1)
    command = m[0]
    params = []
    if len(m) == 2:
        params = parse_params(m[1])

    return {"message": message,
            "prefix": prefix,
            "command": command,
            "params": params}


def parse_prefix(prefix):
    ret = {}
    s = prefix.split("@", 1)
    if len(s) == 2:
        ret["host"] = s[1]
        s = s[0].split("!", 1)
        if len(s) == 2:
            ret["user"] = s[1]
        ret["nickname"] = s[0]
        return ret

    ret["nickname"] = s[0]
    return ret


def parse_params(params):
    p = params.split(":", 1)
    if len(p) == 2:
        params = p[0].split(" ", 14)
        if len(params) == 15:
            params[-1] = params[-1] + " :" + p[1]
            return params
        params[-1] = p[1]
        return params

    # Edge case: 14 middle and no space trailing
    return params.split(" ", 14)
