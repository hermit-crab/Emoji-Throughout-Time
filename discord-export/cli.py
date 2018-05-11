#!/usr/bin/env python
import os
import sys
import re
import argparse
import asyncio
import json
import time
from datetime import datetime, timedelta
from getpass import getpass

import discord
from logzero import logger

from crawl import crawl
from serialize import *
from util import channel_name, filter_channels


async def connect(client):
    if not client.ws:
        asyncio.ensure_future(client.connect())
        logger.info('awaiting client ready state')
        await client.wait_until_ready()


def continuation_get_conf(file):
    conf = {}
    timestamps = {}
    with open(file) as f:
        for l in f:
            type_, data = l.split(',', 1)
            if not conf and type_ == 'run_info':
                conf = json.loads(data)['conf']
            elif type_ == 'message':
                data = json.loads(data)
                ch = data['channel']
                t = data['timestamp']
                current = timestamps.get(ch, 0)
                if t > current:
                    timestamps[ch] = t
    assert conf, f'no run_info found in {file}'
    return argparse.Namespace(**conf), timestamps


def interactive_get_conf(client):
    conf = {}

    servers = ['[Direct Messages]'] + [s.name for s in client.servers]
    print()
    for i, name in enumerate(servers, 1):
        print(f'{i}. {name}')
    i = int(input('Pick a server (number): '))
    print(f'\n==> {servers[i-1]}\n')

    if i == 1:

        channels = list(client.connection.private_channels)
        for i, ch in enumerate(channels, 1):
            recipients = ', '.join([m.name for m in ch.recipients])
            print(f'{i}. {recipients}')
        answer = input('Select channels (numbers, blank for all): ').strip().split()
        conf['mode'] = 'dm'
        if answer:
            channels = [channels[int(i)-1] for i in answer]
            conf['mode'] = 'channels'
            conf['id'] = [ch.id for ch in channels]

    else:

        server = list(client.servers)[i-2]
        channels, skipped = filter_channels(server.channels)
        for reason, ch in skipped:
            logger.info(f'filtering out {ch.id} ({channel_name(ch)}), {reason}')

        # TODO:low channel.category
        print()
        for i, ch in enumerate(channels, 1):
            print(f'{i}. {channel_name(ch)}')
        answer = input('Select channels (numbers, blank for all): ').strip().split()
        conf['mode'] = 'server'
        conf['id'] = server.id
        if answer:
            channels = [channels[int(i)-1] for i in answer]
            conf['mode'] = 'channels'
            conf['id'] = [ch.id for ch in channels]

    print(f'\n==> channels:')
    for ch in channels:
        print(f'{channel_name(ch)}')
    print()

    answer = input('Continue? [Y/n]: ')
    if answer.lower() == 'n':
        raise Exception('cancelled')

    return argparse.Namespace(**conf)


def process_conf(client, conf):

    server = None
    timestamps = {}
    file = container_id = container_name = None
    date_s = '-'.join(datetime.now().isoformat().split(':')[:2])

    if conf.mode == 'dm':

        channels = client.connection.private_channels
        container_id = container_name = 'dm'

    elif conf.mode == 'server':

        server = client.get_server(conf.id)
        assert server, 'server does not exist'
        channels, skipped = filter_channels(server.channels)
        for reason, ch in skipped:
            logger.info(f'filtering out {ch.id} ({channel_name(ch)}), {reason}')
        container_id = server.id
        container_name = server.name

    elif conf.mode == 'channels':

        channels = []
        for id in conf.id:
            channel = client.get_channel(id)
            if not channel:
                logger.error(f'channel {id} does not exist')
            else:
                channels.append(channel)

        assert channels, 'no channels to work with'
        assert len(set(getattr(ch, 'server', None) for ch in channels)) <= 1, \
                'when specifying channels only one source is allowed'

        if isinstance(channels[0], discord.PrivateChannel):
            container_id = 'dm'
            container_name = 'dm'
            if len(channels) == 1:
                container_name = channel_name(channels[0])
        else:
            server = channels[0].server

            container_id = server.id
            container_name = server.name

            channels, bad = filter_channels(channels)
            if bad:
                for reason, ch in bad:
                    logger.error(f'filtering out {ch.id} ({channel_name(ch)}), {reason}')

    assert channels, 'no channels to work with'

    container_name = re.sub(r'[^A-Za-z\d_()-]', '_', container_name)
    file = f'{container_id}.{date_s}.{container_name}.records'

    return server, channels, timestamps, file


