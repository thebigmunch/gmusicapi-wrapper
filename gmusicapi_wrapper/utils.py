# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

import logging
import os
import re

import mutagen

CHARACTER_REPLACEMENTS = {
	'\\': '-', '/': ',', ':': '-', '*': 'x', '<': '[',
	'>': ']', '|': '!', '?': '', '"': "''"
}

TEMPLATE_PATTERNS = {
	'%artist%': 'artist', '%title%': 'title', '%track%': 'tracknumber',
	'%track2%': 'tracknumber', '%album%': 'album', '%date%': 'date',
	'%genre%': 'genre', '%albumartist%': 'performer', '%disc%': 'discnumber'
}

logger = logging.getLogger(__name__)


def _mutagen_fields_to_single_value(file):
	"""Replace mutagen metadata field list values in mutagen tags with the first list value."""

	return dict((k, v[0]) for k, v in mutagen.File(file, easy=True).items())


def _filter_fields(song):
	"""Filter missing artist, album, title, or track fields to improve match accuracy."""

	# Need both tracknumber (mutagen) and track_number (Google Music) here.
	return [field for field in ['artist', 'album', 'title', 'tracknumber', 'track_number'] if field in song and song[field]]


def _normalize_metadata(metadata):
	"""Normalize metadata to improve match accuracy."""

	metadata = unicode(metadata)  # Convert metadata to unicode.
	metadata = metadata.lower()  # Convert to lower case.

	metadata = re.sub('\/\s*\d+', '', metadata)  # Remove "/<totaltracks>" from track number.
	metadata = re.sub('^0+([0-9]+)', r'\1', metadata)  # Remove leading zero(s) from track number.
	metadata = re.sub('^\d+\.+', '', metadata)  # Remove dots from track number.
	metadata = re.sub('[^\w\s]', '', metadata)  # Remove any non-words.
	metadata = re.sub('\s+', ' ', metadata)  # Reduce multiple spaces to a single space.
	metadata = re.sub('^\s+', '', metadata)  # Remove leading space.
	metadata = re.sub('\s+$', '', metadata)  # Remove trailing space.
	metadata = re.sub('^the\s+', '', metadata, re.I)  # Remove leading "the".

	return metadata


def _create_song_key(song):
	"""Create dict key for a Google Muisc song dict or local song file based on metadata in the form of artist|album|title|tracknumber."""

	metadata = []

	song = song if isinstance(song, dict) else _mutagen_fields_to_single_value(song)

	assert isinstance(song, dict)

	# Replace track numbers with 0 if no tag exists.
	if song.get('id'):
		if not song.get('track_number'):
			song['track_number'] = '0'
	else:
		if not song.get('tracknumber'):
			song['tracknumber'] = '0'

	for field in _filter_fields(song):
		metadata.append(_normalize_metadata(song[field]))

	key = '|'.join(metadata)

	return key


def compare_song_collections(src_songs, dest_songs):
	"""Compare two song collections to find missing songs.

	Returns a list of Google Music song dicts or filepaths of local songs from source missing in destination.

	:param src_songs: A list of Google Music song dicts or filepaths of local songs.

	:param dest_songs: A list of Google Music song dicts or filepaths of local songs.
	"""

	missing_songs = []
	src_songs_keyed = {}
	dest_songs_keyed = {}

	for src_song in src_songs:
		src_key = _create_song_key(src_song)
		src_songs_keyed[src_key] = src_song

	for dest_song in dest_songs:
		dest_key = _create_song_key(dest_song)
		dest_songs_keyed[dest_key] = dest_song

	for src_key, src_song in src_songs_keyed.items():
		if src_key not in dest_songs_keyed:
			missing_songs.append(src_song)

	return missing_songs


def exclude_path(path, exclude_patterns):
	"""Exclude file paths based on regex patterns."""

	if exclude_patterns and re.search(exclude_patterns, path):
		return True
	else:
		return False


def _get_valid_filter_fields():
	"""Enumerate valid filter fields."""

	valid_fields = dict((shared, shared) for shared in ['artist', 'title', 'album'])
	valid_fields.update({'albumartist': 'album_artist'})

	return valid_fields


