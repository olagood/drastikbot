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


def parse(message):
    # Remove CRLF
    m = message.replace(b"\r", b"")
    m = m.replace(b"\n", b"")

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

    return message, prefix, command, params


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
