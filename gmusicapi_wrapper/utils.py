# coding=utf-8

import logging
import os
import re
import subprocess

import mutagen
from gmusicapi.utils.utils import accept_singleton

from .constants import CHARACTER_REPLACEMENTS, CYGPATH_RE, TEMPLATE_PATTERNS

logger = logging.getLogger(__name__)


def convert_cygwin_path(path):
	"""Convert Unix path from Cygwin to Windows path."""

	return subprocess.check_output(["cygpath", "-aw", path]).strip()  # pragma: no cover


def _get_mutagen_metadata(filepath):
	"""Get mutagen metadata dict from a file."""

	return mutagen.File(filepath, easy=True)


def _mutagen_fields_to_single_value(metadata):
	"""Replace mutagen metadata field list values in mutagen tags with the first list value."""

	return dict((k, v[0]) for k, v in metadata.items() if v)


def _split_field_to_single_value(field):
	"""Convert number field values split by a '/' to a single number value."""

	split_field = re.match(r'(\d+)/\d+', field)

	return split_field.group(1) or field


def _filter_fields(song):
	"""Filter missing artist, album, title, or track fields to improve match accuracy."""

	# Need both tracknumber (mutagen) and track_number (Google Music) here.
	return [field for field in ['artist', 'album', 'title', 'tracknumber', 'track_number'] if field in song and song[field]]


def _normalize_metadata(metadata):
	"""Normalize metadata to improve match accuracy."""

	metadata = str(metadata)  # Convert metadata to unicode.
	metadata = metadata.lower()  # Convert to lower case.

	metadata = re.sub(r'\/\s*\d+', '', metadata)  # Remove "/<totaltracks>" from track number.
	metadata = re.sub(r'^0+([0-9]+)', r'\1', metadata)  # Remove leading zero(s) from track number.
	metadata = re.sub(r'^\d+\.+', '', metadata)  # Remove dots from track number.
	metadata = re.sub(r'[^\w\s]', '', metadata)  # Remove any non-words.
	metadata = re.sub(r'\s+', ' ', metadata)  # Reduce multiple spaces to a single space.
	metadata = re.sub(r'^\s+', '', metadata)  # Remove leading space.
	metadata = re.sub(r'\s+$', '', metadata)  # Remove trailing space.
	metadata = re.sub(r'^the\s+', '', metadata, re.I)  # Remove leading "the".

	return metadata


def _create_song_key(song):
	"""Create dict key for a Google Muisc song dict or local song file based on metadata in the form of artist|album|title|tracknumber."""

	metadata = []

	song = song if isinstance(song, dict) else _mutagen_fields_to_single_value(_get_mutagen_metadata(song))

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


@accept_singleton(str, 0)
def get_supported_filepaths(filepaths, supported_extensions, max_depth=float('inf')):
	"""Get filepaths with supported extensions from given filepaths.

	:param filepaths: A list of filepaths or a single filepath.

	:param supported_extensions: A tuple of supported extensions or a single extension string.
	"""

	supported_filepaths = []

	for path in filepaths:
		if os.name == 'nt' and CYGPATH_RE.match(path):
			path = convert_cygwin_path(path)

		if os.path.isdir(path):
			for root, _, files in walk_depth(path, max_depth):
				for f in files:
					if f.lower().endswith(supported_extensions):
						supported_filepaths.append(os.path.join(root, f))
		elif os.path.isfile(path) and path.lower().endswith(supported_extensions):
			supported_filepaths.append(path)

	return supported_filepaths


@accept_singleton(str, 0)
def exclude_filepaths(filepaths, exclude_patterns=None):
	"""Exclude file paths based on regex patterns.

	Returns a list of filepaths to include and a list of filepaths to exclude.

	:param filepaths: A list of filepaths or a single filepath.

	:param exclude_patterns: A list of Python regex patterns.
	"""

	if not exclude_patterns:
		return filepaths, []

	exclude_re = re.compile("|".join(pattern for pattern in exclude_patterns))

	included_songs = []
	excluded_songs = []

	for filepath in filepaths:
		if exclude_patterns and exclude_re.search(filepath):
			excluded_songs.append(filepath)
		else:
			included_songs.append(filepath)

	return included_songs, excluded_songs


def _get_valid_filter_fields():
	"""Enumerate valid filter fields."""

	valid_fields = dict((shared, shared) for shared in ['artist', 'title', 'album'])
	valid_fields.update({'albumartist': 'album_artist'})

	return valid_fields


def _check_filters(song, include_filters=None, exclude_filters=None, all_includes=False, all_excludes=False):
	"""Check a song metadata dict against a set of metadata filters."""

	include = True

	if include_filters:
		if all_includes:
			if not all(field in song and re.search(value, song[field], re.I) for field, value in include_filters):
				include = False
		else:
			if not any(field in song and re.search(value, song[field], re.I) for field, value in include_filters):
				include = False

	if exclude_filters:
		if all_excludes:
			if all(field in song and re.search(value, song[field], re.I) for field, value in exclude_filters):
				include = False
		else:
			if any(field in song and re.search(value, song[field], re.I) for field, value in exclude_filters):
				include = False

	return include


