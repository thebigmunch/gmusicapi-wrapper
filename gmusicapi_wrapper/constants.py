# coding=utf-8

import re

# A regex for the Google Music id format.
# Stolen with love from gmusicapi.
GM_ID_RE = re.compile(("{h}{{8}}-" + ("{h}{{4}}-" * 3) + "{h}{{12}}").format(h="[0-9a-f]"))

# Compile regex to match Unix absolute paths from Cygwin.
CYGPATH_RE = re.compile("^(?:/[^/]+)*/?$")

CHARACTER_REPLACEMENTS = {
	'\\': '-', '/': ',', ':': '-', '*': 'x', '<': '[',
	'>': ']', '|': '!', '?': '', '"': "''"
}

TEMPLATE_PATTERNS = {
	'%artist%': 'artist', '%title%': 'title', '%track%': 'tracknumber',
	'%track2%': 'tracknumber', '%album%': 'album', '%date%': 'date',
	'%genre%': 'genre', '%albumartist%': 'performer', '%disc%': 'discnumber'
}

SUPPORTED_SONG_FORMATS = ('.mp3', '.flac', '.ogg', '.m4a')
"""tuple: File extensions of supported media formats for uploading."""

SUPPORTED_PLAYLIST_FORMATS = ('.m3u', '.m3u8')
"""tuple: File extensions of supported playlist formats."""
