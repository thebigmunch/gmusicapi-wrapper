# coding=utf-8

import logging
import os

from gmusicapi.utils.utils import accept_singleton

from.constants import CYGPATH_RE, SUPPORTED_PLAYLIST_FORMATS, SUPPORTED_SONG_FORMATS
from .utils import convert_cygwin_path, exclude_filepaths, filter_local_songs, get_supported_filepaths

logger = logging.getLogger(__name__)


class _Base(object):
	"""Common client wrapper methods."""

	@staticmethod
	@accept_singleton(str)
	def get_local_songs(
			filepaths, include_filters=None, exclude_filters=None, all_includes=False, all_excludes=False,
			exclude_patterns=None, max_depth=float('inf')):
		"""Load songs from local filepaths.

		Returns a list of local song filepaths matching criteria,
		a list of local song filepaths filtered out using filter criteria,
		and a list of local song filepaths excluded using exclusion criteria.

		:param filepaths: A list of filepaths or a single filepath.

		:param include_filters: A list of ``(field, pattern)`` tuples.
		  Fields are any valid mutagen metadata fields.
		  Patterns are Python regex patterns.

		  Local songs are filtered out if the given metadata field values don't match any of the given patterns.

		:param exclude_filters: A list of ``(field, pattern)`` tuples.
		  Fields are any valid mutagen metadata fields.
		  Patterns are Python regex patterns.

		  Local songs are filtered out if the given metadata field values match any of the given patterns.

		:param all_includes: If ``True``, all include_filters criteria must match to include a song.

		:param all_excludes: If ``True``, all exclude_filters criteria must match to exclude a song.

		:param exclude_patterns: A list of patterns to exclude.
		  Filepaths are excluded if they match any of the exclude patterns.
		  Patterns are Python regex patterns.

		:param max_depth: The depth in the directory tree to walk.
		  A depth of '0' limits the walk to the top directory.
		  Default: Infinite depth.
		"""

		logger.info("Loading local songs...")

		supported_filepaths = get_supported_filepaths(filepaths, SUPPORTED_SONG_FORMATS, max_depth)

		included_songs, excluded_songs = exclude_filepaths(supported_filepaths, exclude_patterns)

		matched_songs, filtered_songs = filter_local_songs(
			included_songs, include_filters, exclude_filters, all_includes, all_excludes
		)

		logger.info("Excluded {0} local songs.".format(len(excluded_songs)))
		logger.info("Filtered {0} local songs.".format(len(filtered_songs)))
		logger.info("Loaded {0} local songs.".format(len(matched_songs)))

		return matched_songs, filtered_songs, excluded_songs

	@staticmethod
	@accept_singleton(str)
	def get_local_playlists(filepaths, exclude_patterns=None, max_depth=float('inf')):
		"""Load playlists from local filepaths.

		Returns a list of local playlist filepaths matching criteria
		and a list of local playlist filepaths excluded using exclusion criteria.

		:param filepaths: A list of filepaths or a single filepath.

		:param exclude_patterns: A list of patterns to exclude.
		  Filepaths are excluded if they match any of the exclude patterns.
		  Patterns are Python regex patterns.

		:param max_depth: The depth in the directory tree to walk.
		  A depth of '0' limits the walk to the top directory.
		  Default: Infinite depth.
		"""

		logger.info("Loading local playlists...")

		included_playlists = []
		excluded_playlists = []

		supported_filepaths = get_supported_filepaths(filepaths, SUPPORTED_PLAYLIST_FORMATS, max_depth)

		included_playlists, excluded_playlists = exclude_filepaths(supported_filepaths, exclude_patterns)

		logger.info("Excluded {0} local playlists.".format(len(excluded_playlists)))
		logger.info("Loaded {0} local playlists.".format(len(included_playlists)))

		return included_playlists, excluded_playlists

	@staticmethod
	def get_local_playlist_songs(
		playlist, include_filters=None, exclude_filters=None,
		all_includes=False, all_excludes=False, exclude_patterns=None):
		"""Load songs from local playlist.

		Returns a list of local playlist song filepaths matching criteria,
		a list of local playlist song filepaths filtered out using filter criteria,
		and a list of local playlist song filepaths excluded using exclusion criteria.

		:param playlist: An M3U(8) playlist.

		:param include_filters: A list of ``(field, pattern)`` tuples.
		  Fields are any valid mutagen metadata fields.
		  Patterns are Python regex patterns.

		  Local songs are filtered out if the given metadata field values don't match any of the given patterns.

		:param exclude_filters: A list of ``(field, pattern)`` tuples.
		  Fields are any valid mutagen metadata fields.
		  Patterns are Python regex patterns.

		  Local songs are filtered out if the given metadata field values match any of the given patterns.

		:param all_includes: If ``True``, all include_filters criteria must match to include a song.

		:param all_excludes: If ``True``, all exclude_filters criteria must match to exclude a song.

		:param exclude_patterns: A list of patterns to exclude.
		  playlist are excluded if they match any of the exclude patterns.
		  Patterns are Python regex patterns.
		"""

		logger.info("Loading local playlist songs...")

		if os.name == 'nt' and CYGPATH_RE.match(playlist):
			playlist = convert_cygwin_path(playlist)

		included_songs = []
		excluded_songs = []

		base_filepath = os.path.dirname(os.path.abspath(playlist))

		with open(playlist) as local_playlist:
			for line in local_playlist.readlines():
				line = line.strip()

				if line.lower().endswith(SUPPORTED_SONG_FORMATS):
					path = line

					if not os.path.isabs(path):
						path = os.path.join(base_filepath, path)

					if exclude_filepaths(path, exclude_patterns) or not os.path.isfile(path):
						excluded_songs.append(path)
					else:
						included_songs.append(path)

		matched_songs, filtered_songs = filter_local_songs(
			included_songs, include_filters, exclude_filters, all_includes, all_excludes
		)

		logger.info("Excluded {0} local playlist songs.".format(len(excluded_songs)))
		logger.info("Filtered {0} local playlist songs.".format(len(filtered_songs)))
		logger.info("Loaded {0} local playlist songs.".format(len(matched_songs)))

		return matched_songs, filtered_songs, excluded_songs
