# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

__title__ = 'gmusicapi_wrapper'
__version__ = "0.1.0"
__license__ = 'MIT'
__copyright__ = 'Copyright 2015 thebigmunch <mail@thebigmunch.me>'

import logging

from . import utils
from .gmusicapi_wrapper import MobileClientWrapper, MusicManagerWrapper

# Keep linters from complaining.
(utils, __version__, MobileClientWrapper, MusicManagerWrapper)

# Set default logging handler to avoid "No handlers found" warnings.
# Copied from requests.
try:  # Python 2.7+
	from logging import NullHandler
except ImportError:
	class NullHandler(logging.Handler):
		def emit(self, record):
			pass

logging.getLogger(__name__).addHandler(NullHandler())

# Clean up.
del NullHandler
