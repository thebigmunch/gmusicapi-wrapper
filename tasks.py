# coding=utf-8

"""Useful task commands for development and maintenance."""

from invoke import run, task


@task
def build(clean):
	"""Build sdist and bdist_wheel distributions."""

	run('python setup.py sdist bdist_wheel')


@task(build)
def deploy():
	"""Build and upload gmusicapi_wrapper distributions."""

	upload()


@task
def upload():
	"""Upload gmusicapi_wrapper distributions using twine."""

	run('twine upload dist/*')


@task
def clean():
	"""Clean the project directory of unwanted files and directories."""

	run('rm -rf gmusicapi_wrapper.egg-info')
	run('rm -rf .coverage')
	run('rm -rf .tox')
	run('rm -rf .cache')
	run('rm -rf build/')
	run('rm -rf dist/')
	run('find . -name *.pyc -delete')
	run('find . -name *.pyo -delete')
	run('find . -name __pycache__ -delete -depth')
	run('find . -name *~ -delete')


@task
def cover(verbose=False):
	"""Shorter alias for coverage task."""

	coverage(verbose)


@task
def coverage(verbose=False):
	"""Run the gmusicapi_wrapper tests using pytest-cov for coverage."""

	cov_cmd = 'py.test --cov ./gmusicapi_wrapper --cov ./tests ./gmusicapi_wrapper ./tests'

	if verbose:
		cov_cmd += ' -v'

	run(cov_cmd)


@task
def test():
	"""Run the gmusicapi_wrapper tests using pytest."""

	run('py.test')


@task
def tox():
	"""Run the gmusicapi_wrapper tests using tox."""

	run('tox')
