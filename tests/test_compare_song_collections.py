# coding=utf-8

"""Module for testing gmusicapi_wrapper.utils.compare_songs_collections utility function."""

from gmusicapi_wrapper.utils import compare_song_collections

from fixtures import TEST_SONGS_1, TEST_SONGS_2


def test_compare_song_collections_same():
	"""Test gmusicapi_wrapper.utils.compare_song_collections with identical song collections."""

	result = compare_song_collections(TEST_SONGS_1, TEST_SONGS_1)
	expected = []

	assert len(result) == 0
	assert result == expected


def test_compare_song_collections_partial():
	"""Test gmusicapi_wrapper.utils.compare_song_collections with collection 2 containing 1 of 2 songs from collection 1."""

	result = compare_song_collections(TEST_SONGS_1, TEST_SONGS_2)
	expected = [TEST_SONGS_1[1]]

	assert len(result) == 1
	assert result == expected
