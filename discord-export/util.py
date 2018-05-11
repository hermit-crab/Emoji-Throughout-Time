import discord


def filter_channels(channels):
    good = []
    bad = []
    for ch in channels:
        perms = ch.permissions_for(ch.server.me)
        if ch.type != discord.ChannelType.text:
            bad.append((f'type "{ch.type}"', ch))
        elif not perms.read_message_history:
            bad.append(('lack permissions', ch))
        else:
            good.append(ch)
    return good, bad


def channel_name(ch):
    if not isinstance(ch, discord.PrivateChannel) or ch.name:
        # redundant check for private channel here but eh
        return ch.name

    name = ch.user.name
    if len(ch.recipients) > 1:
        name = 'group-' + name
    return name
