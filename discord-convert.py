#!/usr/bin/env python3
import sys
import json
import csv
import re
import argparse

parser = argparse.ArgumentParser('discord-convert',
            description='convert a database created by discord-export into a digestable format')
parser.add_argument('database', help='path to the database')
parser.add_argument('user', type=int, nargs='?', help='optional user to extract (numeric identifier)')
parser.add_argument('--skip-reactions', action='store_true', help='don\'t include reactions')
parser.add_argument('--append-id', action='store_true', help='append custom emoji identifier to its name, useful if name conflicts are present')
args = parser.parse_args()

user = None if not args.user else str(args.user)
database = args.database

seen_identifiers = set()
writer = csv.writer(sys.stdout)
with open(database) as f:
    for l in f:
        type_, data = l.split(',', 1)
        if type_ != 'message':
            continue

        data = json.loads(data)
        if user and user != data['author']:
            continue

        content = data['content']
        id = data['id']
        if not content or id in seen_identifiers:
            continue

        seen_identifiers.add(id)

        if args.append_id:
            content = re.sub(r'<:(.*?):(.*?)>', r'<:\1:https://cdn.discordapp.com/emojis/\2.png>', content)
        else:
            content = re.sub(r'<:(.*?):(.*?)>', r'<:\1-\2:https://cdn.discordapp.com/emojis/\2.png>', content)

        writer.writerow((data['timestamp'], content))

        if args.skip_reactions:
            continue

        for reaction in data['reactions']:
            if user and user not in reaction['users']:
                continue

            ej = reaction['emoji']
            if not isinstance(ej, str):
                if args.append_id:
                    ej = '(reaction) <:{name}-{id}:https://cdn.discordapp.com/emojis/{id}.png>'.format(**ej)
                else:
                    ej = '(reaction) <:{name}:https://cdn.discordapp.com/emojis/{id}.png>'.format(**ej)

            writer.writerow((data['timestamp'], ej))
