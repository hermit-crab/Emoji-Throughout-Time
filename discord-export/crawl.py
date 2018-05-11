import json
from datetime import datetime, timedelta
from urllib.parse import quote

import discord
from logzero import logger

from util import channel_name
from serialize import *


TIME_BEFORE_DISCORD = datetime(2015, 5, 1).timestamp()


async def get_reaction_users(client, reaction):
    r_after = None
    r_limit = 100
    fail404 = False
    started = False
    orig = None
    while True:
        try:
            gen = await client.get_reaction_users(reaction, limit=r_limit, after=r_after)
            users = list(gen)
            started = True
            for user in users:
                yield user
            if len(users) < r_limit:
                break
            r_after = users[-1]
        except discord.NotFound:
            if fail404 or started or isinstance(reaction.emoji, discord.Emoji):
                raise
            orig = reaction.emoji
            fail404 = True
            reaction.emoji = quote(reaction.emoji)

    if orig:
        reaction.emoji = orig


async def crawl(client, channels, timestamps):
    logger.info(f'starting crawl')

    users_seen = set()
    server = None
    if not isinstance(channels[0], discord.PrivateChannel):
        server = channels[0].server

    def ensure_user(user):
        if user.id not in users_seen:
            member = None
            if server:
                member = server.get_member(user.id)
            yield ['user', serialize_user(member or user)]
        users_seen.add(user.id)

    ch_n = 1
    now = datetime.now()
    for ch in channels:
        logger.info(f'==> {ch.id} ({channel_name(ch)})')

        beginning = datetime.fromtimestamp(timestamps.get(ch.id, TIME_BEFORE_DISCORD))
        after = beginning - timedelta(hours=1) # shift one hour to be sure
        first_message = timespan = None
        messages_count = 0
        while True:
            messages = [m async for m in client.logs_from(ch, limit=500, after=after)]
            if not messages:
                if not first_message:
                    logger.info(f'{ch.id} ({channel_name(ch)}) has no messages')
                else:
                    logger.info(f'{ch.id} ({channel_name(ch)}) done')
                break

            messages.sort(key=lambda m: m.timestamp)
            if not first_message:
                first_message = messages[0]
                timespan = now - first_message.timestamp

            for m in messages:
                for record in ensure_user(m.author):
                    yield record

                if m.timestamp <= beginning:
                    continue
                messages_count += 1

                m_obj = serialize_message(m)

                m_obj['reactions'] = []
                for reaction in m.reactions:
                    r_obj = serialize_reaction(reaction)
                    r_obj['users'] = []

                    async for user in get_reaction_users(client, reaction):
                        for record in ensure_user(user):
                            yield record

                        r_obj['users'].append(user.id)

                    m_obj['reactions'].append(r_obj)

                yield ['message', m_obj]

            after = messages[-1]

            covered = now - after.timestamp
            percent = (1-covered/timespan)*100
            at = after.timestamp.isoformat().split('T')[0]
            logger.info(f'{ch_n}/{len(channels)} {ch.id} ({channel_name(ch)}): {percent:.2f}% ({messages_count:,} messages, at {at})')

        ch_n += 1
