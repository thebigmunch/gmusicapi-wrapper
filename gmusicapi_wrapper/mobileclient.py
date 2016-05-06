# coding=utf-8

"""Mobile Client functionality.

	>>> from gmusicapi_wrapper import MobileClientWrapper
"""

import getpass
import logging

from gmusicapi.clients import Mobileclient

from .base import _BaseWrapper
from .utils import filter_google_songs

logger = logging.getLogger(__name__)


class MobileClientWrapper(_BaseWrapper):
	"""Wrap gmusicapi's Mobileclient client interface to provide extra functionality and conveniences.

	Parameters:
		enable_logging (bool): Enable gmusicapi's debug_logging option.
	"""

	def __init__(self, enable_logging=False):
		super().__init__(Mobileclient, enable_logging=enable_logging)

	def login(self, username=None, password=None, android_id=None):
		"""Authenticate the gmusicapi Mobileclient instance.

		Parameters:
			username (Optional[str]): Your Google Music username. Will be prompted if not given.

			password (Optional[str]): Your Google Music password. Will be prompted if not given.

			android_id (Optional[str]): The 16 hex digits from an Android device ID.
				Default: Use gmusicapi.Mobileclient.FROM_MAC_ADDRESS to create ID from computer's MAC address.

		Returns:
			``True`` on successful login or ``False`` on unsuccessful login.
		"""

		cls_name = type(self).__name__

		if username is None:
			username = input("Enter your Google username or email address: ")

		if password is None:
			password = getpass.getpass("Enter your Google Music password: ")

		if android_id is None:
			android_id = Mobileclient.FROM_MAC_ADDRESS

		try:
			self.api.login(username, password, android_id)
		except OSError:
			logger.exception("{} authentication failed.".format(cls_name))

		if not self.is_authenticated:
			logger.warning("{} authentication failed.".format(cls_name))

			return False

		logger.info("{} authentication succeeded.\n".format(cls_name))

		return True

	def logout(self):
		"""Log out the gmusicapi Mobileclient instance.

		Returns:
			``True`` on success.
		"""

		return self.api.logout()

	@property
	def is_subscribed(self):
		"""Check the subscription status of the gmusicapi client instance.

		Returns:
			``True`` if subscribed, ``False`` if not.
		"""

		return self.api.is_subscribed

	def get_google_songs(self, include_filters=None, exclude_filters=None, all_includes=False, all_excludes=False):
		"""Create song list from user's Google Music library.

		Parameters:
			include_filters (list): A list of ``(field, pattern)`` tuples.
				Fields are any valid Google Music metadata field available to the Mobileclient client.
				Patterns are Python regex patterns.
				Google Music songs are filtered out if the given metadata field values don't match any of the given patterns.

			exclude_filters (list): A list of ``(field, pattern)`` tuples.
				Fields are any valid Google Music metadata field available to the Mobileclient client.
				Patterns are Python regex patterns.
				Google Music songs are filtered out if the given metadata field values match any of the given patterns.

			all_includes (bool): If ``True``, all include_filters criteria must match to include a song.

			all_excludes (bool): If ``True``, all exclude_filters criteria must match to exclude a song.

		Returns:
			A list of Google Music song dicts matching criteria and
			a list of Google Music song dicts filtered out using filter criteria.
		"""

		logger.info("Loading Google Music songs...")

		google_songs = self.api.get_all_songs()

		matched_songs, filtered_songs = filter_google_songs(
			google_songs, include_filters=include_filters, exclude_filters=exclude_filters,
			all_includes=all_includes, all_excludes=all_excludes
		)

		logger.info("Filtered {0} Google Music songs".format(len(filtered_songs)))
		logger.info("Loaded {0} Google Music songs".format(len(matched_songs)))

		return matched_songs, filtered_songs

	def get_google_playlist(self, playlist):
		"""Get playlist information of a user-generated Google Music playlist.

		Parameters:
			playlist (str): Name or ID of Google Music playlist. Names are case-sensitive.
				Google allows multiple playlists with the same name.
				If multiple playlists have the same name, the first one encountered is used.

		Returns:
			dict: The playlist dict as returned by Mobileclient.get_all_user_playlist_contents.
		"""

		logger.info("Loading playlist {0}".format(playlist))

		for google_playlist in self.api.get_all_user_playlist_contents():
			if google_playlist['name'] == playlist or google_playlist['id'] == playlist:
				return google_playlist
		else:
			logger.warning("Playlist {0} does not exist.".format(playlist))
			return {}

	def get_google_playlist_songs(self, playlist, include_filters=None, exclude_filters=None, all_includes=False, all_excludes=False):
		"""Create song list from a user-generated Google Music playlist.

		Parameters:
			playlist (str): Name or ID of Google Music playlist. Names are case-sensitive.
				Google allows multiple playlists with the same name.
				If multiple playlists have the same name, the first one encountered is used.

			include_filters (list): A list of ``(field, pattern)`` tuples.
				Fields are any valid Google Music metadata field available to the Musicmanager client.
				Patterns are Python regex patterns.
				Google Music songs are filtered out if the given metadata field values don't match any of the given patterns.

			exclude_filters (list): A list of ``(field, pattern)`` tuples.
				Fields are any valid Google Music metadata field available to the Musicmanager client.
				Patterns are Python regex patterns.
				Google Music songs are filtered out if the given metadata field values match any of the given patterns.

			all_includes (bool): If ``True``, all include_filters criteria must match to include a song.

			all_excludes (bool): If ``True``, all exclude_filters criteria must match to exclude a song.

		Returns:
			A list of Google Music song dicts in the playlist matching criteria and
			a list of Google Music song dicts in the playlist filtered out using filter criteria.
		"""

		logger.info("Loading Google Music playlist songs...")

		google_playlist = self.get_google_playlist(playlist)

		if not google_playlist:
			return [], []

		playlist_song_ids = [track['trackId'] for track in google_playlist['tracks']]
		playlist_songs = [song for song in self.api.get_all_songs() if song['id'] in playlist_song_ids]

		matched_songs, filtered_songs = filter_google_songs(
			playlist_songs, include_filters=include_filters, exclude_filters=exclude_filters,
			all_includes=all_includes, all_excludes=all_excludes
		)

		logger.info("Filtered {0} Google playlist songs".format(len(filtered_songs)))
		logger.info("Loaded {0} Google playlist songs".format(len(matched_songs)))

		return matched_songs, filtered_songs