def _match_filters(song, filters, filter_all):
	"""Match a song metadata dict against a set of metadata filters."""

	if filter_all:
		if not all(field in song and re.search(value, song[field], re.I) for field, value in filters):
			return False
	else:
		if not any(field in song and re.search(value, song[field], re.I) for field, value in filters):
			return False

	return True


def filter_google_songs(songs, filters, filter_all):
	"""Match a Google Music song dict against a set of metadata filters.

	Returns a list of Google Music song dicts matching criteria and
	a list of Google Music song dicts filtered out using filter criteria.

	:param songs: A list of Google Music song dicts.

	:param filters: A list of ``(field, pattern)`` tuples.
	  Google Music songs are filtered out if the given metadata fields match the given patterns.

	  Fields are any valid Google Music metadata field available to the Musicmanager client.
	  Patterns are Python regex patterns.

	:param filter_all: If ``True``, all filter criteria must match to filter out a Google Music song.
	"""

	match_songs = []
	filter_songs = []

	if filters:
		norm_filters = []
		valid_fields = _get_valid_filter_fields().items()

		for filter_field, filter_value in filters:
			for mutagen_field, google_field in valid_fields:
				if filter_field == mutagen_field or filter_field == google_field:
					norm_filters.append((google_field, filter_value))

		for song in songs:
			if _match_filters(song, norm_filters, filter_all):
				match_songs.append(song)
			else:
				filter_songs.append(song)
	else:
		match_songs += songs

	return match_songs, filter_songs


def filter_local_songs(filepaths, filters, filter_all):
	"""Match a local file against a set of metadata filters.

	Returns a list of local song filepaths matching criteria and
	a list of local song filepaths filtered out using filter criteria.

	:param filepaths: A list of filepaths.

	:param filters: A list of ``(field, pattern)`` tuples.
	  Local files are filtered out if the given metadata fields match the given patterns.

	  Fields are any valid mutagen metadata field for the file format.
	  Patterns are Python regex patterns.

	:param filter_all: If ``True``, all filter criteria must match to filter out a local file.
	"""

	match_songs = []
	filter_songs = []
	norm_filters = []

	if filters:
		valid_fields = _get_valid_filter_fields().items()

		for filter_field, filter_value in filters:
			for mutagen_field, google_field in valid_fields:
				if filter_field == mutagen_field or filter_field == google_field:
					norm_filters.append((mutagen_field, filter_value))

	for file in filepaths:
		try:
			song = _mutagen_fields_to_single_value(file)
		except:
			logger.warning("{} is not a valid music file!".format(file))
		else:
			if filters:
				if _match_filters(song, norm_filters, filter_all):
					match_songs.append(file)
				else:
					filter_songs.append(file)
			else:
				match_songs.append(file)

	return match_songs, filter_songs


def template_to_file_name(template, metadata):
	"""Create directory structure and file name based on metadata template.

	Returns a filepath.

	:param template: A filepath which can include template patterns as definied by :const TEMPLATE_PATTERNS:.

	:param metadata: A mutagen metadata dict.
	"""

	metadata = metadata if isinstance(metadata, dict) else _mutagen_fields_to_single_value(metadata)

	assert isinstance(metadata, dict)

	drive, path = os.path.splitdrive(template)
	parts = []

	while True:
		newpath, tail = os.path.split(path)

		if newpath == path:
			break

		parts.append(tail)
		path = newpath

	parts.reverse()

	for i, part in enumerate(parts):
		for key in TEMPLATE_PATTERNS:
			if key in part and TEMPLATE_PATTERNS[key] in metadata:
				if key == '%track2%':
					metadata['tracknumber'] = metadata['tracknumber'].zfill(2)
					try:
						metadata.save()
					except:
						pass

				parts[i] = parts[i].replace(key, metadata[TEMPLATE_PATTERNS[key]])

		for char in CHARACTER_REPLACEMENTS:
			if char in parts[i]:
				parts[i] = parts[i].replace(char, CHARACTER_REPLACEMENTS[char])

	if drive:
		filename = os.path.join(drive, os.sep, *parts) + '.mp3'
	else:
		if os.path.isabs(template):
			filename = os.path.join(os.sep, *parts) + '.mp3'
		else:
			filename = os.path.join(*parts) + '.mp3'

	dirname, __ = os.path.split(filename)

	if dirname:
		try:
			os.makedirs(dirname)
		except OSError:
			if not os.path.isdir(dirname):
				raise

	return filename
