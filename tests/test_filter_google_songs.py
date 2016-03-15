# coding=utf-8

"""Module for testing gmusciapi_wrapper.utils.filter_google_songs utility function."""

from gmusicapi_wrapper.utils import filter_google_songs

from fixtures import TEST_SONGS_1


def test_filter_google_songs_no_filters():
	"""Test gmusicapi_wrapper.utils.filter_google_songs with no filters."""

	matched, filtered = filter_google_songs(TEST_SONGS_1)
	expected_matched = TEST_SONGS_1
	expected_filtered = []

	assert matched == expected_matched
	assert filtered == expected_filtered


class TestIncludeFilters:
	"""Test gmusicapi_wrapper.utils.filter_google_songs with input_filters."""

	def test_filter_google_songs_single_include_filters_any_match(self):
		"""Test gmusicapi_wrapper.utils.filter_google_songs with a single include filter matching with any."""

		matched, filtered = filter_google_songs(TEST_SONGS_1, include_filters=[("title", "Take")], all_includes=False)
		expected_matched = [TEST_SONGS_1[0]]
		expected_filtered = [TEST_SONGS_1[1]]

		assert matched == expected_matched
		assert filtered == expected_filtered

	def test_filter_google_songs_single_include_filters_any_no_match(self):
		"""Test gmusicapi_wrapper.utils.filter_google_songs with a single include filter not matching with any."""

		matched, filtered = filter_google_songs(TEST_SONGS_1, include_filters=[("artist", "Modest")], all_includes=False)
		expected_matched = []
		expected_filtered = TEST_SONGS_1

		assert matched == expected_matched
		assert filtered == expected_filtered

	def test_filter_google_songs_multiple_include_filters_any_match(self):
		"""Test gmusicapi_wrapper.utils.filter_google_songs with multiple include filters matching with any."""

		matched, filtered = filter_google_songs(TEST_SONGS_1, include_filters=[("artist", "Muse"), ("title", "Take")], all_includes=False)
		expected_matched = TEST_SONGS_1
		expected_filtered = []

		assert matched == expected_matched
		assert filtered == expected_filtered

	def test_filter_google_songs_multiple_include_filters_any_no_match(self):
		"""Test gmusicapi_wrapper.utils.filter_google_songs with multiple include filters not matching with any."""

		matched, filtered = filter_google_songs(
			TEST_SONGS_1, include_filters=[("artist", "Modest"), ("title", "Everything")], all_includes=False
		)
		expected_matched = []
		expected_filtered = TEST_SONGS_1

		assert matched == expected_matched
		assert filtered == expected_filtered

	def test_filter_google_songs_multiple_all_includes_filters_match(self):
		"""Test gmusicapi_wrapper.utils.filter_google_songs with multiple include filters matching with all."""

		matched, filtered = filter_google_songs(
			TEST_SONGS_1, include_filters=[("artist", "Muse"), ("title", "Take")], all_includes=True
		)
		expected_matched = [TEST_SONGS_1[0]]
		expected_filtered = [TEST_SONGS_1[1]]

		assert matched == expected_matched
		assert filtered == expected_filtered

	def test_filter_google_songs_multiple_all_includes_filters_no_match(self):
		"""Test gmusicapi_wrapper.utils.filter_google_songs with multiple include filters not matching with all."""

		matched, filtered = filter_google_songs(
			TEST_SONGS_1, include_filters=[("artist", "Modest"), ("title", "Take")], all_includes=True
		)
		expected_matched = []
		expected_filtered = TEST_SONGS_1

		assert matched == expected_matched
		assert filtered == expected_filtered


class TestExcludeFilters:
	"""Test gmusicapi_wrapper.utils.filter_google_songs with exclude_filters."""

	def test_filter_google_songs_single_exclude_filters_any_match(self):
		"""Test gmusicapi_wrapper.utils.filter_google_songs with a single exclude filter matching with any."""

		matched, filtered = filter_google_songs(
			TEST_SONGS_1, exclude_filters=[("title", "Take")]
		)
		expected_matched = [TEST_SONGS_1[1]]
		expected_filtered = [TEST_SONGS_1[0]]

		assert matched == expected_matched
		assert filtered == expected_filtered

	def test_filter_google_songs_single_exclude_filters_any_no_match(self):
		"""Test gmusicapi_wrapper.utils.filter_google_songs with a single exclude filter not matching with any."""

		matched, filtered = filter_google_songs(
			TEST_SONGS_1, exclude_filters=[("artist", "Modest")]
		)
		expected_matched = TEST_SONGS_1
		expected_filtered = []

		assert matched == expected_matched
		assert filtered == expected_filtered

	def test_filter_google_songs_multiple_exclude_filters_any_match(self):
		"""Test gmusicapi_wrapper.utils.filter_google_songs with multiple exclude filters matching with any."""

		matched, filtered = filter_google_songs(
			TEST_SONGS_1, exclude_filters=[("artist", "Muse"), ("title", "Take")]
		)
		expected_matched = []
		expected_filtered = TEST_SONGS_1

		assert matched == expected_matched
		assert filtered == expected_filtered

	def test_filter_google_songs_multiple_exclude_filters_any_no_match(self):
		"""Test gmusicapi_wrapper.utils.filter_google_songs with multiple exclude filters not matching with any."""

		matched, filtered = filter_google_songs(
			TEST_SONGS_1, exclude_filters=[("artist", "Modest"), ("title", "Everything")]
		)
		expected_matched = TEST_SONGS_1
		expected_filtered = []

		assert matched == expected_matched
		assert filtered == expected_filtered

	def test_filter_google_songs_multiple_all_excludes_filters_match(self):
		"""Test gmusicapi_wrapper.utils.filter_google_songs with multiple exclude filters matching with all."""

		matched, filtered = filter_google_songs(
			TEST_SONGS_1, exclude_filters=[("artist", "Muse"), ("title", "Take")], all_excludes=True
		)
		expected_matched = [TEST_SONGS_1[1]]
		expected_filtered = [TEST_SONGS_1[0]]

		assert matched == expected_matched
		assert filtered == expected_filtered

	def test_filter_google_songs_multiple_all_excludes_filters_no_match(self):
		"""Test gmusicapi_wrapper.utils.filter_google_songs with multiple exclude filters not matching with all."""

		matched, filtered = filter_google_songs(
			TEST_SONGS_1, exclude_filters=[("artist", "Modest"), ("title", "Take")], all_excludes=True
		)
		expected_matched = TEST_SONGS_1
		expected_filtered = []

		assert matched == expected_matched
		assert filtered == expected_filtered
