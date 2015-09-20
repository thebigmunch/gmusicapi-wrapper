#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import re
import sys

from setuptools import find_packages, setup

if not ((2, 7, 0) <= sys.version_info[:3] < (2, 8)):
	sys.exit("gmusicapi-wrapper only supports Python 2.7.")

# From http://stackoverflow.com/a/7071358/1231454
version_file = "gmusicapi_wrapper/__init__.py"
version_re = r"^__version__ = ['\"]([^'\"]*)['\"]"

version_file_contents = open(version_file).read()
match = re.search(version_re, version_file_contents, re.M)

if match:
	version = match.group(1)
else:
	raise RuntimeError("Could not find version in '%s'" % version_file)

setup(
	name='gmusicapi-wrapper',
	version=version,
	description='A wrapper interface around gmusicapi.',
	url='https://github.com/thebigmunch/gmusicapi-wrapper',
	license='MIT',
	author='thebigmunch',
	author_email='mail@thebigmunch.me',

	keywords=[],
	classifiers=[
		'License :: OSI Approved :: MIT License',
		'Programming Language :: Python :: 2',
		'Programming Language :: Python :: 2.6',
		'Programming Language :: Python :: 2.7',
	],

	install_requires=[
		'gmusicapi >= 7.0.0',  # New Music Manager upload endpoint.
		'mutagen'
	],

	packages=find_packages(),

	zip_safe=False
)
