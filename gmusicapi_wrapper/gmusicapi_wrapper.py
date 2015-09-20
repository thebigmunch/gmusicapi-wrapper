# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

import getpass
import logging
import os
import re
import shutil
import sys
import tempfile

import mutagen
from gmusicapi import CallFailure
from gmusicapi.clients import Mobileclient, Musicmanager, OAUTH_FILEPATH
from gmusicapi.utils.utils import accept_singleton

from .utils import convert_cygwin_path, exclude_path, filter_google_songs, filter_local_songs, template_to_filepath, walk_depth

logger = logging.getLogger(__name__)

SUPPORTED_FORMATS = ('.mp3', '.flac', '.ogg', '.m4a')

# Compile regex to match Unix absolute paths from Cygwin.
cygpath_re = re.compile("^(?:/[^/]+)*/?$")


class _Base(object):
	"""Common client wrapper methods."""

	@accept_singleton(basestring)
	def get_local_songs(
			self, filepaths, include_filters=None, exclude_filters=None, all_include_filters=False,
			all_exclude_filters=False, filepath_exclude_patterns=None, recursive=True, max_depth=0,
			formats=SUPPORTED_FORMATS):
		"""Load songs from local filepaths.

		Returns a list of local song filepaths matching criteria,
		a list of local song filepaths filtered out using filter criteria,
		and a list of local song filepaths excluded using exclusion criteria.

		:param filepaths: A list of filepaths or a single filepath.

		:param include_filters: A list of ``(field, pattern)`` tuples.
		  Fields are any valid Google Music metadata field available to the Musicmanager client.
		  Patterns are Python regex patterns.

		  Google Music songs are filtered out if the given metadata field values don't match any of the given patterns.

		:param exclude_filters: A list of ``(field, pattern)`` tuples.
		  Fields are any valid Google Music metadata field available to the Musicmanager client.
		  Patterns are Python regex patterns.

		  Google Music songs are filtered out if the given metadata field values match any of the given patterns.

		:param all_include_filters: If ``True``, all include_filters criteria must match to include a song.

		:param all_exclude_filters: If ``True``, all exclude_filters criteria must match to exclude a song.

		:param filepath_exclude_patterns: A list of patterns to exclude.
		  Filepaths are excluded if they match any of the exclude patterns.
		  Patterns are Python regex patterns.

		:param formats: A tuple of supported file extension stings including the dot character.
		  Default: ``('.mp3', '.flac', '.ogg', '.m4a')``
		"""

		logger.info("Loading local songs...")

		included_songs = []
		excluded_songs = []

		for path in filepaths:
			if not isinstance(path, unicode):
				path = path.decode(sys.getfilesystemencoding())

			if os.name == 'nt' and cygpath_re.match(path):
				path = convert_cygwin_path(path)

			if os.path.isdir(path):
				for dirpath, dirnames, filenames in walk_depth(path, recursive, max_depth):
					for filename in filenames:
						if filename.lower().endswith(formats):
							filepath = os.path.join(dirpath, filename)

							if exclude_path(filepath, filepath_exclude_patterns):
								excluded_songs.append(filepath)
							else:
								included_songs.append(filepath)
			elif os.path.isfile(path) and path.lower().endswith(formats):
				if exclude_path(path, filepath_exclude_patterns):
					excluded_songs.append(path)
				else:
					included_songs.append(path)

		matched_songs, filtered_songs = filter_local_songs(
			included_songs, include_filters, exclude_filters, all_include_filters, all_exclude_filters
		)

		logger.info("Excluded {0} local songs.".format(len(excluded_songs)))
		logger.info("Filtered {0} local songs.".format(len(filtered_songs)))
		logger.info("Loaded {0} local songs.".format(len(matched_songs)))

		return matched_songs, filtered_songs, excluded_songs


