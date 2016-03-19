# coding=utf-8

"""Music Manager functionality.

	>>> from gmusicapi_wrapper import MusicManagerWrapper
"""

import logging
import os
import shutil
import tempfile

import mutagen
from gmusicapi import CallFailure
from gmusicapi.clients import Musicmanager, OAUTH_FILEPATH

from .base import _BaseWrapper
from .constants import CYGPATH_RE, GM_ID_RE
from .decorators import cast_to_list
from .utils import convert_cygwin_path, filter_google_songs, template_to_filepath

logger = logging.getLogger(__name__)


class MusicManagerWrapper(_BaseWrapper):
	"""Wrap gmusicapi's Musicmanager client interface to provide extra functionality and conveniences.

	Parameters:
		enable_logging (bool): Enable gmusicapi's debug_logging option.
	"""

	def __init__(self, enable_logging=False):
		super().__init__(Musicmanager, enable_logging=enable_logging)

	def login(self, oauth_filename="oauth", uploader_id=None):
		"""Authenticate the gmusicapi Musicmanager instance.

		Parameters:
			oauth_filename (str): The filename of the oauth credentials file to use/create for login.
				Default: ``oauth``

			uploader_id (str): A unique id as a MAC address (e.g. ``'00:11:22:33:AA:BB'``).
				This should only be provided in cases where the default (host MAC address incremented by 1) won't work.

		Returns:
			``True`` on successful login, ``False`` on unsuccessful login.
		"""

		cls_name = type(self).__name__

		oauth_cred = os.path.join(os.path.dirname(OAUTH_FILEPATH), oauth_filename + '.cred')

		try:
			if not self.api.login(oauth_credentials=oauth_cred, uploader_id=uploader_id):
				try:
					self.api.perform_oauth(storage_filepath=oauth_cred)
				except OSError:
					logger.exception("\nUnable to login with specified oauth code.")

				self.api.login(oauth_credentials=oauth_cred, uploader_id=uploader_id)
		except (OSError, ValueError):
			logger.exception("{} authentication failed.".format(cls_name))

			return False

		if not self.is_authenticated:
			logger.warning("{} authentication failed.".format(cls_name))

			return False

		logger.info("{} authentication succeeded.\n".format(cls_name))

		return True

	def logout(self, revoke_oauth=False):
		"""Log out the gmusicapi Musicmanager instance.

		Parameters:
			revoke_oauth (bool): If ``True``, oauth credentials will be revoked and the corresponding oauth file will be deleted.

		Returns:
			``True`` on success.
		"""

		return self.api.logout(revoke_oauth=revoke_oauth)

	def get_google_songs(
		self, include_filters=None, exclude_filters=None, all_includes=False, all_excludes=False,
		uploaded=True, purchased=True):
		"""Create song list from user's Google Music library.

		Parameters:
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

			uploaded (bool): Include uploaded songs. Default: ``True``.

			purchased (bool): Include purchased songs. Default: ``True``.

		Returns:
			A list of Google Music song dicts matching criteria and
			a list of Google Music song dicts filtered out using filter criteria.
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
			google_songs, include_filters=include_filters, exclude_filters=exclude_filters,
			all_includes=all_includes, all_excludes=all_excludes
		)

		logger.info("Filtered {0} Google Music songs".format(len(filtered_songs)))
		logger.info("Loaded {0} Google Music songs".format(len(matched_songs)))

		return matched_songs, filtered_songs

	@cast_to_list(0)
	def _download(self, songs, template=os.getcwd()):
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

	@cast_to_list(0)
	def download(self, songs, template=None):
		"""Download Google Music songs.

		Parameters:
			songs (list or dict): Google Music song dict(s).

			template (str): A filepath which can include template patterns.

		Returns:
			A list of result dictionaries.
			::

				[
					{'result': 'downloaded', 'id': song_id, 'filepath': downloaded[song_id]},  # downloaded
					{'result': 'error', 'id': song_id, 'message': error[song_id]}   # error
				]
		"""

		if not template:
			template = os.getcwd()

		songnum = 0
		total = len(songs)
		results = []
		errors = {}
		pad = len(str(total))

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

				results.append({'result': 'downloaded', 'id': song_id, 'filepath': downloaded[song_id]})
			elif error:
				title = songs[songnum].get('title', "<empty>")
				artist = songs[songnum].get('artist', "<empty>")
				album = songs[songnum].get('album', "<empty>")

				logger.info(
					"({num:>{pad}}/{total}) Error on download -- {title} -- {artist} -- {album} ({song_id})".format(
						num=songnum, pad=pad, total=total, title=title, artist=artist, album=album, song_id=song_id
					)
				)

				results.append({'result': 'error', 'id': song_id, 'message': error[song_id]})

		if errors:
			logger.info("\n\nThe following errors occurred:\n")
			for filepath, e in errors.items():
				logger.info("{file} | {error}".format(file=filepath, error=e))
			logger.info("\nThese files may need to be synced again.\n")

		return results

	@cast_to_list(0)
	def _upload(self, filepaths, enable_matching=False, transcode_quality='320k'):
		for filepath in filepaths:
			try:
				logger.debug("Uploading -- {}".format(filepath))
				uploaded, matched, not_uploaded = self.api.upload(
					filepath, enable_matching=enable_matching, transcode_quality=transcode_quality
				)
				result = (uploaded, matched, not_uploaded, {})
			except CallFailure as e:
				result = ({}, {}, {}, {filepath: e})

			yield result

	@cast_to_list(0)
	def upload(self, filepaths, enable_matching=False, transcode_quality='320k', delete_on_success=False):
		"""Upload local songs to Google Music.

		Parameters:
			filepaths (list or str): Filepath(s) to upload.

			enable_matching (bool): If ``True`` attempt to use `scan and match
				<http://support.google.com/googleplay/bin/answer.py?hl=en&answer=2920799&topic=2450455>`__.
				This requieres ffmpeg or avconv.

			transcode_quality (str or int): If int, pass to ffmpeg/avconv ``-q:a`` for libmp3lame `VBR quality
				<http://trac.ffmpeg.org/wiki/Encode/MP3#VBREncoding>'__.
				If string, pass to ffmpeg/avconv ``-b:a`` for libmp3lame `CBR quality
				<http://trac.ffmpeg.org/wiki/Encode/MP3#CBREncoding>'__.
				Default: ``320k``

			delete_on_success (bool): Delete successfully uploaded local files. Default: ``False``

		Returns:
			A list of result dictionaries.
			::

				[
					{'result': 'uploaded', 'filepath': <filepath>, 'id': <song_id>},  # uploaded
					{'result': 'matched', 'filepath': <filepath>, 'id': <song_id>},  # matched
					{'result': 'error', 'filepath': <filepath>, 'message': <error_message>},  # error
					{'result': 'not_uploaded', 'filepath': <filepath>, 'id': <song_id>, 'message': <reason_message>},  # not_uploaded ALREADY_EXISTS
					{'result': 'not_uploaded', 'filepath': <filepath>, 'message': <reason_message>}  # not_uploaded
				]
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

				results.append({'result': 'uploaded', 'filepath': filepath, 'id': uploaded[filepath]})
			elif matched:
				logger.info(
					"({num:>{pad}}/{total}) Successfully scanned and matched -- {file} ({song_id})".format(
						num=filenum, pad=pad, total=total, file=filepath, song_id=matched[filepath]
					)
				)

				results.append({'result': 'matched', 'filepath': filepath, 'id': matched[filepath]})
			elif error:
				logger.warning("({num:>{pad}}/{total}) Error on upload -- {file}".format(num=filenum, pad=pad, total=total, file=filepath))

				results.append({'result': 'error', 'filepath': filepath, 'message': error[filepath]})
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

					results.append({'result': 'not_uploaded', 'filepath': filepath, 'id': song_id, 'message': not_uploaded[filepath]})
				else:
					response = not_uploaded[filepath]

					logger.info(
						"({num:>{pad}}/{total}) Failed to upload -- {file} | {response}".format(
							num=filenum, pad=pad, total=total, file=filepath, response=response
						)
					)

					results.append({'result': 'not_uploaded', 'filepath': filepath, 'message': not_uploaded(filepath)})

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
