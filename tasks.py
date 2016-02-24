# coding=utf-8

"""Useful task commands for development and maintenance."""

from invoke import run, task


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
