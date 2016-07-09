# coding=utf-8

"""Utility functions for gmusicapi_wrapper.

	>>> import gmusicapi_wrapper.utils as gmw_utils
	>>> from gmusicapi_wrapper.utils import ...
"""

import logging
import os
import re
import subprocess

import mutagen

from .constants import CHARACTER_REPLACEMENTS, CYGPATH_RE, TEMPLATE_PATTERNS
from .decorators import cast_to_list

logger = logging.getLogger(__name__)


def convert_cygwin_path(path):
	"""Convert Unix path from Cygwin to Windows path."""

	try:
		win_path = subprocess.check_output(["cygpath", "-aw", path], universal_newlines=True).strip()
	except (FileNotFoundError, subprocess.CalledProcessError):
		logger.exception("Call to cygpath failed.")
		raise

	return win_path


def _get_mutagen_metadata(filepath):
	"""Get mutagen metadata dict from a file."""

	try:
		metadata = mutagen.File(filepath, easy=True)
	except mutagen.MutagenError:
		logger.warning("Can't load {} as music file.".format(filepath))
		raise

	return metadata


def _mutagen_fields_to_single_value(metadata):
	"""Replace mutagen metadata field list values in mutagen tags with the first list value."""

	return dict((k, v[0]) for k, v in metadata.items() if v)


def _split_field_to_single_value(field):
	"""Convert number field values split by a '/' to a single number value."""

	split_field = re.match(r'(\d+)/\d+', field)

	return split_field.group(1) or field


def _filter_comparison_fields(song):
	"""Filter missing artist, album, title, or track fields to improve match accuracy."""

	# Need both tracknumber (mutagen) and track_number (Google Music) here.
	return [field for field in ['artist', 'album', 'title', 'tracknumber', 'track_number'] if field in song and song[field]]


def _normalize_metadata(metadata):
	"""Normalize metadata to improve match accuracy."""

	metadata = str(metadata)
	metadata = metadata.lower()

	metadata = re.sub(r'\/\s*\d+', '', metadata)  # Remove "/<totaltracks>" from track number.
	metadata = re.sub(r'^0+([0-9]+)', r'\1', metadata)  # Remove leading zero(s) from track number.
	metadata = re.sub(r'^\d+\.+', '', metadata)  # Remove dots from track number.
	metadata = re.sub(r'[^\w\s]', '', metadata)  # Remove any non-words.
	metadata = re.sub(r'\s+', ' ', metadata)  # Reduce multiple spaces to a single space.
	metadata = re.sub(r'^\s+', '', metadata)  # Remove leading space.
	metadata = re.sub(r'\s+$', '', metadata)  # Remove trailing space.
	metadata = re.sub(r'^the\s+', '', metadata, re.I)  # Remove leading "the".

	return metadata


def _normalize_song(song):
	"""Convert filepath to song dict while leaving song dicts untouched."""

	return song if isinstance(song, dict) else _mutagen_fields_to_single_value(_get_mutagen_metadata(song))


def compare_song_collections(src_songs, dst_songs):
	"""Compare two song collections to find missing songs.

	Parameters:
		src_songs (list): Google Music song dicts or filepaths of local songs.

		dest_songs (list): Google Music song dicts or filepaths of local songs.

	Returns:
		A list of Google Music song dicts or local song filepaths from source missing in destination.
	"""

	def gather_field_values(song):
		return tuple((_normalize_metadata(song[field]) for field in _filter_comparison_fields(song)))

	dst_songs_criteria = {gather_field_values(_normalize_song(dst_song)) for dst_song in dst_songs}

	return [src_song for src_song in src_songs if gather_field_values(_normalize_song(src_song)) not in dst_songs_criteria]


@cast_to_list(0)
def get_supported_filepaths(filepaths, supported_extensions, max_depth=float('inf')):
	"""Get filepaths with supported extensions from given filepaths.

	Parameters:
		filepaths (list or str): Filepath(s) to check.

		supported_extensions (tuple or str): Supported file extensions or a single file extension.

		max_depth (int): The depth in the directory tree to walk.
			A depth of '0' limits the walk to the top directory.
			Default: No limit.

	Returns:
		A list of supported filepaths.
	"""

	supported_filepaths = []

	for path in filepaths:
		if os.name == 'nt' and CYGPATH_RE.match(path):
			path = convert_cygwin_path(path)

		if os.path.isdir(path):
			for root, __, files in walk_depth(path, max_depth):
				for f in files:
					if f.lower().endswith(supported_extensions):
						supported_filepaths.append(os.path.join(root, f))
		elif os.path.isfile(path) and path.lower().endswith(supported_extensions):
			supported_filepaths.append(path)

	return supported_filepaths


@cast_to_list(0)
def exclude_filepaths(filepaths, exclude_patterns=None):
	"""Exclude file paths based on regex patterns.

	Parameters:
		filepaths (list or str): Filepath(s) to check.

		exclude_patterns (list): Python regex patterns to check filepaths against.

	Returns:
		A list of filepaths to include and a list of filepaths to exclude.
	"""

	if exclude_patterns is not None:
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


def _check_field_value(field_value, pattern):
	"""Check a song metadata field value for a pattern."""

	if isinstance(field_value, list):
		return any(re.search(pattern, str(value), re.I) for value in field_value)
	else:
		return re.search(pattern, str(field_value), re.I)


