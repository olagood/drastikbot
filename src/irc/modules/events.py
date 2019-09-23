# coding=utf-8

# This is core module for Drastikbot.
# It handles events such as JOIN, PART, QUIT, NICK, MODE and updates irc.py's
# variables for use by the other modules.

'''
Copyright (C) 2018-2019 drastik.org

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
    def __init__(self):
        self.msgtypes = ['JOIN', 'QUIT', 'PART', 'MODE', '353',
                         '324']
        self.auto = True


def dict_prep(irc, msg):
    '''
    Prepare 'irc.var.namesdict'
    This function inserts a new key with the channels name in
    'irc.var.namesdict' for the other functions to use.
    '''
    # Verify that this is indeed a channel before adding it to 'namesdict'.
    # This is so that we can avoid adding the users (or services) that send
    # privmsges with to bot.
    chan_prefix_ls = ['#', '&', '+', '!']
    if msg.channel[0] not in chan_prefix_ls:
        return

    if msg.channel not in irc.var.namesdict:
        irc.var.namesdict[msg.channel] = [[], {}]


def _rpl_namreply_353(irc, msg):
    dict_prep(irc, msg)
    namesdict = irc.var.namesdict[msg.channel]
    namesdict[0] = [msg.cmd_ls[2]]
    modes = ['~', '&', '@', '%', '+']
    for i in msg.msg_params.split():
        if i[:1] in modes:
            namesdict[1][i[1:]] = [i[:1]]
        else:
            namesdict[1][i] = []
    irc.send(('MODE', msg.channel))  # Reply handled by rpl_channelmodeis


def _rpl_channelmodeis_324(irc, msg):
    '''Handle reply to: "MODE #channel" to save the channel modes'''
    channel = msg.cmd_ls[2]
    m = list(msg.cmd_ls[3][1:])
    for idx, mode in reversed(list(enumerate(m))):
        irc.var.namesdict[channel][0].append(mode)


def _join(irc, msg):
    try:
        dict_prep(irc, msg)
        irc.var.namesdict[msg.channel][1][msg.nickname] = []
    except KeyError:
        # This occures when first joining a channel for the first time.
        # We take advantage of this to efficiently:
        # Get the hostmask and call a function to calculate and set
        # the irc.var.msg_len variable.
        if msg.nickname == irc.var.curr_nickname:
            nick_ls = (msg.nickname, msg.username, msg.hostname)
            irc.var.bot_hostmask = msg.hostname
            irc.set_msg_len(nick_ls)


def _part(irc, msg):
    try:
        del irc.var.namesdict[msg.channel][1][msg.nickname]
    except KeyError:
        # This should not be needed now that @rpl_namreply()
        # is fixed, but the exception will be monitored for
        # possible future reoccurance, before it is removed.
        irc.var.log.debug('KeyError @Events.irc_part(). Err: 01')


def _quit(irc, msg):
    for chan in irc.var.namesdict:
        if msg.nickname in irc.var.namesdict[chan][1]:
            del irc.var.namesdict[chan][1][msg.nickname]


def _nick(irc, msg):
    for chan in irc.var.namesdict:
        try:
            k = irc.var.namesdict[chan][1]
            k[msg.params] = k.pop(msg.nickname)
        except KeyError:
            # This should not be needed now that @rpl_namreply()
            # is fixed, but the exception will be monitored for
            # possible future reoccurance, before it is removed.
            irc.var.log.debug('KeyError @Events.irc_part(). Err: 01')


def user_mode(irc, msg):
    # MODE used on a user
    m_dict = {'q': '~', 'a': '&', 'o': '@', 'h': '%', 'v': '+'}
    channel = msg.cmd_ls[1]
    m = msg.cmd_ls[2]    # '+ooo' or '-vvv'
    modes = list(m[1:])  # [o,o,o,o]
    if m[:1] == '+':  # Add (+) modes
        for idx, mode in reversed(list(enumerate(modes))):
            nick = msg.cmd_ls[3+idx]
            try:
                irc.var.namesdict[channel][1][nick].append(
                    m_dict[mode])
            except KeyError:
                # This should not be needed now that @rpl_namreply()
                # is fixed, but the exception will be monitored for
                # possible future reoccurance, before it is removed.
                irc.var.log.debug('KeyError @Events.irc_mode(). Err: 01')
                irc.var.namesdict[channel][1].update({nick: modes[idx]})
    elif m[:1] == '-':  # Remove (-) modes
        for i, e in reversed(list(enumerate(modes))):
            try:
                irc.var.namesdict[channel][1][msg.cmd_ls[3+i]].remove(
                    m_dict[modes[i]])
            except Exception:
                irc.var.log.debug('AttributeError @Events.irc_mode(). '
                                  'Err: 02')
                # Quick hack for to avoid crashes in cases where a mode
                # doesnt use a nickname. (For instance setting +b on a
                # hostmask). Should be properly handled, after this
                # method gets broken into smaller parts.


def channel_mode(irc, msg):
    # MODE used on a channel
    channel = msg.cmd_ls[1]
    m = msg.cmd_ls[2]    # '+ooo' or '-vvv'
    modes = list(m[1:])  # [o,o,o,o]
    if m[:1] == '+':  # Add (+) modes
        for idx, mode in reversed(list(enumerate(modes))):
            irc.var.namesdict[channel][0].append(mode)
    elif m[:1] == '-':  # Remove (-) modes
        for idx, mode in reversed(list(enumerate(modes))):
            irc.var.namesdict[channel][0].remove(mode)


def _mode(irc, msg):
    dict_prep(irc, msg)
    if len(msg.cmd_ls) > 3:
        user_mode(irc, msg)
    elif msg.cmd_ls[1] == irc.var.curr_nickname:
        # Set the bot's server modes.
        irc.var.botmodes.extend(
            list(msg.msg_ls[3].replace("+", "").replace(":", "")))
    else:
        channel_mode(irc, msg)


def main(i, irc):
    d = {
        '353':  _rpl_namreply_353,
        '324':  _rpl_channelmodeis_324,
        'JOIN': _join,
        'PART': _part,
        'QUIT': _quit,
        'NICK': _nick,
        'MODE': _mode
        }
    d[i.msgtype](irc, i)
