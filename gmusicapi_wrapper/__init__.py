# coding=utf-8

__title__ = 'gmusicapi_wrapper'
__version__ = "0.5.0"
__license__ = 'MIT'
__copyright__ = 'Copyright 2016 thebigmunch <mail@thebigmunch.me>'

import logging

from . import constants
from . import utils
from .constants import SUPPORTED_PLAYLIST_FORMATS, SUPPORTED_SONG_FORMATS
from .mobileclient import MobileClientWrapper
from .musicmanager import MusicManagerWrapper

# Set default logging handler to avoid "No handlers found" warnings.
logging.getLogger(__name__).addHandler(logging.NullHandler())

# Keep linters from complaining.
(
	constants, utils, SUPPORTED_PLAYLIST_FORMATS, SUPPORTED_SONG_FORMATS,
	MobileClientWrapper, MusicManagerWrapper
)
