import matplotlib as mpl
import os

BASEDIR = os.path.dirname(__file__)

EMOJI_DIR = os.path.join(BASEDIR, 'emoji')
CUSTOM_EMOJI_DIR = os.path.join(BASEDIR, 'custom_emoji')
OUTPUT_DIR = os.path.join(BASEDIR, 'out')

# csv file without a header of format: timestamp,text
# timestamp is a standard utc timestamp (e.g. 1526007950)
DATASET = 'posts.csv'

# how much time in seconds should one frame cover
ROLLING_WINDOW_PERIOD = 60 * 60 * 24 * 30 * 4 # 4 months

# for when going outside of the edges of full timespan of the dataset
# setting this to ROLLING_WINDOW_PERIOD will not allow going off edges
ROLLING_WINDOW_MIN_PERIOD = 60 * 60 * 24 * 30 * 2 # 2 months

# how much time is shifted for each next frame
ROLLING_WINDOW_SHIFT = 60 * 60 * 24 * 30 # 1 day

# if certain emoji are simply aliases or you wish for them to be treated as such
# then put them into this mapping.
EMOJI_MAP = {
    'Thonkang': 'thonkang',
    # 'Thonk': 'thonkang',
    # '😀': '😃',
    '©': None # Mapping to None is removing emoji from processing
}

# None to just show the animation using default matplolib interface
# 'png' to export raw files into OUTPUT_DIR
# anything else will be treated as a desired file extension (e.g. 'mp4')
EXPORT_FORMAT = None

# animation config, will have no effect with 'png' export
ANIMATION_INTERVAL = 200 # ms
FIRST_FRAME_DURATION = ANIMATION_INTERVAL
LAST_FRAME_DURATION = 15000

# any desired customizations to the matplotlib config
mpl.rcParams.update({
    'figure.figsize': (15, 7),
})
