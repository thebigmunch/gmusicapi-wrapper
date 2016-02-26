# coding=utf-8

import logging
import os
import shutil
import tempfile

import mutagen
from gmusicapi import CallFailure
from gmusicapi.clients import Musicmanager, OAUTH_FILEPATH
from gmusicapi.utils.utils import accept_singleton

from .base import _Base
from .constants import CYGPATH_RE, GM_ID_RE
from .utils import convert_cygwin_path, filter_google_songs, template_to_filepath

logger = logging.getLogger(__name__)


class MusicManagerWrapper(_Base):
	"""Wraps gmusicapi's Musicmanager client interface to provide extra functionality and conveniences."""

	def __init__(self, enable_logging=False):
		"""

		:param enable_logging: Enable gmusicapi's debug_logging option.
		"""

		self.api = Musicmanager(debug_logging=enable_logging)
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
				except OSError:
					logger.exception("\nUnable to login with specified oauth code.")

				self.api.login(oauth_credentials=oauth_cred, uploader_id=uploader_id)
		except (OSError, ValueError):
			logger.exception("Sorry, login failed.")
			return False

		if not self.api.is_authenticated():
			logger.error("Sorry, login failed.")

			return False

		logger.info("Successfully logged in to Musicmanager.\n")

		return True

	def logout(self, revoke_oauth=False):
		"""Log out the gmusicapi Musicmanager instance.

		Returns ``True`` on success.

		:param revoke_oauth: If ``True``, oauth credentials will be revoked and
		  the corresponding oauth file will be deleted.
		"""

		return self.api.logout(revoke_oauth=revoke_oauth)

	def get_google_songs(
		self, include_filters=None, exclude_filters=None, all_includes=False, all_excludes=False,
		uploaded=True, purchased=True):
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

		:param all_includes: If ``True``, all include_filters criteria must match to include a song.

		:param all_excludes: If ``True``, all exclude_filters criteria must match to exclude a song.

		:param uploaded: Include uploaded songs.
		  Default: True

		:param purchased: Include purchased songs.
		  Default: True
		"""

		if not uploaded and not purchased:
			raise ValueError("One or both of uploaded/purchased parameters must be True.")

		logger.info("Loading Google Music songs...")

		google_songs = []

		if uploaded:
			google_songs += self.api.get_uploaded_songs()

		if purchased:
			google_songs += self.api.get_purchased_songs()

		matched_songs, filtered_songs = filter_google_songs(
			google_songs, include_filters, exclude_filters, all_includes, all_excludes
		)

		logger.info("Filtered {0} Google Music songs".format(len(filtered_songs)))
		logger.info("Loaded {0} Google Music songs".format(len(matched_songs)))

		return matched_songs, filtered_songs

	@accept_singleton(str)
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

				with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp:
					temp.write(audio)

				metadata = mutagen.File(temp.name, easy=True)

				if "%suggested%" in template:
					template = template.replace("%suggested%", suggested_filename.replace('.mp3', ''))

				if os.name == 'nt' and CYGPATH_RE.match(template):
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

	@accept_singleton(str)
	def download(self, songs, template=None):
		"""Download the given songs one-by-one.

		Yields a 2-tuple ``(download, error)`` of dictionaries.

		    (
		        {'<server id>': '<filepath>'},  # downloaded
                {'<filepath>': '<exception>'}   # error
		    )

		:param songs: A list of Google Music song dicts.

		:param template: A filepath which can include template patterns as defined by the user or
		  :const gmusicapi_wrapper.constants.TEMPLATE_PATTERNS:.
		"""

		if not template:
			template = os.getcwd()

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

	@accept_singleton(str)
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

	@accept_singleton(str)
	def upload(self, filepaths, enable_matching=False, transcode_quality='320k', delete_on_success=False):
		"""Upload local filepaths to Google Music.

		Returns a list of result dictionaries.

			[
		    	{'filepath': <filepath>, 'result': 'uploaded', 'id': <song_id>},                                   # uploaded
				{'filepath': <filepath>, 'result': 'matched', 'id': <song_id>},                                    # matched
				{'filepath': <filepath>, 'result': 'error', 'message': <error_message>},                           # error
				{'filepath': <filepath>, 'result': 'not_uploaded', 'id': <song_id>, 'message': <reason_message>},  # not_uploaded ALREADY_EXISTS
				{'filepath': <filepath>, 'result': 'not_uploaded', 'message': <reason_message>}                    # not_uploaded
			]

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
		results = []
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

				results.append({'filepath': filepath, 'result': 'uploaded', 'id': uploaded[filepath]})
			elif matched:
				logger.info(
					"({num:>{pad}}/{total}) Successfully scanned and matched -- {file} ({song_id})".format(
						num=filenum, pad=pad, total=total, file=filepath, song_id=matched[filepath]
					)
				)

				results.append({'filepath': filepath, 'result': 'matched', 'id': matched[filepath]})
			elif error:
				logger.warning("({num:>{pad}}/{total}) Error on upload -- {file}".format(num=filenum, pad=pad, total=total, file=filepath))

				results.append({'filepath': filepath, 'result': 'error', 'message': error[filepath]})
				errors.update(error)
			else:
				if any(exist_string in not_uploaded[filepath] for exist_string in exist_strings):
					response = "ALREADY EXISTS"

					song_id = GM_ID_RE.search(not_uploaded[filepath]).group(0)

					logger.info(
						"({num:>{pad}}/{total}) Failed to upload -- {file} ({song_id}) | {response}".format(
							num=filenum, pad=pad, total=total, file=filepath, response=response, song_id=song_id
						)
					)

					results.append({'filepath': filepath, 'result': 'not_uploaded', 'id': song_id, 'message': not_uploaded[filepath]})
				else:
					response = not_uploaded[filepath]

					logger.info(
						"({num:>{pad}}/{total}) Failed to upload -- {file} | {response}".format(
							num=filenum, pad=pad, total=total, file=filepath, response=response
						)
					)

					results.append({'filepath': filepath, 'result': 'not_uploaded', 'message': not_uploaded(filepath)})

			success = (uploaded or matched) or (not_uploaded and 'ALREADY_EXISTS' in not_uploaded[filepath])

			if success and delete_on_success:
				try:
					os.remove(filepath)
				except (OSError, PermissionError):
					logger.warning("Failed to remove {} after successful upload".format(filepath))

		if errors:
			logger.info("\n\nThe following errors occurred:\n")

			for filepath, e in errors.items():
				logger.info("{file} | {error}".format(file=filepath, error=e))
			logger.info("\nThese filepaths may need to be synced again.\n")

		return results
