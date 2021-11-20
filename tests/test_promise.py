import asyncio
import unittest
import pytest
import promisio
from promisio import Promise, promisify
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

    @async_test
    async def test_all(self):
        async def f():
            await asyncio.sleep(0.01)
            return 'f'

        async def g():
            await asyncio.sleep(0.05)
            return 'g'

        async def h():
            await asyncio.sleep(0)
            return 'h'

        p1 = promisify(f)()
        p2 = promisify(g)()
        p3 = promisify(h)()
        result = await Promise.all([p1, p2, p3])
        assert result == ['f', 'g', 'h']

    @async_test
    async def test_empty_all(self):
        result = await Promise.all([])
        assert result == []

    @async_test
    async def test_all_settled(self):
        error = get_fake_error()

        async def f():
            await asyncio.sleep(0.01)
            return 'f'

        async def g():
            raise error

        async def h():
            await asyncio.sleep(0)
            return 'h'

        p1 = promisify(f)()
        p2 = promisify(g)()
        p3 = promisify(h)()
        result = await Promise.all_settled([p1, p2, p3])
        assert result == [
            {'status': 'fulfilled', 'value': 'f'},
            {'status': 'rejected', 'reason': error},
            {'status': 'fulfilled', 'value': 'h'},
        ]

    @async_test
    async def test_any(self):
        error = get_fake_error()

        async def f():
            await asyncio.sleep(0.01)
            return 'f'

        async def g():
            raise error

        async def h():
            await asyncio.sleep(0)
            return 'h'

        p1 = promisify(f)()
        p2 = promisify(g)()
        p3 = promisify(h)()
        result = await Promise.any([p1, p2, p3])
        assert result == 'h'

    @async_test
    async def test_any_rejected(self):
        error1 = get_fake_error(':1')
        error2 = get_fake_error(':2')
        error3 = get_fake_error(':3')

        async def f():
            await asyncio.sleep(0.01)
            raise error1

        async def g():
            await asyncio.sleep(0.05)
            raise error2

        async def h():
            await asyncio.sleep(0)
            raise error3

        p1 = promisify(f)()
        p2 = promisify(g)()
        p3 = promisify(h)()
        try:
            await Promise.any([p1, p2, p3])
        except promisio.AggregateError as error:
            assert error.errors == [error1, error2, error3]
        else:
            assert False

    @async_test
    async def test_empty_any(self):
        with pytest.raises(promisio.AggregateError):
            await Promise.any([])

    @async_test
    async def test_race_resolved(self):
        async def f():
            await asyncio.sleep(0.01)
            raise get_fake_error()

        async def g():
            await asyncio.sleep(0.05)
            return 'g'

        async def h():
            await asyncio.sleep(0)
            return 'h'

        p1 = promisify(f)()
        p2 = promisify(g)()
        p3 = promisify(h)()
        result = await Promise.race([p1, p2, p3])
        assert result == 'h'

    @async_test
    async def test_racei_rejected(self):
        error = get_fake_error()

        async def f():
            await asyncio.sleep(0.01)
            return 'f'

        async def g():
            await asyncio.sleep(0.05)
            return 'g'

        async def h():
            await asyncio.sleep(0)
            raise error

        p1 = promisify(f)()
        p2 = promisify(g)()
        p3 = promisify(h)()
        with pytest.raises(RuntimeError):
            await Promise.race([p1, p2, p3])

    @async_test
    async def test_promisify(self):
        error1 = get_fake_error(':1')
        error2 = get_fake_error(':2')

        def f():
            return 'f'

        async def g():
            return 'g'

        def h():
            raise error1

        async def i():
            raise error2

        p1 = promisify(f)()
        p2 = promisify(g)()
        p3 = promisify(h)()
        p4 = promisify(i)()
        result = await Promise.all_settled([p1, p2, p3, p4])
        assert result == [
            {'status': 'fulfilled', 'value': 'f'},
            {'status': 'fulfilled', 'value': 'g'},
            {'status': 'rejected', 'reason': error1},
            {'status': 'rejected', 'reason': error2},
        ]

    @async_test
    async def test_cancel(self):
        @promisify
        async def long():
            await asyncio.sleep(10)

        p = long()
        await asyncio.sleep(0.01)
        assert not p.cancelled()
        p.cancel()
        with pytest.raises(asyncio.CancelledError):
            await p
        assert p.cancelled()

    @async_test
    async def test_cannot_cancel(self):
        p = Promise.resolve(42)
        assert not p.cancelled()
        p.cancel()
        await p
        assert not p.cancelled()

    def test_run(self):
        assert promisio.run(lambda x: x * 2, 21) == 42