def _normalize_filters(filters, origin=None):
	normalized_filters = []

	if filters:
		valid_fields = _get_valid_filter_fields().items()

		for filter_field, filter_value in filters:
			for mutagen_field, google_field in valid_fields:
				if filter_field == mutagen_field or filter_field == google_field:
					if origin == "local":
						normalized_filters.append((mutagen_field, filter_value))
					elif origin == "google":
						normalized_filters.append((google_field, filter_value))

	return normalized_filters


def filter_google_songs(songs, include_filters=None, exclude_filters=None, all_includes=False, all_excludes=False):
	"""Match a Google Music song dict against a set of metadata filters.

	Returns a list of Google Music song dicts matching criteria and
	a list of Google Music song dicts filtered out using filter criteria.

	:param songs: A list of Google Music song dicts.

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

	matched_songs = []
	filtered_songs = []

	include_filters_norm = _normalize_filters(include_filters, origin="google")
	exclude_filters_norm = _normalize_filters(exclude_filters, origin="google")

	if include_filters_norm or exclude_filters_norm:
		for song in songs:
			if _check_filters(song, include_filters_norm, exclude_filters_norm, all_includes, all_excludes):
				matched_songs.append(song)
			else:
				filtered_songs.append(song)
	else:
		matched_songs += songs

	return matched_songs, filtered_songs


def filter_local_songs(filepaths, include_filters=None, exclude_filters=None, all_includes=False, all_excludes=False):
	"""Match a local file against a set of metadata filters.

	Returns a list of local song filepaths matching criteria and
	a list of local song filepaths filtered out using filter criteria.
	Invalid music files are also filtered out.

	:param filepaths: A list of filepaths.

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
	"""

	matched_songs = []
	filtered_songs = []

	include_filters_norm = _normalize_filters(include_filters, origin="local")
	exclude_filters_norm = _normalize_filters(exclude_filters, origin="local")

	for filepath in filepaths:
		try:
			song = _mutagen_fields_to_single_value(_get_mutagen_metadata(filepath))
		except mutagen.MutagenError:
			logger.warning("{} is not a valid music file!".format(filepath))
			filtered_songs.append(filepath)
		else:
			if include_filters_norm or exclude_filters_norm:
				if _check_filters(song, include_filters_norm, exclude_filters_norm, all_includes, all_excludes):
					matched_songs.append(filepath)
				else:
					filtered_songs.append(filepath)
			else:
				matched_songs.append(filepath)

	return matched_songs, filtered_songs


def template_to_filepath(template, metadata, template_patterns=None):
	"""Create directory structure and file name based on metadata template.

	Returns a filepath.

	:param template: A filepath which can include template patterns as defined by :param template_patterns:.

	:param metadata: A mutagen metadata dict.

	:param template_patterns: A dict of pattern:field pairs used to replace patterns with metadata field values.
	  Default: :const TEMPLATE_PATTERNS:
	"""

	if not template_patterns:
		template_patterns = TEMPLATE_PATTERNS

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
		for key in template_patterns:
			if key in part and template_patterns[key] in metadata:
				# Force track number to be zero-padded to 2 digits.
				# This is a potentially temporary solution to allowing arbitrary template patterns while allowing zero-padded track numbers.
				if any(template_patterns[key] == tracknumber_field for tracknumber_field in ['tracknumber', 'track_number']):
					track_number = _split_field_to_single_value(metadata[template_patterns[key]])
					metadata[template_patterns[key]] = track_number.zfill(2)

				parts[i] = parts[i].replace(key, metadata[template_patterns[key]])

		for char in CHARACTER_REPLACEMENTS:
			if char in parts[i]:
				parts[i] = parts[i].replace(char, CHARACTER_REPLACEMENTS[char])

	if drive:
		filepath = os.path.join(drive, os.sep, *parts)
	else:
		if os.path.isabs(template):
			filepath = os.path.join(os.sep, *parts)
		else:
			filepath = os.path.join(*parts)

	return filepath


def walk_depth(path, max_depth=float('inf')):
	"""Walk a directory tree with configurable depth.

	:param path: A directory path to walk.

	:param max_depth: The depth in the directory tree to walk.
	  A depth of '0' limits the walk to the top directory.
	  Default: Infinite depth.
	"""

	start_level = os.path.abspath(path).count(os.path.sep)

	for dir_entry in os.walk(path):
		root, dirs, _ = dir_entry
		level = root.count(os.path.sep) - start_level

		yield dir_entry

		if level >= max_depth:
			dirs[:] = []
