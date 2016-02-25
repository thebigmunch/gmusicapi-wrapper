# coding=utf-8

import getpass
import logging

from gmusicapi.clients import Mobileclient

from .base import _Base
from .utils import filter_google_songs

logger = logging.getLogger(__name__)


class MobileClientWrapper(_Base):
	"""Wraps gmusicapi's Mobileclient client interface to provide extra functionality and conveniences."""

	def __init__(self, enable_logging=False):
		"""

		:param enable_logging: Enable gmusicapi's debug_logging option.
		"""

		self.api = Mobileclient(debug_logging=enable_logging)
		self.api.logger.addHandler(logging.NullHandler())

	def login(self, username=None, password=None, android_id=None):
		"""Authenticate the gmusicapi Mobileclient instance.

		Returns ``True`` on successful login or ``False`` on unsuccessful login.

		:param username: (Optional) Your Google Music username. Will be prompted if not given.

		:param password: (Optional) Your Google Music password. Will be prompted if not given.

		:param android_id: (Optional) The 16 hex digits from an Android device ID.
		  Default: Use gmusicapi.Mobileclient.FROM_MAC_ADDRESS to create ID from computer's MAC address.
		"""

		if not username:
			username = input("Enter your Google username or email address: ")

		if not password:
			password = getpass.getpass("Enter your Google Music password: ")

		if not android_id:
			android_id = Mobileclient.FROM_MAC_ADDRESS

		try:
			self.api.login(username, password, android_id)
		except OSError:
			logger.exception("Sorry, login failed.")

		if not self.api.is_authenticated():
			logger.error("Sorry, login failed.")

			return False

		logger.info("Successfully logged in to Mobileclient.\n")

		return True

	def logout(self):
		"""Log out the gmusicapi Mobileclient instance.

		Returns ``True`` on success.
		"""

		return self.api.logout()

	def get_google_songs(self, include_filters=None, exclude_filters=None, all_includes=False, all_excludes=False):
		"""Create song list from user's Google Music library using gmusicapi's Mobileclient.get_all_songs().

		Returns a list of Google Music song dicts matching criteria and
		a list of Google Music song dicts filtered out using filter criteria.

		:param include_filters: A list of ``(field, pattern)`` tuples.
		  Fields are any valid Google Music metadata field available to the Musicmanager client.
		  Patterns are Python regex patterns.

		  Google Music songs are filtered out if the given metadata field values don't match any of the given patterns.

		:param exclude_filters: A list of ``(field, pattern)`` tuples.
		  Fields are any valid Google Music metadata field available to the Musicmanager client.
		  Patterns are Python regex patterns.

		  Google Music songs are filtered out if the given metadata field values match any of the given patterns.

		:param all_includes: If ``True``, all include_filters criteria must match to include a song.

		:param all_excludes: If ``True``, all exclude_filters criteria must match to exclude a song.
		"""

		logger.info("Loading Google Music songs...")

		google_songs = self.api.get_all_songs()

		if include_filters or exclude_filters:
			matched_songs, filtered_songs = filter_google_songs(
				google_songs, include_filters, exclude_filters, all_includes, all_excludes
			)
		else:
			matched_songs = google_songs
			filtered_songs = []

		logger.info("Filtered {0} Google Music songs".format(len(filtered_songs)))
		logger.info("Loaded {0} Google Music songs".format(len(matched_songs)))

		return matched_songs, filtered_songs
