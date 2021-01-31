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
import functools

import numpy as np
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
        if not file:
            file = emoji.UNICODE_EMOJI[ej].strip(':')
            # TODO in this case use custom emoji dir?
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
            edf = edf[~(edf.Name == alias)]
            continue

        ddf = edf[edf.Name == name]
        if ddf.shape[0]:
            edf.loc[edf.Name == alias,'Path'] = ddf.iloc[0].Path
        edf.loc[edf.Name == alias,'Name'] = name

    name2path = {name: edf[edf.Name == name].iloc[0].Path for name in edf.dropna().Name.unique()}

    # init and collect per frame ranges
    ############################################################################

    period = Second(settings.ROLLING_WINDOW_PERIOD)
    start = edf.index[0]
    stop = edf.index[-1] - period
    shift = Second(settings.ROLLING_WINDOW_SHIFT)

    export = settings.EXPORT_FORMAT

    frames = []
    for i in itertools.count():
        a = start + shift*i
        b = a + period
        if a > stop:
            break
        frames.append((a,b))

    # setup axes
    ############################################################################

    fig, ax = plt.subplots()

    xa, xb = d2n(edf.index[0]), d2n(edf.index[-1])
    ya, yb = 0, 1+settings.EMOJI_PAD_TOP
    aspect, _ = get_aspect(ax)
    xrange = xb-xa

    margin = .02
    xmargin = xrange*margin*aspect
    bottom_margin = margin+.1
    top_margin = margin+.1

    image_hspace = xrange*settings.EMOJI_HSPACE
    bar_y = ya-bottom_margin*.7

    def set_lims():
        ax.set_xlim(xa-xmargin, xb+xmargin)
        ax.set_ylim(ya-bottom_margin, yb+top_margin)

    # now the crux calc and plotting
    ############################################################################

    positions = []
    tops = []

    def animation(frame):
        a, b = frame
        i = frames.index(frame)
        print(f'\rframe {i+1}/{len(frames)} - {a}', end='')
        ax.clear()
        set_lims()
        sub_edf = edf[a:b]
        aspect, _ = get_aspect(ax)
        nonlocal tops, positions
        if i == 0:
            tops = []
            positions = []

        # bar
        ax.plot([a, b], [bar_y, bar_y], **settings.BAR_ARGS)

        counted = sub_edf.groupby('Name').Name.count().sort_values()[:-45:-1]
        top = counted.max()

        ref_level = top

        # line
        tops.append((d2n(b), top))
        to_plot = [(x, y/ref_level*.85+settings.EMOJI_PAD_TOP-settings.LINE_PAD_TOP) for x,y in tops]
        ax.plot(*zip(*to_plot), **settings.LINE_ARGS)

        # sort emotes
        items = counted.items()
        if not positions:
            positions = list(counted.keys())
        elif settings.LAX_SORT:
            tmp = counted.to_dict()
            items = [(name, tmp.pop(name)) for name in positions if name in tmp]
            items += [(name, freq) for name, freq in counted.items() if name not in positions]
            items.sort(key=functools.cmp_to_key(lax_cmp), reverse=True)

        # items = list(items)
        # for name, freq in list(items)[:2]:
        #     ax.axhline(freq / ref_level)

        right = xb
        for i, (name, freq) in enumerate(items):
            height = freq / ref_level
            if i == 0 and settings.HEAD_RELATIVITY:
                prev = tops[-settings.HEAD_RELATIVITY-1:][0][1]
                height = freq / prev
            left = right - (height*aspect)

            if right < xa:
                break

            path = name2path.get(name) or get_emoji_path(name)
            try:
                image = open_image(name, path)
            except Exception as e:
                err = f'\n==x error reading emoji "{name}" from "{path}": {e}'
                print(err, file=sys.stderr)
            else:
                ax.imshow(image, extent=[left, right, 0, height], aspect='auto')
                # ax.add_patch(mpl.patches.Rectangle((left, 0), (right-left), height, fill=False, alpha=.5))

            right = left-image_hspace

        decorate(ax, ref_level)
        return [ax]

    # now show or export
    ############################################################################

    anim = mpl.animation.FuncAnimation(fig, animation,
            frames=frames, repeat=True, repeat_delay=5000, interval=settings.ANIMATION_INTERVAL)

    if settings.TIGHT_LAYOUT is not None:
        fig.tight_layout(**settings.TIGHT_LAYOUT)
    fig.subplots_adjust(**settings.SUBPLOT_ADJUST)

    if not export:
        plt.show()
    elif export != 'png':
        file = join(settings.OUTPUT_DIR, 'out.' + export)
        print(f'==> exporting to "{file}"')
        anim.save(file)
    else:
        print('==> exporting to frame sequence')
        for i, frame in enumerate(frames):
            animation(frame)
            fig.savefig(join(settings.OUTPUT_DIR, f'out{i:04d}.png'))

    print('\n==> done')


def date_fmt(dt, i):
    dt = mpl.dates.num2date(dt)
    if dt.month == 1 or i == 0:
        return dt.strftime('%b\n%Y')
    else:
        return dt.strftime('%b')


def count_fmt(n, i, ref_level):
    val = round(n*ref_level)
    err = 10 - val % 10
    val -= val % 10
    if val >= 1000:
        return f'{val/1000:.1f}k'
    elif val <= 0:
        return ''
    else:
        return int(val)


def lax_cmp(a, b):
    (_, freq_a), (_, freq_b) = a, b

    if freq_a/freq_b > .88: # TODO this dont look right
        return 0
    elif freq_a < freq_b:
        return -1
    elif freq_b < freq_a:
        return 1
    else:
        return 0


def d2n(d):
    return mpl.dates.date2num(d)


def decorate(ax, ref_level):
    ax.xaxis.set_major_locator(mpl.dates.MonthLocator())
    ax.xaxis.set_major_formatter(mpl.ticker.FuncFormatter(date_fmt))
    plt.setp(ax.get_xmajorticklabels(), linespacing=1.4)

    if ref_level < 200:
        mul = 50
    elif ref_level < 400:
        mul = 100
    elif ref_level < 1000:
        mul = 200
    else:
        mul = 500

    ax.yaxis.set_major_locator(mpl.ticker.MultipleLocator(mul/ref_level))
    ax.yaxis.set_major_formatter(mpl.ticker.FuncFormatter(lambda n,i: count_fmt(n,i,ref_level)))


def get_aspect(ax):
    # credits to https://stackoverflow.com/a/42014041
    figW, figH = ax.get_figure().get_size_inches()
    _, _, w, h = ax.get_position().bounds
    disp_ratio = (figH * h) / (figW * w)
    data_ratio = sub(*ax.get_ylim()) / sub(*ax.get_xlim())
    return disp_ratio / data_ratio, data_ratio


def main():
    os.makedirs(settings.CUSTOM_EMOJI_DIR, exist_ok=True)
    os.makedirs(settings.OUTPUT_DIR, exist_ok=True)

    st = os.stat(settings.DATASET)
    cached_db = f'{basename(settings.DATASET)}.{int(st.st_mtime)}.{st.st_size}.p'
    cached_db = join(tempfile.gettempdir(), cached_db)
    try:
        with open(cached_db, 'rb') as f:
            edf = pickle.load(f)
    except FileNotFoundError: # TODO invalidate cache in case of any other exception?
        print('==> loading in the dataset')
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

    assert edf.shape[0], 'no emoji found in the dataset' # TODO raise before caching?

    run(edf)


if __name__ == '__main__':
    main()
