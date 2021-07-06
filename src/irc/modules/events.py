# coding=utf-8

# This is core module for Drastikbot.
# It handles events such as JOIN, PART, QUIT, NICK, MODE and updates irc.py's
# variables for use by the other modules.

'''
Copyright (C) 2018-2019, 2021 drastik.org

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


class Module:
    irc_commands = ["353", "366", "JOIN", "MODE", "NICK", "PART", "QUIT"]


def rpl_namreply_353(i, irc):
    state = i.varget("names", defval={})
    channel = i.msg.get_channel()
    if channel not in state or state[channel] == "ended":
        irc.names[channel] = i.msg.get_names()
        state[channel] = "pending"
        i.varset("names", state)
    else:
        irc.names[channel].update(i.msg.get_names())


def rpl_endofnames_366(i, irc):
    state = i.varget("names", defval={})
    state[i.msg.get_channel()] = "ended"
    i.varset("names", state)


# ====================================================================
# JOIN
# ====================================================================

def join(i, irc):
    nickname = i.msg.get_nickname()
    if nickname == irc.curr_nickname:
        join_bot(i, irc)
    else:
        join_user(i, irc)


def join_bot(i, irc):
    channel = i.msg.get_channel()
    irc.channels[channel] = []

    # Log bot JOIN events
    i.bot["runlog"].info(f"+ Joined {channel}")


def join_user(i, irc):
    nickname = i.msg.get_nickname()
    channel = i.msg.get_channel()
    try:
        irc.names[channel].update({nickname: [""]})
    except KeyError:
        irc.names[channel] = {nickname: [""]}


# ====================================================================
# PART
# ====================================================================

def part(i, irc):
    nickname = i.msg.get_nickname()
    if nickname == irc.curr_nickname:
        part_bot(i, irc)
    else:
        part_user(i, irc)


def part_bot(i, irc):
    channel = i.msg.get_channel()
    del irc.channels[channel]

    # Log bot PART events
    i.bot["runlog"].info(f"- Left {channel}")


def part_user(i, irc):
    nickname = i.msg.get_nickname()
    channel = i.msg.get_channel()
    del irc.names[channel][nickname]


# ====================================================================
# QUIT
# ====================================================================

def quit(i, irc):
    nickname = i.msg.get_nickname()
    for channel in irc.names:
        if nickname in irc.names[channel]:
            del irc.names[channel][nickname]


# ====================================================================
# NICK
# ====================================================================

def nick(i, irc):
    old_nickname = i.msg.get_nickname()
    if old_nickname == irc.curr_nickname:
        nick_bot(i, irc)
    else:
        nick_user(i, irc)


def nick_bot(i, irc):
    new_nickname = i.msg.get_new_nickname()
    irc.curr_nickname = new_nickname


def nick_user(i, irc):
    old_nickname = i.msg.get_nickname()
    new_nickname = i.msg.get_new_nickname()
    for channel in irc.names:
        if old_nickname in irc.names[channel]:
            mode = irc.names[channel].pop(old_nickname)
            irc.names[channel][new_nickname] = mode


# ====================================================================
# MODE
# ====================================================================

def mode(i, irc):
    if i.msg.is_channel_mode():
        for mode in i.msg.get_modes():
            if mode["mode"] in irc.prefix:
                _user_prefix_mode(i, irc, mode)
    else:
        # User modes are not handled yet.
        pass


def _user_prefix_mode(i, irc, mode):
    user = mode["param"]
    target = i.msg.get_target()
    prefix = irc.prefix[mode["mode"]]
    if mode["flag"] == "+":
        insert_prefix(irc, target, user, prefix)
    elif mode["flag"] == "-":
        # There is no way to reliably know the full prefix list without IRCv3.
        # We send a NAMES command to get a new list.
        irc.out.names([target])


def insert_prefix(irc, channel, nickname, new_prefix):
    for index, prefix in enumerate(irc.names[channel][nickname]):
        if is_higher_prefix(new_prefix, prefix):
            irc.names[channel][nickname].insert(index, new_prefix)
            return
    irc.names[channel][nickname].append(new_prefix)


def is_higher_prefix(x, y):
    "Is x a higher channel prefix than y?"
    val = {"": 0, "+": 1, "%": 2, "@": 3, "&": 4, "~": 5}
    return val[x] > val[y]


# ====================================================================
# Main
# ====================================================================

dispatch = {
    "353":  rpl_namreply_353,
    "366":  rpl_endofnames_366,
    "JOIN": join,
    "PART": part,
    "QUIT": quit,
    "NICK": nick,
    "MODE": mode
}


def main(i, irc):
    dispatch[i.msg.get_command()](i, irc)
