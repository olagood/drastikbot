# coding=utf-8

# This is core module for Drastikbot.
# It provides an ignore list to other drastikbot modules and
# an interface that allows the users to add or remove other users
# from the ignore list.

'''
Copyright (C) 2019, 2021 drastik.org

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

import json
from user_auth import user_auth


class Module:
    _bot_commands = ["ignore", "unignore", "ignored", "ignore_mode"]
    manual = {
        "desc": ("Manage your ignore lists. Ignored users will not be able"
                 " to use your nickname in the supported modules."),
        "bot_commands": {
            "ignore": {"usage": lambda x: f"{x}ignore <nickname>"},
            "unignore": {"usage": lambda x: f"{x}unignore <nickname>"},
            "ignored": {"usage": lambda x: f"{x}ignored",
                        "info": "Get your ignore list"},
            "ignore_mode": {
                "usage": lambda x: (f"{x}ignore_mode <mode> <value>"),
                "info": ("Modes: ``ignore_all'' - Ignore everyone"
                         ", ``registered_only'' - Ignore unregistered users"
                         " | Values: true/false"
                         " | Example: .ignore_mode ignore_all true")}
        }
    }


logo = "\x02ignore\x0F"


# ====================================================================
# Functions for use by other modules
# ====================================================================

def is_ignored(i, irc, user, query_nick):
    dbc = i.db[1].cursor()
    try:
        dbc.execute("SELECT settings FROM ignore WHERE user = ?;", (user,))
        j = dbc.fetchone()[0]
        o = json.loads(j)

        if o["ignore_all"]:
            return True
        elif o["registered_only"] and not user_auth(i, irc, query_nick):
            return True
        elif query_nick in o["ignored"]:
            return True
        else:
            return False
    except Exception:
        return False


# ====================================================================
# Ignore
# ====================================================================

def ignore(i, irc, dbc):
    receiver = i.msg.get_nickname()  # The user who issued the command
    args = i.msg.get_args().strip()

    if len(args.split()) != 1:
        m = f"{logo} Usage: {i.msg.get_botcmd_prefix()}ignore <nickname>"
        irc.out.notice(receiver, m)
        return

    if i.msg.is_nickname(args):
        irc.out.notice(receiver, f"{logo}: You cannot ignore yourself.")
        return

    if args.lower() == irc.curr_nickname.lower():
        irc.out.notice(receiver, f"{logo}: Ignoring the bot has no effect.")
        return

    ret = ignore_database(dbc, i.msg.get_nickname(), args)
    if ret == 0:
        m = f"{logo}: \x0311{args}\x0F was added to your ignore list."
    elif ret == 1:
        m = f"{logo}: \x0311{args}\x0F is already in your ignore list."
    else:
        m = f"{logo}: Database error when adding {args} to your ignore list."

    irc.out.notice(receiver, m)


def ignore_database(dbc, user, to_ignore):
    try:
        dbc.execute("SELECT settings FROM ignore WHERE user = ?;", (user,))
        j = dbc.fetchone()[0]
        o = json.loads(j)
        if to_ignore not in o["ignored"]:
            o["ignored"].append(ignore_nick)
        else:
            return 1
        j = json.dumps(o)
        dbc.execute("UPDATE ignore SET settings = ? WHERE user = ?;", (j, user))
        return 0
    except Exception:
        return 2


# ====================================================================
# Unignore
# ====================================================================

def unignore(i, irc, dbc):
    receiver = i.msg.get_nickname()  # The user who issued the command
    args = i.msg.get_args().strip()

    if len(args.split()) != 1:
        m = f"{logo} Usage: {i.msg.get_botcmd_prefix()}unignore <nickname>"
        irc.out.notice(receiver, m)
        return

    ret = unignore_database(dbc, i.msg.get_nickname(), args)
    if ret == 0:
        m = f"{logo}: \x0311{args}\x0F was removed from your ignore list."
    else:
        m = f"{logo}: \x0311{args}\x0F is not in your ignore list."

    irc.out.notice(receiver, m)


def unignore_database(dbc, user, to_unignore):
    try:
        dbc.execute("SELECT settings FROM ignore WHERE user = ?;", (user,))
        j = dbc.fetchone()[0]
        o = json.loads(j)
        o["ignored"].remove(to_unignore)
        j = json.dumps(o)
        dbc.execute("UPDATE ignore SET settings = ? WHERE user = ?;", (j, user))
        return 0
    except Exception:
        return 1


# ====================================================================
# Ignored
# ====================================================================

def ignored(i, irc, dbc):
    receiver = i.msg.get_nickname()  # The user who issued the command
    args = i.msg.get_args().strip()

    if args:
        m = f"{logo} Usage: {i.msg.get_botcmd_prefix()}ignored"
        irc.out.notice(receiver, m)
        return

    ret = ignored_database(dbc, i.msg.get_nickname())
    if ret:
        m = f"{logo}: {ret[0]}: {ret[1]}"
    else:
        m = f"{logo}: There are no ignored users."

    irc.out.notice(receiver, m)


def ignored_database(dbc, user):
    try:
        dbc.execute("SELECT settings FROM ignore WHERE user = ?;", (user,))
        j = dbc.fetchone()[0]
        o = json.loads(j)
        return len(o["ignored"]), ", ".join(o["ignored"])
    except Exception:
        return False


# ====================================================================
# Ignore mode
# ====================================================================

def ignore_mode(i, irc, dbc):
    prefix = i.msg.get_botcmd_prefix()
    receiver = i.msg.get_nickname()  # The user who issued the command
    args = i.msg.get_args().strip()
    args = args.split()

    if len(args) != 2:
        m = f"{logo} Usage: {prefix}ignore_mode <mode> <value>"
        irc.out.notice(receiver, m)
        return

    if args[0] == "registered_only":
        if args[1].lower() == "true":
            value = True
        elif args[1].lower() == "false":
            value = False
        else:
            m = f"Usage: {prefix}ignore_mode registered_only <true|false>"
            irc.out.notice(receiver, m)
            return

        ret = registered_only(dbc, i.msg.get_nickname(), value)
        if ret == 0:
            m = f"{logo}: registered_only mode set to ``{value}''."
        else:
            m = f"{logo}: Error while changing the registered_only mode."

        irc.out.notice(receiver, m)
        return

    if args[0] == "ignore_all":
        if args[1].lower() == "true":
            value = True
        elif args[1].lower() == "false":
            value = False
        else:
            m = f"Usage: {prefix}ignore_mode ignore_all <true|false>"
            irc.out.notice(receiver, m)
            return

        ret = ignore_all(dbc, i.msg.get_nickname(), value)
        if ret == 0:
            m = f"{logo}: ignore_all mode set to ``{value}''."
        else:
            m = f"{logo}: Error while changing the ignore_all mode."

        irc.out.notice(receiver, m)
        return

    m = f"Use ``{prefix}help ignore'' to learn how to use this command."
    irc.out.notice(receiver, m)


def registered_only(dbc, user, value):
    try:
        dbc.execute("SELECT settings FROM ignore WHERE user = ?;", (user,))
        j = dbc.fetchone()[0]
        o = json.loads(j)
        o["registered_only"] = value
        j = json.dumps(o)
        dbc.execute("UPDATE ignore SET settings = ? WHERE user = ?;", (j, user))
        return 0
    except Exception:
        return 1


def ignore_all(dbc, user, value):
    try:
        dbc.execute("SELECT settings FROM ignore WHERE user = ?;", (user,))
        j = dbc.fetchone()[0]
        o = json.loads(j)
        o["ignore_all"] = value
        j = json.dumps(o)
        dbc.execute("UPDATE ignore SET settings = ? WHERE user = ?;", (j, user))
        return 0
    except Exception:
        return 1


# ====================================================================
# Main
# ====================================================================

dispatch = {
    "ignore": ignore,
    "unignore": unignore,
    "ignored": ignored,
    "ignore_mode": ignore_mode
}

def main(i, irc):
    dbc = i.db_disk.cursor()
    nickname = i.msg.get_nickname()
    dbc.execute("""
CREATE TABLE IF NOT EXISTS ignore (
    user TEXT COLLATE NOCASE PRIMARY KEY,
    settings TEXT COLLATE NOCASE
);
""")
    jdef = '{"ignored": [], "registered_only": false, "ignore_all": false}'
    dbc.execute("INSERT OR IGNORE INTO ignore VALUES (?, ?);", (nickname, jdef))

    dispatch[i.msg.get_botcmd()](i, irc, dbc)

    i.db_disk.commit()
