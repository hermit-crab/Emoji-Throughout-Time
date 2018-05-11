#!/usr/bin/env python3
import os
import sys
import requests as rq
import shutil
import re
import pickle
import csv
import tempfile
import itertools
from operator import sub
from os.path import join, basename

import pandas as pd
from pandas.tseries.offsets import Second
import matplotlib as mpl
import matplotlib.animation
import matplotlib.pyplot as plt
from PIL import Image

import requests as rq
import emoji

import settings


EMOJI_RX = emoji.get_emoji_regexp()


def open_image(emoji_name, path):
    try:
        return Image.open(join(settings.CUSTOM_EMOJI_DIR, emoji_name))
    except FileNotFoundError:
        pass

    try:
        return Image.open(join(settings.EMOJI_DIR, emoji_name))
    except FileNotFoundError:
        pass

    if not path.startswith(('http:', 'https:')):
        return Image.open(path)

    r = rq.get(path, stream=True)
    r.raise_for_status()
    file = join(settings.CUSTOM_EMOJI_DIR, emoji_name)
    with open(file, 'wb') as f:
        r.raw.decode_content = True
        shutil.copyfileobj(r.raw, f)

    return open_image(emoji_name, path)


def get_emoji_path(ej):
    if ej in emoji.UNICODE_EMOJI:
        file = ej.encode('unicode_escape').decode()
        file = '-'.join(re.findall(r'\\[uU]0*([^\\]+)', file))
        return join(settings.EMOJI_DIR, file + '.png')
    else:
        join(settings.CUSTOM_EMOJI_DIR, emoji + '.png')


def find_emoji_instances(df):
    for i, (idx, row) in enumerate(df.iterrows()):
        if i % 500 == 0:
            print(f'\r{i}/{df.shape[0]} {i/df.shape[0]*100:.3f}%', end='')

        for ej in re.findall(EMOJI_RX, row.Text):
            yield (idx, ej, None)

        for name, path in re.findall(r'<:(.*?):(.*?)>', row.Text):
            yield (idx, name, path)
    print(' done')


def run(edf):
    # preprocess
    ############################################################################

    print('==> preprocessing')

    for alias, name in settings.EMOJI_MAP.items():
        if name is None:
            edf = edf[~(edf.Name == name)]
            continue

        ddf = edf[edf.Name == name]
        if ddf.shape[0]:
            edf[edf.Name == alias]['Path'] = ddf.iloc[0].Path
        edf[edf.Name == alias]['Name'] = name

    name2path = {name: edf[edf.Name == name].iloc[0].Path for name in edf.dropna().Name.unique()}

    # init and collect per frame ranges
    ############################################################################

    period = Second(settings.ROLLING_WINDOW_PERIOD)
    start = edf.index[0] - period + Second(settings.ROLLING_WINDOW_MIN_PERIOD)
    stop = edf.index[-1] - Second(settings.ROLLING_WINDOW_MIN_PERIOD)
    shift = Second(settings.ROLLING_WINDOW_SHIFT)

    export = settings.EXPORT_FORMAT

    frames = []
    for i in itertools.count():
        a = start + shift*i
        b = a + period
        if a > stop:
            break
        frames.append((a,b))

    fig, ax = plt.subplots()
    # ax.set_xlim(d2n(edf.index[0]), d2n(edf.index[-1]))
    # ax.set_aspect('auto')
    aspect = get_aspect(ax)

    # now the crux calc and plotting
    ############################################################################
    frames = frames[:1]

    def animation(frame):
        a, b = frame
        i = frames.index(frame)
        print(f'\rframe {i+1}/{len(frames)} - {a}', end='')
        ax.clear()

        sub_edf = edf[a:b]

        # row = sub_edf.sample(1).iloc[0]
        # path = row.Path or get_emoji_path(row.Name)
        # try:
        #     ax.imshow(open_image(row.Name, path))
        # except Exception as e:
        #     err = f'\nexception reading emoji "{row.Name}" from "{path}": {e}'
        #     print(err, file=sys.stderr)
        # cnt = df.groupby('Name').Name.count().sort_values()[-40:]
        # cnt = cnt / cnt.max() * 2
        # emoji_ids = reversed(list((cnt).items()))

        return ax

    # now show or export
    ############################################################################

    anim = mpl.animation.FuncAnimation(fig, animation, frames=frames, repeat=False)

    if not export:
        plt.show()
    elif export != 'png':
        file = join(settings.OUTPUT_DIR, 'out.' + export)
        print(f'==> exporting to "{file}"')
        anim.save(file)
    else:
        print('==> exporting to frame sequence')
        for frame in frames:
            animation(frame)
            fig.savefig(join(settings.OUTPUT_DIR, f'out{i:04d}.png'))

    print('\n==> done')


def date_fmt(dt, i):
    dt = mpl.dates.num2date(dt)
    if dt.month == 1 or i == 0:
        return dt.strftime('%b\n%Y')
    else:
        return dt.strftime('%b')


def d2n(d):
    return mpl.dates.date2num(d)


def decorate(ax):
    ax.xaxis.set_major_locator(mpl.dates.MonthLocator())
    ax.xaxis.set_major_formatter(mpl.ticker.FuncFormatter(date_fmt))
    plt.setp(ax.get_xmajorticklabels(), linespacing=1.4)


def get_aspect(ax):
    # credits to https://stackoverflow.com/a/42014041
    figW, figH = ax.get_figure().get_size_inches()
    _, _, w, h = ax.get_position().bounds
    disp_ratio = (figH * h) / (figW * w)
    data_ratio = sub(*ax.get_ylim()) / sub(*ax.get_xlim())
    return disp_ratio / data_ratio


def main():
    assert settings.ROLLING_WINDOW_MIN_PERIOD <= settings.ROLLING_WINDOW_PERIOD, 'minimum period can not be greater than the period'

    os.makedirs(settings.CUSTOM_EMOJI_DIR, exist_ok=True)
    os.makedirs(settings.OUTPUT_DIR, exist_ok=True)

    st = os.stat(settings.DATASET)
    cached_db = f'{basename(settings.DATASET)}.{int(st.st_mtime)}.{st.st_size}.p'
    cached_db = join(tempfile.gettempdir(), cached_db)
    try:
        with open(cached_db, 'rb') as f:
            edf = pickle.load(f)
    except FileNotFoundError:
        print('==> loading in database')
        df = pd.read_csv(settings.DATASET)
        df.columns = ['Timestamp', 'Text']
        df['Timestamp'] = pd.to_datetime(df['Timestamp'], unit='s')
        df.set_index('Timestamp', inplace=True)
        df.sort_index(inplace=True)
        df.dropna(inplace=True)

        print('==> scanning for emoji')
        edf = pd.DataFrame.from_records(find_emoji_instances(df))
        edf.columns = ['Timestamp', 'Name', 'Path']
        edf.set_index('Timestamp', inplace=True)

        with open(cached_db, 'wb') as f:
            pickle.dump(edf, f)

    assert edf.shape[0], 'no emoji found in the dataset'

    run(edf)

if __name__ == '__main__':
    main()