def _check_filters(song, include_filters=None, exclude_filters=None, all_includes=False, all_excludes=False):
	"""Check a song metadata dict against a set of metadata filters."""

	include = True

	if include_filters:
		if all_includes:
			if not all(field in song and _check_field_value(song[field], pattern) for field, pattern in include_filters):
				include = False
		else:
			if not any(field in song and _check_field_value(song[field], pattern) for field, pattern in include_filters):
				include = False

	if exclude_filters:
		if all_excludes:
			if all(field in song and _check_field_value(song[field], pattern) for field, pattern in exclude_filters):
				include = False
		else:
			if any(field in song and _check_field_value(song[field], pattern) for field, pattern in exclude_filters):
				include = False

	return include


def filter_google_songs(songs, include_filters=None, exclude_filters=None, all_includes=False, all_excludes=False):
	"""Match a Google Music song dict against a set of metadata filters.

	Parameters:
		songs (list): Google Music song dicts to filter.

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
		A list of Google Music song dicts matching criteria and
		a list of Google Music song dicts filtered out using filter criteria.
		::

			(matched, filtered)
	"""

	matched_songs = []
	filtered_songs = []

	if include_filters or exclude_filters:
		for song in songs:
			if _check_filters(
					song, include_filters=include_filters, exclude_filters=exclude_filters,
					all_includes=all_includes, all_excludes=all_excludes):
				matched_songs.append(song)
			else:
				filtered_songs.append(song)
	else:
		matched_songs += songs

	return matched_songs, filtered_songs


def filter_local_songs(filepaths, include_filters=None, exclude_filters=None, all_includes=False, all_excludes=False):
	"""Match a local file against a set of metadata filters.

	Parameters:
		filepaths (list): Filepaths to filter.

		include_filters (list): A list of ``(field, pattern)`` tuples.
			Fields are any valid mutagen metadata fields.
			Patterns are Python regex patterns.
			Local songs are filtered out if the given metadata field values don't match any of the given patterns.

		exclude_filters (list): A list of ``(field, pattern)`` tuples.
			Fields are any valid mutagen metadata fields.
			Patterns are Python regex patterns.
			Local songs are filtered out if the given metadata field values match any of the given patterns.

		all_includes (bool): If ``True``, all include_filters criteria must match to include a song.

		all_excludes (bool): If ``True``, all exclude_filters criteria must match to exclude a song.

	Returns:
		A list of local song filepaths matching criteria and
		a list of local song filepaths filtered out using filter criteria.
		Invalid music files are also filtered out.
		::

			(matched, filtered)
	"""

	matched_songs = []
	filtered_songs = []

	for filepath in filepaths:
		try:
			song = _get_mutagen_metadata(filepath)
		except mutagen.MutagenError:
			filtered_songs.append(filepath)
		else:
			if include_filters or exclude_filters:
				if _check_filters(
						song, include_filters=include_filters, exclude_filters=exclude_filters,
						all_includes=all_includes, all_excludes=all_excludes):
					matched_songs.append(filepath)
				else:
					filtered_songs.append(filepath)
			else:
				matched_songs.append(filepath)

	return matched_songs, filtered_songs


def get_suggested_filename(metadata):
	"""Generate a filename for a song based on metadata.

	Parameters:
		metadata (dict): A metadata dict.

	Returns:
		A filename.
	"""

	if metadata.get('title') and metadata.get('track_number'):
		suggested_filename = '{track_number:0>2} {title}'.format(**metadata)
	elif metadata.get('title') and metadata.get('trackNumber'):
		suggested_filename = '{trackNumber:0>2} {title}'.format(**metadata)
	elif metadata.get('title') and metadata.get('tracknumber'):
		suggested_filename = '{tracknumber:0>2} {title}'.format(**metadata)
	else:
		suggested_filename = '00 {}'.format(metadata.get('title', ''))

	return suggested_filename


def _replace_template_patterns(template, metadata, template_patterns):
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


def template_to_filepath(template, metadata, template_patterns=None):
	"""Create directory structure and file name based on metadata template.

	Parameters:
		template (str): A filepath which can include template patterns as defined by :param template_patterns:.

		metadata (dict): A metadata dict.

		template_patterns (dict): A dict of ``pattern: field`` pairs used to replace patterns with metadata field values.
			Default: :const TEMPLATE_PATTERNS:

	Returns:
		A filepath.
	"""

	if template_patterns is None:
		template_patterns = TEMPLATE_PATTERNS

	metadata = metadata if isinstance(metadata, dict) else _mutagen_fields_to_single_value(metadata)
	assert isinstance(metadata, dict)

	suggested_filename = get_suggested_filename(metadata).replace('.mp3', '')

	if template == os.getcwd() or template == '%suggested%':
		filepath = suggested_filename
	else:
		t = template.replace('%suggested%', suggested_filename)
		filepath = _replace_template_patterns(t, metadata, template_patterns)

	return filepath


def walk_depth(path, max_depth=float('inf')):
	"""Walk a directory tree with configurable depth.

	Parameters:
		path (str): A directory path to walk.

		max_depth (int): The depth in the directory tree to walk.
			A depth of '0' limits the walk to the top directory.
			Default: No limit.
	"""

	start_level = os.path.abspath(path).count(os.path.sep)

	for dir_entry in os.walk(path):
		root, dirs, _ = dir_entry
		level = root.count(os.path.sep) - start_level

		yield dir_entry

		if level >= max_depth:
			dirs[:] = []
