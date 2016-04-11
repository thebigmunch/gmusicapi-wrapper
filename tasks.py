# coding=utf-8

"""Useful task commands for development and maintenance."""

import glob
import os
import shutil

from invoke import run, task

to_remove_dirnames = ['**/__pycache__', '.cache', '.tox', 'build', 'dist', 'gmusicapi_wrapper.egg-info']
to_remove_filenames = ['**/*.pyc', '**/*.pyo', '.coverage']


@task
def clean():
	"""Clean the project directory of unwanted files and directories."""

	to_remove_dirs = [
		path for dirname in to_remove_dirnames for path in glob.glob(dirname) if os.path.isdir(path)
	]

	for dirpath in to_remove_dirs:
		shutil.rmtree(dirpath)

	to_remove_files = [
		path for filename in to_remove_filenames for path in glob.glob(filename) if os.path.isfile(path)
	]

	for filepath in to_remove_files:
		os.remove(filepath)


@task(clean)
def build():
	"""Build sdist and bdist_wheel distributions."""

	run('python setup.py sdist bdist_wheel')


@task(build)
def publish():
	"""Build and upload gmusicapi_wrapper distributions."""

	upload()


@task
def upload():
	"""Upload gmusicapi_wrapper distributions using twine."""

	run('twine upload dist/*')


@task
def cov(missing=False):
	"""Shorter alias for coverage task."""

	coverage(missing)


@task
def coverage(missing=False):
	"""Run the gmusicapi_wrapper tests using pytest-cov for coverage."""

	cov_run = 'coverage run --source gmusicapi_wrapper -m py.test'
	cov_report = 'coverage report'

	if missing:
		cov_report += ' -m'

	run(cov_run)
	run(cov_report)


@task
def test(coverage=False, verbose=False):
	"""Run the gmusicapi_wrapper tests using pytest."""

	if coverage:
		test_cmd = 'py.test --cov ./gmusicapi_wrapper --cov ./tests ./gmusicapi_wrapper ./tests'
	else:
		test_cmd = 'py.test'

	if verbose:
		test_cmd += ' -v'

	run(test_cmd)


@task
def tox():
	"""Run the gmusicapi_wrapper tests using tox."""

	run('tox')
