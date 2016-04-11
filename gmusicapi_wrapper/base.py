# coding=utf-8

"""Shared wrapper functionality.

	>>> from gmusicapi_wrapper.base
"""

import logging
import os

from .constants import CYGPATH_RE, SUPPORTED_PLAYLIST_FORMATS, SUPPORTED_SONG_FORMATS
from .decorators import cast_to_list
from .utils import convert_cygwin_path, exclude_filepaths, filter_local_songs, get_supported_filepaths

logger = logging.getLogger(__name__)


class _BaseWrapper:
	"""Common client wrapper methods.

	Parameters:
		enable_logging (bool): Enable gmusicapi's debug_logging option.
	"""

	def __init__(self, cls, enable_logging=False):
		self.api = cls(debug_logging=enable_logging)
		self.api.logger.addHandler(logging.NullHandler())

	@property
	def is_authenticated(self):
		"""Check the authentication status of the gmusicapi client instance.

		Returns:
			``True`` if authenticated, ``False`` if not.
		"""

		return self.api.is_authenticated()

	@staticmethod
	@cast_to_list(0)
	def get_local_songs(
			filepaths, include_filters=None, exclude_filters=None, all_includes=False, all_excludes=False,
			exclude_patterns=None, max_depth=float('inf')):
		"""Load songs from local filepaths.

		Parameters:
			filepaths (list or str): Filepath(s) to search for music files.

			include_filters (list): A list of ``(field, pattern)`` tuples.
				Fields are any valid mutagen metadata fields. Patterns are Python regex patterns.
				Local songs are filtered out if the given metadata field values don't match any of the given patterns.

			exclude_filters (list): A list of ``(field, pattern)`` tuples.
				Fields are any valid mutagen metadata fields. Patterns are Python regex patterns.
				Local songs are filtered out if the given metadata field values match any of the given patterns.

			all_includes (bool): If ``True``, all include_filters criteria must match to include a song.

			all_excludes (bool): If ``True``, all exclude_filters criteria must match to exclude a song.

			exclude_patterns (list or str): Pattern(s) to exclude.
				Patterns are Python regex patterns.
				Filepaths are excluded if they match any of the exclude patterns.

			max_depth (int): The depth in the directory tree to walk.
				A depth of '0' limits the walk to the top directory.
				Default: No limit.

		Returns:
			A list of local song filepaths matching criteria,
			a list of local song filepaths filtered out using filter criteria,
			and a list of local song filepaths excluded using exclusion criteria.

		"""

		logger.info("Loading local songs...")

		supported_filepaths = get_supported_filepaths(filepaths, SUPPORTED_SONG_FORMATS, max_depth=max_depth)

		included_songs, excluded_songs = exclude_filepaths(supported_filepaths, exclude_patterns=exclude_patterns)

		matched_songs, filtered_songs = filter_local_songs(
			included_songs, include_filters=include_filters, exclude_filters=exclude_filters,
			all_includes=all_includes, all_excludes=all_excludes
		)

		logger.info("Excluded {0} local songs".format(len(excluded_songs)))
		logger.info("Filtered {0} local songs".format(len(filtered_songs)))
		logger.info("Loaded {0} local songs".format(len(matched_songs)))

		return matched_songs, filtered_songs, excluded_songs

	@staticmethod
	@cast_to_list(0)
	def get_local_playlists(filepaths, exclude_patterns=None, max_depth=float('inf')):
		"""Load playlists from local filepaths.

		Parameters:
			filepaths (list or str): Filepath(s) to search for music files.

			exclude_patterns (list or str): Pattern(s) to exclude.
				Patterns are Python regex patterns.
				Filepaths are excluded if they match any of the exclude patterns.

			max_depth (int): The depth in the directory tree to walk.
				A depth of '0' limits the walk to the top directory.
				Default: No limit.

		Returns:
			A list of local playlist filepaths matching criteria
			and a list of local playlist filepaths excluded using exclusion criteria.
		"""

		logger.info("Loading local playlists...")

		included_playlists = []
		excluded_playlists = []

		supported_filepaths = get_supported_filepaths(filepaths, SUPPORTED_PLAYLIST_FORMATS, max_depth=max_depth)

		included_playlists, excluded_playlists = exclude_filepaths(supported_filepaths, exclude_patterns=exclude_patterns)

		logger.info("Excluded {0} local playlists".format(len(excluded_playlists)))
		logger.info("Loaded {0} local playlists".format(len(included_playlists)))

		return included_playlists, excluded_playlists

	@staticmethod
	def get_local_playlist_songs(
		playlist, include_filters=None, exclude_filters=None,
		all_includes=False, all_excludes=False, exclude_patterns=None):
		"""Load songs from local playlist.

		Parameters:
			playlist (str): An M3U(8) playlist filepath.

			include_filters (list): A list of ``(field, pattern)`` tuples.
				Fields are any valid mutagen metadata fields. Patterns are Python regex patterns.
				Local songs are filtered out if the given metadata field values don't match any of the given patterns.

			exclude_filters (list): A list of ``(field, pattern)`` tuples.
				Fields are any valid mutagen metadata fields. Patterns are Python regex patterns.
				Local songs are filtered out if the given metadata field values match any of the given patterns.

			all_includes (bool): If ``True``, all include_filters criteria must match to include a song.

			all_excludes (bool): If ``True``, all exclude_filters criteria must match to exclude a song.

			exclude_patterns (list or str): Pattern(s) to exclude.
				Patterns are Python regex patterns.
				Filepaths are excluded if they match any of the exclude patterns.

		Returns:
			A list of local playlist song filepaths matching criteria,
			a list of local playlist song filepaths filtered out using filter criteria,
			and a list of local playlist song filepaths excluded using exclusion criteria.
		"""

		logger.info("Loading local playlist songs...")

		if os.name == 'nt' and CYGPATH_RE.match(playlist):
			playlist = convert_cygwin_path(playlist)

		filepaths = []
		base_filepath = os.path.dirname(os.path.abspath(playlist))

		with open(playlist) as local_playlist:
			for line in local_playlist.readlines():
				line = line.strip()

				if line.lower().endswith(SUPPORTED_SONG_FORMATS):
					path = line

					if not os.path.isabs(path):
						path = os.path.join(base_filepath, path)

					if os.path.isfile(path):
						filepaths.append(path)

		supported_filepaths = get_supported_filepaths(filepaths, SUPPORTED_SONG_FORMATS)

		included_songs, excluded_songs = exclude_filepaths(supported_filepaths, exclude_patterns=exclude_patterns)

		matched_songs, filtered_songs = filter_local_songs(
			included_songs, include_filters=include_filters, exclude_filters=exclude_filters,
			all_includes=all_includes, all_excludes=all_excludes
		)

		logger.info("Excluded {0} local playlist songs".format(len(excluded_songs)))
		logger.info("Filtered {0} local playlist songs".format(len(filtered_songs)))
		logger.info("Loaded {0} local playlist songs".format(len(matched_songs)))

		return matched_songs, filtered_songs, excluded_songs
