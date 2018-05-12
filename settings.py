import matplotlib as mpl
import os

import emoji


BASEDIR = os.path.dirname(__file__)

EMOJI_DIR = os.path.join(BASEDIR, 'emoji')
CUSTOM_EMOJI_DIR = os.path.join(BASEDIR, 'custom_emoji')
OUTPUT_DIR = os.path.join(BASEDIR, 'out')

# csv file without a header of format: timestamp,text
# timestamp is a standard utc timestamp (e.g. 1526007950)
DATASET = 'posts.csv'

# how much time in seconds should one frame cover
ROLLING_WINDOW_PERIOD = 60 * 60 * 24 * 30 * 4 # 4 months

# how much time is shifted for each next frame
ROLLING_WINDOW_SHIFT = 60 * 60 * 24 * 1 # 1 day

# try to not shuffle emoji too frantically
LAX_SORT = True

# should top emote stay the same size (0) or scale relative to
# itself size since before last N frames?
HEAD_RELATIVITY = 3

# None to just show the animation using default matplolib interface
# 'png' to export raw files into OUTPUT_DIR
# anything else will be treated as a desired file extension (e.g. 'mp4')
# matplotlib has to be configured for any video formats to work
EXPORT_FORMAT = None

# animation config, will have no effect with 'png' export
ANIMATION_INTERVAL = 100 # ms

# if certain emoji are simply aliases or you wish for them to be treated as such
# mapping to None is removing emoji from processing completely
EMOJI_MAP = {
    'Thonkang': 'thonkang',
    '©': None,
    # emoji.EMOJI_UNICODE[':headphone:']: emoji.EMOJI_UNICODE[':headbag:']
}

mpl.rcParams.update({
    'figure.figsize': (10, 2.8),
    'image.interpolation': 'bilinear',
})

# Style
################################################################################

# fraction of axes height
EMOJI_PAD_TOP = .2
LINE_PAD_TOP = 0

# emoji horizontal spacing, fraction of axes width
EMOJI_HSPACE = .005

# set to false to not adjust into a tight layout
TIGHT_LAYOUT = dict(pad=1.4)

# adjust boundaries
SUBPLOT_ADJUST = dict(bottom=.15, left=.01)

# sliding bar args
BAR_ARGS = dict(color='#00ffffab', linewidth=1)

# background line args (set alpha to zero to hide completely (1,1,1,0))
LINE_ARGS = dict(color=(1,1,1,.3), linewidth=.4, zorder=-1)

# any further matplotlib options
bg_color = '#36393E'
mpl.rcParams.update({
    'font.size': 8,
    'ytick.labelsize': 6,
    'ytick.major.size': .5,

    'figure.facecolor': bg_color,
    'axes.facecolor': bg_color,
    'savefig.facecolor': bg_color,
    'xtick.color': (1,1,1,.7),
    'ytick.color': (1,1,1,.5),

    'axes.spines.bottom': False,
    'axes.spines.left': False,
    'axes.spines.right': False,
    'axes.spines.top': False,

    'savefig.bbox': 'tight',
    'savefig.pad_inches': .08,
    'xtick.major.size': 0,
    'xtick.labelbottom': True,
    'ytick.major.left': False,

    'ytick.major.right': True,
    'ytick.labelright': True,
})