async def run(client, conf, creds):
    logger.info('initializing and logging in')
    await client.login(*creds)

    file = None
    if conf.mode == 'continue':
        logger.info('reading previous run info')
        file = conf.file
        conf, timestamps = continuation_get_conf(conf.file)

    await connect(client)
    if conf.mode == 'interactive':
        conf = interactive_get_conf(client)

    server, channels, timestamps_, file_ = process_conf(client, conf)
    if not file:
        file = file_
        timestamps = timestamps_

    logger.info(f'file: {file}')
    server_ = f'{server.id} ({server.name})' if server else 'dm'
    logger.info(f'server: {server_}')
    for ch in channels:
        logger.info(f'channel: {ch.id} ({channel_name(ch)})')

    with open(file, 'a+') as f:
        run_info = {
            'argv': sys.argv[1:],
            'time': time.time(),
            'client.user.id': client.user.id,
            'discord.__version__': discord.__version__,
            'server': server.id if server else None,
            'conf': vars(conf),
            'file': file,
            'channels': [ch.id for ch in channels],
            'timestamps': timestamps
        }

        def format_record(type, data):
            return f'{type},{json.dumps(data)}'

        f.write(format_record('run_info', run_info))
        f.write('\n')
        if server:
            logger.info(f'serializing server info')
            await client.request_offline_members(server)
            f.write(format_record('server_info', serialize_server(server)))
            f.write('\n')
        else:
            logger.info(f'serializing channels info')
            serialized = [serialize_channel(ch) for ch in channels]
            f.write(format_record('channels_info', serialized))
            f.write('\n')

        async for record in crawl(client, channels, timestamps):
            f.write(format_record(*record))
            f.write('\n')

        f.write(format_record('run_finished', {'time': time.time()}))
        f.write('\n')

    await client.close()


def parse_args():
    epilog = '''
        With no arguments will run in an interactive mode.
        Accepts TOKEN or EMAIL/PASS environment variables.
    '''.replace('  ', '')
    parser = argparse.ArgumentParser(prog='discord-extract', epilog=epilog, formatter_class=argparse.RawTextHelpFormatter)
    subparsers = parser.add_subparsers()

    sub = subparsers.add_parser('interactive')
    sub.set_defaults(mode='interactive')

    sub = subparsers.add_parser('dm')
    sub.set_defaults(mode='dm')

    def snowflake(string):
        assert string.isalnum()
        return string

    sub = subparsers.add_parser('channels')
    sub.add_argument('id', type=snowflake, nargs='+', help='must come from the same source')
    sub.set_defaults(mode='channels')

    sub = subparsers.add_parser('server')
    sub.add_argument('id', type=snowflake)
    sub.set_defaults(mode='server')

    sub = subparsers.add_parser('continue')
    sub.add_argument('file')
    sub.set_defaults(mode='continue')

    if not sys.argv[1:]:
        sys.argv.append('interactive')

    conf = parser.parse_args()
    if conf.mode == 'channels' and len(conf.id) != len(set(conf.id)):
        logger.warning('repeated identifiers given')

    return conf


def main():
    logger.info(f'argv: {sys.argv[1:]}')

    conf = parse_args()

    token = os.environ.get('TOKEN')
    email = os.environ.get('EMAIL')
    pw = os.environ.get('PASS')

    if not token and not email:
        token = input('Token (can be empty): ')
    if not token and not email:
        email = input('Email: ')

    if token:
        creds = (token, )
    elif email:
        if not pw:
            pw = getpass()
        creds = (email, pw)
    else:
        logger.error('no credentials are set')
        return 2

    loop = asyncio.get_event_loop()
    client = discord.client.Client()

    try:
        loop.run_until_complete(run(client, conf, creds))
    except (KeyboardInterrupt, Exception) as e:
        if isinstance(e, KeyboardInterrupt):
            logger.info('interrupted')
        else:
            logger.exception(e)
        logger.info('cleaning up')
        loop.run_until_complete(client.logout())
        pending = asyncio.Task.all_tasks()
        gathered = asyncio.gather(*pending)
        try:
            gathered.cancel()
            loop.run_until_complete(gathered)
            gathered.exception()
        except:
            pass
        return 1
    finally:
        loop.close()


if __name__ == '__main__':
    sys.exit(main())
