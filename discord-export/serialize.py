import discord


def serialize_user(model):
    obj = {}
    for k in ['name', 'id', 'discriminator', 'avatar', 'bot',
              'avatar_url', 'default_avatar', 'default_avatar_url',
              'display_name']:
        obj[k] = getattr(model, k)

    obj['created_at'] = model.created_at.timestamp()
    obj['default_avatar'] = str(model.default_avatar)
    if isinstance(model, discord.Member):
        obj['roles'] = [e.id for e in model.roles]
        obj['joined_at'] = model.joined_at.timestamp()
        obj['top_role'] = model.top_role.id
        obj['nick'] = model.nick
        obj['color'] = model.color.value
    return obj


def serialize_channel(model):
    if isinstance(model, discord.PrivateChannel):
        return _serialize_private_channel(model)

    obj = {}
    for k in ['name', 'id', 'topic', 'is_private', 'position', 'bitrate']:
        obj[k] = getattr(model, k)

    obj['overwrites'] = [(a.id, [p.value for p in b.pair()]) for a, b in model.overwrites]
    obj['created_at'] = model.created_at.timestamp()
    # obj['type'] = str(model.type) # TODO for later versions
    obj['type'] = ('%s' % {e.value: e.name for e in discord.ChannelType}.get(model.type, model.type))
    return obj


def _serialize_private_channel(model):
    obj = {}
    for k in ['id', 'icon', 'name', 'icon_url', 'is_private']:
        obj[k] = getattr(model, k)

    obj['recipients'] = [serialize_user(e) for e in model.recipients]
    obj['owner'] = serialize_user(model.owner) if model.owner else None
    obj['created_at'] = model.created_at.timestamp()
    obj['type'] = ('%s' % {e.value: e.name for e in discord.ChannelType}.get(model.type, model.type))
    return obj


def serialize_emoji(model):
    obj = {}
    for k in ['name', 'id', 'require_colons', 'managed',
              'managed', 'url']:
        obj[k] = getattr(model, k)

    obj['created_at'] = model.created_at.timestamp()
    obj['roles'] = [e.id for e in model.roles]
    obj['server'] = model.server.id if model.server else None
    return obj


def serialize_message(model):
    obj = {}
    for k in ['content', 'id', 'tts', 'mention_everyone',
              'attachments', 'pinned']:
        obj[k] = getattr(model, k)

    obj['edited_timestamp'] = model.edited_timestamp.timestamp() if model.edited_timestamp else None
    obj['timestamp'] = model.timestamp.timestamp()
    obj['author'] = model.author.id
    obj['channel'] = model.channel.id
    obj['mentions'] = [e.id for e in model.mentions]
    obj['embeds'] = model.embeds # TODO in later versions use .to_dict()
    obj['channel_mentions'] = [e.id for e in model.channel_mentions]
    obj['role_mentions'] = [e.id for e in model.role_mentions]
    return obj


def serialize_role(model):
    obj = {}
    for k in ['name', 'id', 'mentionable',
              'managed', 'position', 'hoist']:
        obj[k] = getattr(model, k)

    obj['color'] = model.color.value
    obj['created_at'] = model.created_at.timestamp()
    obj['permissions'] = model.permissions.value
    return obj


def serialize_reaction(model):
    obj = {}
    for k in ['count', 'emoji', 'me']:
        obj[k] = getattr(model, k)

    if not isinstance(model.emoji, str):
        obj['emoji'] = serialize_emoji(model.emoji)
    return obj


def serialize_server(model):
    obj = {}
    for k in ['name', 'id', 'afk_timeout', 'icon',
              'large', 'mfa_level', 'features', 'splash',
              'icon_url', 'splash_url', 'member_count']:
        obj[k] = getattr(model, k)

    obj['roles'] = [serialize_role(e) for e in model.role_hierarchy]
    obj['region'] = str(model.region)
    obj['created_at'] = model.created_at.timestamp()
    obj['afk_channel'] = model.afk_channel.id if model.afk_channel else None
    obj['members'] = [serialize_user(e) for e in model.members]
    obj['channels'] = [serialize_channel(e) for e in model.channels]
    obj['owner'] = model.owner.id
    obj['verification_level'] = str(model.verification_level)
    obj['default_channel'] = model.default_channel.id if model.default_channel else None
    return obj
