import asyncio
import os
from functools import wraps


def async_test(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        loop.run_until_complete(f(*args, **kwargs))

    return wrapper


def get_fake_error(suffix=''):
    return RuntimeError(os.environ.get('PYTEST_CURRENT_TEST', '') + suffix)
