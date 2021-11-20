import asyncio
import unittest
import pytest
from promisio import Promise
from .utils import async_test, get_fake_error


class TestPromise(unittest.TestCase):
    @async_test
    async def test_resolved(self):
        result = None

        def f(resolve, reject):
            resolve(42)

        def g(x):
            nonlocal result
            result = x

        p = Promise(f)
        p.then(g)

        await asyncio.sleep(0)
        while result is None:
            await asyncio.sleep(0.05)
        assert result == 42

    @async_test
    async def test_rejected(self):
        result = None
        error = get_fake_error()

        def f(resolve, reject):
            reject(error)

        def g(x):
            nonlocal result
            result = x

        p = Promise(f)
        p.catch(g)

        await asyncio.sleep(0)
        while result is None:
            await asyncio.sleep(0.05)
        assert result == error

    @async_test
    async def test_await_resolved_promise(self):
        p = Promise.resolve(42)
        result = await p
        assert result == 42

    @async_test
    async def test_await_rejected_promise(self):
        p = Promise.reject(get_fake_error())
        with pytest.raises(RuntimeError):
            await p

    @async_test
    async def test_resolve_to_promise(self):
        def f(resolve, reject):
            resolve(42)

        p = Promise(f)
        q = Promise.resolve(p)
        result = await q
        assert result == 42

    @async_test
    async def test_catch(self):
        result = None
        result2 = None
        error = get_fake_error()

        def f(x):
            nonlocal result
            result = x
            return 42

        def g(x):
            nonlocal result2
            result2 = x

        p = Promise.reject(error)
        await p.then().then().then().catch(f).then(g)
        assert result == error
        assert result2 == 42

    @async_test
    async def test_then_finally(self):
        result = None

        def f():
            nonlocal result
            result = True

        p = Promise.resolve(42)
        await p.finally_(f)
        assert result
