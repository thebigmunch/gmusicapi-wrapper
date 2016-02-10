# coding=utf-8

__title__ = 'gmusicapi_wrapper'
__version__ = "0.2.0"
__license__ = 'MIT'
__copyright__ = 'Copyright 2016 thebigmunch <mail@thebigmunch.me>'

import logging

from . import utils
from .gmusicapi_wrapper import MobileClientWrapper, MusicManagerWrapper

# Set default logging handler to avoid "No handlers found" warnings.
logging.getLogger(__name__).addHandler(logging.NullHandler())

# Keep linters from complaining.
(utils, MobileClientWrapper, MusicManagerWrapper)
