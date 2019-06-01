# coding=utf-8

# This is core module for Drastikbot.
# It provides an ignore list to other drastikbot modules and
# an interface that allows the users to add or remove other users
# from the ignore list.

'''
Copyright (C) 2019 drastik.org

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

import json
from user_auth import user_auth


class Module:
    def __init__(self):
        self.commands = ["ignore", "unignore", "ignored", "ignore_mode"]
        self.helpmsg = [
            "Usage: .ignore <Nickname>",
            "       .unignore <Nickname>",
            "       .ignored",
            "       .ignore_mode <mode> <value>",
            " ",
            "Ignore a list of users. The will not be able to use your",
            "nickname in the supported modules/commands.",
            " ",
            ".ignored : The bot will PM you a list of your ignored users.",
            ".ignore_mode : <mode> :",
            "                  ignore_all: to ignore everyone.",
            "                  registered_only: to ignore unidentified users.",
            "               <value> : True / False",
            "Example: .ignore_mode registered_only true"
        ]


logo = "\x02ignore\x0F"


def is_ignored(i, irc, user_nick, ignore_nick):
    dbc = i.db[1].cursor()
    try:
        dbc.execute("SELECT settings FROM ignore WHERE user = ?;",
                    (user_nick,))
        j = dbc.fetchone()[0]
        o = json.loads(j)
        if o["ignore_all"]:
            return True
        elif o["registered_only"] and not user_auth(i, irc, ignore_nick):
            return True
        elif ignore_nick in o["ignored"]:
            return True
        else:
            return False
    except Exception:
        return False


def ignore(dbc, user_nick, ignore_nick):
    try:
        dbc.execute("SELECT settings FROM ignore WHERE user = ?;",
                    (user_nick,))
        j = dbc.fetchone()[0]
        o = json.loads(j)
        if ignore_nick not in o["ignored"]:
            o["ignored"].append(ignore_nick)
        else:
            return (f"{logo}: \x0311{ignore_nick}\x0F"
                    " is already in your ignore list.")
        j = json.dumps(o)
        dbc.execute("UPDATE ignore SET settings = ? WHERE user = ?;",
                    (j, user_nick))
        return (f"{logo}: \x0311{ignore_nick}\x0F "
                "was added to your ignore list.")
    except Exception:
        return (f"{logo}: An error occured while adding the user {ignore_nick}"
                " to your ignore list")


def unignore(dbc, user_nick, unignore_nick):
    try:
        dbc.execute("SELECT settings FROM ignore WHERE user = ?;",
                    (user_nick,))
        j = dbc.fetchone()[0]
        o = json.loads(j)
        o["ignored"].remove(unignore_nick)
        j = json.dumps(o)
        dbc.execute("UPDATE ignore SET settings = ? WHERE user = ?;",
                    (j, user_nick))
        return (f"{logo}: \x0311{unignore_nick}\x0F"
                " was removed from your ignore list.")
    except Exception:
        return (f"{logo}: \x0311{unignore_nick}\x0F"
                " does not exist in your ignore list.")


def ignored(dbc, user_nick):
    try:
        dbc.execute("SELECT settings FROM ignore WHERE user = ?;",
                    (user_nick,))
        j = dbc.fetchone()[0]
        o = json.loads(j)
        ret = ""
        for i in o["ignored"]:
            ret = f"{ret}{i}, "
        return f'{logo}: {len(o["ignored"])} : {ret[:-2]}'
    except Exception:
        return f"{logo}: There are no ignored users."


def registered_only(dbc, user_nick, value):
    try:
        dbc.execute("SELECT settings FROM ignore WHERE user = ?;",
                    (user_nick,))
        j = dbc.fetchone()[0]
        o = json.loads(j)
        o["registered_only"] = value
        j = json.dumps(o)
        dbc.execute("UPDATE ignore SET settings = ? WHERE user = ?;",
                    (j, user_nick))
        return f'{logo}: registered_only mode set to "{value}".'
    except Exception:
        return ("{logo}: An error occured while "
                "changing the registered_only mode.")


def ignore_all(dbc, user_nick, value):
    try:
        dbc.execute("SELECT settings FROM ignore WHERE user = ?;",
                    (user_nick,))
        j = dbc.fetchone()[0]
        o = json.loads(j)
        o["ignore_all"] = value
        j = json.dumps(o)
        dbc.execute("UPDATE ignore SET settings = ? WHERE user = ?;",
                    (j, user_nick))
        return f'{logo}: ignore_all mode set to "{value}".'
    except Exception:
        return "{logo}: An error occured while changing the ignore_all mode."


def main(i, irc):
    dbc = i.db[1].cursor()
    dbc.execute("CREATE TABLE IF NOT EXISTS ignore "
                "(user TEXT COLLATE NOCASE PRIMARY KEY, "
                "settings TEXT COLLATE NOCASE);")
    dbc.execute(
        "INSERT OR IGNORE INTO ignore VALUES (?, ?);",
        (i.nickname,
         '{"ignored": [], "registered_only": false, "ignore_all": false}'))

    args = i.msg_nocmd.split()

    if i.cmd == "ignore" and len(args) == 1:
        if i.msg_nocmd.lower() == i.nickname.lower():
            return irc.privmsg(i.channel,
                               f"{logo}: You cannot ignore yourself.")
        elif i.msg_nocmd.lower() == irc.var.curr_nickname.lower():
            return irc.privmsg(i.channel,
                               f"{logo}: Ignoring the bot has no effect.")
        return irc.privmsg(i.channel, ignore(dbc, i.nickname, i.msg_nocmd))
    elif i.cmd == "unignore" and len(args) == 1:
        return irc.privmsg(i.channel, unignore(dbc, i.nickname, i.msg_nocmd))
    elif i.cmd == "ignored" and not i.msg_nocmd:
        return irc.privmsg(i.nickname, ignored(dbc, i.nickname))
    elif i.cmd == "ignore_mode" and i.msg_nocmd:
        if args[0] == "registered_only":
            if args[1].lower() == "true":
                return irc.privmsg(i.channel,
                                   registered_only(dbc, i.nickname, True))
            elif args[1].lower() == "false":
                return irc.privmsg(i.channel,
                                   registered_only(dbc, i.nickname, False))
            else:
                return irc.privmsg(
                    i.channel,
                    "Usage: .ignore_mode registered_only < true || false >")
        elif args[0] == "ignore_all":
            if args[1].lower() == "true":
                return irc.privmsg(i.channel,
                                   ignore_all(dbc, i.nickname, True))
            elif args[1].lower() == "false":
                return irc.privmsg(i.channel,
                                   ignore_all(dbc, i.nickname, False))
            else:
                return irc.privmsg(
                    i.channel,
                    "Usage: .ignore_mode ignore_all < true || false >")
        else:
            return irc.privmsg(
                i.channel,
                'Use ".help ignore" to learn how to use this command.')
    else:
        return irc.privmsg(
            i.channel,
            'Use ".help ignore" to learn how to use this command.')
    i.db[1].commit()
