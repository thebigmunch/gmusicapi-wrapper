# coding=utf-8

"""Decorators used in gmusicapi_wrapper."""

import logging
from functools import wraps

logger = logging.getLogger(__name__)


# Created to remove the dependency on gmusicapi's accept_singleton decorator.
def cast_to_list(pos):
	def func_decorator(func):
		@wraps(func)
		def wrapper(*args, **kwargs):
			if not isinstance(args[pos], list):
				args = list(args)
				args[pos] = [args[pos]]
				args = tuple(args)

			return func(*args, **kwargs)
		return wrapper
	return func_decorator
