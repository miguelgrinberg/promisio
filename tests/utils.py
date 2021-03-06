import asyncio
import os
from functools import wraps


def async_test(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(f(*args, **kwargs))

    return wrapper


def get_fake_error(suffix=''):
    return RuntimeError(os.environ.get('PYTEST_CURRENT_TEST', '') + suffix)