class MobileClientWrapper(_Base):
	"""Wraps gmusicapi's Mobileclient client interface to provide extra functionality and conveniences."""

	def __init__(self, log=False):
		"""

		:param log: Enable gmusicapi's debug_logging option.
		"""

		self.api = Mobileclient(debug_logging=log)
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
			username = raw_input("Enter your Google username or email address: ")

		if not password:
			password = getpass.getpass(b"Enter your Google Music password: ")

		if not android_id:
			android_id = Mobileclient.FROM_MAC_ADDRESS

		self.api.login(username, password, android_id)

		if not self.api.is_authenticated():
			logger.info("Sorry, login failed.")

			return False

		logger.info("Successfully logged in.\n")

		return True

	def logout(self):
		"""Log out the gmusicapi Mobileclient instance.

		Returns ``True`` on success.
		"""

		return self.api.logout()

	def get_google_songs(self, include_filters=None, exclude_filters=None, all_include_filters=False, all_exclude_filters=False):
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

		:param all_include_filters: If ``True``, all include_filters criteria must match to include a song.

		:param all_exclude_filters: If ``True``, all exclude_filters criteria must match to exclude a song.
		"""

		logger.info("Loading Google Music songs...")

		google_songs = self.api.get_all_songs()

		if include_filters or exclude_filters:
			matched_songs, filtered_songs = filter_google_songs(
				google_songs, include_filters, exclude_filters, all_include_filters, all_exclude_filters
			)
		else:
			matched_songs = google_songs
			filtered_songs = []

		logger.info("Filtered {0} Google Music songs".format(len(filtered_songs)))
		logger.info("Loaded {0} Google Music songs".format(len(matched_songs)))

		return matched_songs, filtered_songs


class MusicManagerWrapper(_Base):
	"""Wraps gmusicapi's Musicmanager client interface to provide extra functionality and conveniences."""

	def __init__(self, log=False):
		"""

		:param log: Enable gmusicapi's debug_logging option.
		"""

		self.api = Musicmanager(debug_logging=log)
		self.api.logger.addHandler(logging.NullHandler())

	def login(self, oauth_filename="oauth", uploader_id=None):
		"""Authenticate the gmusicapi Musicmanager instance.

		Returns ``True`` on successful login or ``False`` on unsuccessful login.

		:param oauth_filename: The filename of the oauth credentials file to use/create for login.
		  Default: ``oauth``

		:param uploader_id: A unique id as a MAC address (e.g. ``'00:11:22:33:AA:BB'``).
		  This should only be provided in cases where the default (host MAC address incremented by 1)
		  won't work.
		"""

		oauth_cred = os.path.join(os.path.dirname(OAUTH_FILEPATH), oauth_filename + '.cred')

		try:
			if not self.api.login(oauth_credentials=oauth_cred, uploader_id=uploader_id):
				try:
					self.api.perform_oauth(storage_filepath=oauth_cred)
				except:
					logger.info("\nUnable to login with specified oauth code.")

				self.api.login(oauth_credentials=oauth_cred, uploader_id=uploader_id)
		except (OSError, ValueError) as e:
			logger.info(e.args[0])
			return False

		if not self.api.is_authenticated():
			logger.info("Sorry, login failed.")

			return False

		logger.info("Successfully logged in.\n")

		return True

	def logout(self, revoke_oauth=False):
		"""Log out the gmusicapi Musicmanager instance.

		Returns ``True`` on success.

		:param revoke_oauth: If ``True``, oauth credentials will be revoked and
		  the corresponding oauth file will be deleted.
		"""

		return self.api.logout(revoke_oauth=revoke_oauth)

	def get_google_songs(self, include_filters=None, exclude_filters=None, all_include_filters=False, all_exclude_filters=False):
		"""Create song list from user's Google Music library using gmusicapi's Musicmanager.get_uploaded_songs().

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

		:param all_include_filters: If ``True``, all include_filters criteria must match to include a song.

		:param all_exclude_filters: If ``True``, all exclude_filters criteria must match to exclude a song.
		"""

		logger.info("Loading Google Music songs...")

		google_songs = self.api.get_uploaded_songs()

		if include_filters or exclude_filters:
			matched_songs, filtered_songs = filter_google_songs(
				google_songs, include_filters, exclude_filters, all_include_filters, all_exclude_filters
			)
		else:
			matched_songs = google_songs
			filtered_songs = []

		logger.info("Filtered {0} Google Music songs".format(len(filtered_songs)))
		logger.info("Loaded {0} Google Music songs".format(len(matched_songs)))

		return matched_songs, filtered_songs

	@accept_singleton(basestring)
	def _download(self, songs, template=os.getcwd()):
		"""Download the given songs one-by-one.

		Yields a 2-tuple ``(download, error)`` of dictionaries.

		    (
		        {'<server id>': '<filepath>'},  # downloaded
                {'<filepath>': '<exception>'}   # error
		    )

		:param songs: A list of Google Music song dicts.

		:param template: A filepath which can include template patterns as definied by
		  :const gmusicapi_wrapper.utils.TEMPLATE_PATTERNS:.
		"""

		for song in songs:
			song_id = song['id']

			try:
				title = song.get('title', "<empty>")
				artist = song.get('artist', "<empty>")
				album = song.get('album', "<empty>")

				logger.debug(
					"Downloading {title} -- {artist} -- {album} ({song_id})".format(
						title=title, artist=artist, album=album, song_id=song_id
					)
				)

				suggested_filename, audio = self.api.download_song(song_id)

				with tempfile.NamedTemporaryFile(delete=False) as temp:
					temp.write(audio)

				metadata = mutagen.File(temp.name, easy=True)

				if "%suggested%" in template:
					template = template.replace("%suggested%", suggested_filename.replace('.mp3', ''))

				if os.name == 'nt' and cygpath_re.match(template):
					template = convert_cygwin_path(template)

				if template != os.getcwd():
					filepath = template_to_filepath(template, metadata) + '.mp3'

					dirname, basename = os.path.split(filepath)

					if basename == '.mp3':
						filepath = os.path.join(dirname, suggested_filename)
				else:
					filepath = suggested_filename

				dirname = os.path.dirname(filepath)

				if dirname:
					try:
						os.makedirs(dirname)
					except OSError:
						if not os.path.isdir(dirname):
							raise

				shutil.move(temp.name, filepath)

				result = ({song_id: filepath}, {})
			except CallFailure as e:
				result = ({}, {song_id: e})

			yield result

	@accept_singleton(basestring)
	def download(self, songs, template=os.getcwd()):
		"""Download the given songs one-by-one.

		Yields a 2-tuple ``(download, error)`` of dictionaries.

		    (
		        {'<server id>': '<filepath>'},  # downloaded
                {'<filepath>': '<exception>'}   # error
		    )

		:param songs: A list of Google Music song dicts.

		:param template: A filepath which can include template patterns as definied by
		  :const gmusicapi_wrapper.utils.TEMPLATE_PATTERNS:.
		"""

		songnum = 0
		total = len(songs)
		errors = {}
		pad = len(str(total))
		results = []

		for result in self._download(songs, template):
			song_id = songs[songnum]['id']
			songnum += 1

			downloaded, error = result

			if downloaded:
				logger.info(
					"({num:>{pad}}/{total}) Successfully downloaded -- {file} ({song_id})".format(
						num=songnum, pad=pad, total=total, file=downloaded[song_id], song_id=song_id
					)
				)
			elif error:
				title = songs[songnum].get('title', "<empty>")
				artist = songs[songnum].get('artist', "<empty>")
				album = songs[songnum].get('album', "<empty>")

				logger.info(
					"({num:>{pad}}/{total}) Error on download -- {title} -- {artist} -- {album} ({song_id})".format(
						num=songnum, pad=pad, total=total, title=title, artist=artist, album=album, song_id=song_id
					)
				)

				errors.update(error)

			results.append(result)

		if errors:
			logger.info("\n\nThe following errors occurred:\n")
			for filepath, e in errors.items():
				logger.info("{file} | {error}".format(file=filepath, error=e))
			logger.info("\nThese files may need to be synced again.\n")

		return results

	@accept_singleton(basestring)
	def _upload(self, filepaths, enable_matching=False, transcode_quality='320k'):
		"""Upload the given filepaths one-by-one.

		Yields a 4-tuple ``(uploaded, matched, not_uploaded, error)`` of dictionaries.

		    (
		        {'<filepath>': '<new server id>'},                 # uploaded
                {'<filepath>': '<new server id>'},                 # matched
                {'<filepath>': '<reason (e.g. ALREADY_EXISTS)>'},  # not_uploaded
                {'<filepath>': '<exception>'}                      # error
		    )

		:param filepaths: A list of filepaths or a single filepath.

		:param enable_matching: If ``True`` attempt to use `scan and match
		  <http://support.google.com/googleplay/bin/answer.py?hl=en&answer=2920799&topic=2450455>`__
		  to avoid uploading every song. This requieres ffmpeg or avconv.

		:param transcode_quality: If int, pass to ffmpeg/avconv ``-q:a`` for libmp3lame `VBR quality
		  <http://trac.ffmpeg.org/wiki/Encode/MP3#VBREncoding>'__.
		  If string, pass to ffmpeg/avconv ``-b:a`` for libmp3lame `CBR quality
		  <http://trac.ffmpeg.org/wiki/Encode/MP3#CBREncoding>'__.
		  Default: '320k'
		"""

		for filepath in filepaths:
			try:
				logger.debug("Uploading -- {}".format(filepath))
				uploaded, matched, not_uploaded = self.api.upload(filepath, enable_matching=enable_matching, transcode_quality=transcode_quality)
				result = (uploaded, matched, not_uploaded, {})
			except CallFailure as e:
				result = ({}, {}, {}, {filepath: e})

			yield result

	@accept_singleton(basestring)
	def upload(self, filepaths, enable_matching=False, transcode_quality='320k', delete_on_success=False):
		"""Upload local filepaths to Google Music.

		Returns a list of 4-tuples ``(uploaded, matched, not_uploaded, error)`` of dictionaries.

		    (
		        {'<filepath>': '<new server id>'},                 # uploaded
                {'<filepath>': '<new server id>'},                 # matched
                {'<filepath>': '<reason (e.g. ALREADY_EXISTS)>'},  # not_uploaded
                {'<filepath>': '<exception>'}                      # error
		    )

		:param filepaths: A list of filepaths or a single filepath.

		:param enable_matching: If ``True`` attempt to use `scan and match
		  <http://support.google.com/googleplay/bin/answer.py?hl=en&answer=2920799&topic=2450455>`__
		  to avoid uploading every song. This requieres ffmpeg or avconv.

		:param transcode_quality: If int, pass to ffmpeg/avconv ``-q:a`` for libmp3lame `VBR quality
		  <http://trac.ffmpeg.org/wiki/Encode/MP3#VBREncoding>'__.
		  If string, pass to ffmpeg/avconv ``-b:a`` for libmp3lame `CBR quality
		  <http://trac.ffmpeg.org/wiki/Encode/MP3#CBREncoding>'__.
		  Default: '320k'

		:param delete_on_success: Delete successfully uploaded local files.
		  Default: False
		"""

		filenum = 0
		total = len(filepaths)
		uploaded_songs = {}
		matched_songs = {}
		not_uploaded_songs = {}
		errors = {}
		pad = len(str(total))
		exist_strings = ["ALREADY_EXISTS", "this song is already uploaded"]

		for result in self._upload(filepaths, enable_matching=enable_matching, transcode_quality=transcode_quality):
			filepath = filepaths[filenum]
			filenum += 1

			uploaded, matched, not_uploaded, error = result

			if uploaded:
				logger.info(
					"({num:>{pad}}/{total}) Successfully uploaded -- {file} ({song_id})".format(
						num=filenum, pad=pad, total=total, file=filepath, song_id=uploaded[filepath]
					)
				)

				uploaded_songs.update(uploaded)

				if delete_on_success:
					try:
						os.remove(filepath)
					except:
						logger.warning("Failed to remove {} after successful upload".format(filepath))
			elif matched:
				logger.info(
					"({num:>{pad}}/{total}) Successfully scanned and matched -- {file} ({song_id})".format(
						num=filenum, pad=pad, total=total, file=filepath, song_id=matched[filepath]
					)
				)

				matched_songs.update(matched)

				if delete_on_success:
					try:
						os.remove(filepath)
					except:
						logger.warning("Failed to remove {} after successful upload".format(filepath))
			elif error:
				logger.warning("({num:>{pad}}/{total}) Error on upload -- {file}".format(num=filenum, pad=pad, total=total, file=filepath))

				errors.update(error)
			else:
				if any(exist_string in not_uploaded[filepath] for exist_string in exist_strings):
					response = "ALREADY EXISTS"
				else:
					response = not_uploaded[filepath]

				logger.info(
					"({num:>{pad}}/{total}) Failed to upload -- {file} | {response}".format(
						num=filenum, pad=pad, total=total, file=filepath, response=response
					)
				)

				not_uploaded_songs.update(not_uploaded)

		if errors:
			logger.info("\n\nThe following errors occurred:\n")

			for filepath, e in errors.items():
				logger.info("{file} | {error}".format(file=filepath, error=e))
			logger.info("\nThese filepaths may need to be synced again.\n")

		return (uploaded_songs, matched_songs, not_uploaded_songs, errors)
