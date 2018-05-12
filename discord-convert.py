#!/usr/bin/env python3
import sys
import json
import csv
import re
import argparse
from contextlib import closing
from collections import defaultdict


parser = argparse.ArgumentParser('discord-convert',
            description='convert a database created by discord-export into a digestable format')
parser.add_argument('database', type=argparse.FileType('r'), help='path to the database')
parser.add_argument('user', type=int, nargs='?', help='optional user to extract (numeric identifier)')
parser.add_argument('--skip-reactions', action='store_true', help='don\'t include reactions')
parser.add_argument('--append-id', action='store_true', help='append custom emoji identifier to emoji name, useful if name conflicts are present')
args = parser.parse_args()


user = None if not args.user else str(args.user)
database_file = args.database

seen_emoji = defaultdict(lambda: [])

def check_conflicts(emoji_name, id):
    if emoji_name in seen_emoji and id not in seen_emoji[emoji_name]:
        msg = f'emoji with identical name but different identifier: {emoji_name}'
        seen_emoji[emoji_name].append(id)
        for id in seen_emoji[emoji_name]:
            msg += f'\n    https://cdn.discordapp.com/emojis/{id}.png'
        print(msg, file=sys.stderr)
    elif id not in seen_emoji[emoji_name]:
        seen_emoji[emoji_name].append(id)

writer = csv.writer(sys.stdout)
seen_messages = set()
with closing(database_file):
    for l in database_file:
        type_, data = l.split(',', 1)
        if type_ != 'message':
            continue

        data = json.loads(data)
        if user and user != data['author']:
            continue

        content = data['content']
        id = data['id']

        if not content or id in seen_messages:
            continue

        seen_messages.add(id)

        def sub(m):
            name, id = m.groups()
            if args.append_id:
                name = name + '-' + id
            check_conflicts(name, id)
            return f'<:{name}:https://cdn.discordapp.com/emojis/{id}.png>'

        content = re.sub(r'<:(.*?):(.*?)>', sub, content)

        writer.writerow((data['timestamp'], content))

        if args.skip_reactions:
            continue

        for reaction in data['reactions']:
            if user and user not in reaction['users']:
                continue

            ej = reaction['emoji']
            if not isinstance(ej, str):
                name, id = ej['name'], ej['id']
                if args.append_id:
                    name = name + '-' + id

                check_conflicts(name, id)
                ej = f'(reaction) <:{name}:https://cdn.discordapp.com/emojis/{id}.png>'

            writer.writerow((data['timestamp'], ej))
