import asyncio
import unittest
import pytest
import promisio
from promisio import Promise, promisify
from .utils import async_test, get_fake_error


class TestAPlus(unittest.TestCase):
    @async_test
    async def test_aplus_2_2_1(self):
        """Test that the arguments to 'then' are optional."""
        def f(x):
            pass

        p = Promise()
        p.then().then(None, None).then(f).then(f, None).then(None, f)

    @async_test
    async def test_aplus_2_2_1_1(self):
        """Test that if on_resolved is not a callable it is ignored."""
        p = Promise()
        p2 = p.then(123).then('foo').then({'foo': 'bar'}).then(['foo', 'bar'])
        p._resolve(42)
        await p2

    @async_test
    async def test_aplus_2_2_1_2(self):
        """Test that if on_rejected is not a callable it is ignored."""
        p = Promise()
        p2 = p.then(None, 123).then(None, 'foo').then(
            None, {'foo': 'bar'}).then(None, ['foo', 'bar'])
        p._reject(get_fake_error())
        with pytest.raises(RuntimeError):
            await p2

    @async_test
    async def test_aplus_2_2_2_1(self):
        """Test that on_resolved is called when the promise resolves."""
        result = None

        def f(x):
            nonlocal result
            result = x

        p = Promise()
        p.then(f)
        p._resolve(42)
        await p
        assert result == 42

    @async_test
    async def test_aplus_2_2_2_3(self):
        """Test that on_resolved is only called once."""
        result = None

        def f(x):
            nonlocal result
            result = x

        p = Promise()
        p.then(f)
        p._resolve(42)
        await p
        with pytest.raises(asyncio.InvalidStateError):
            p._resolve('foo')
        assert result == 42

    @async_test
    async def test_aplus_2_2_3_1(self):
        """Test that on_rejected is called when the promise is rejected."""
        result = None
        error = get_fake_error()

        def f(x):
            nonlocal result
            result = x

        p = Promise()
        p2 = p.then(None, f)
        p._reject(error)
        await p2
        assert result == error

    @async_test
    async def test_aplus_2_2_3_3(self):
        """Test that on_rejected is only called once."""
        result = None
        error = get_fake_error()

        def f(x):
            nonlocal result
            result = x

        p = Promise()
        p2 = p.then(None, f)
        p._reject(error)
        await p2
        with pytest.raises(asyncio.InvalidStateError):
            p._reject(ValueError('new error'))
        assert result == error

    @async_test
    async def test_aplus_2_2_6_1(self):
        """Test that multiple on_resolved are called in order."""
        result = []

        def f(x):
            result.append(x)

        def g(x):
            result.append(x + 1)

        def h(x):
            result.append(x + 2)

        p = Promise()
        p.then(f)
        p.then(g)
        p.then(h)
        p._resolve(42)
        await p
        assert result == [42, 43, 44]

    @async_test
    async def test_aplus_2_2_6_2(self):
        """Test that multiple on_rejected are called in order."""
        result = []

        def f(x):
            result.append('f')

        def g(x):
            result.append('g')

        def h(x):
            result.append('h')

        p = Promise()
        p.then(None, f)
        p.then(None, g)
        p2 = p.then(None, h)
        p._reject(get_fake_error())
        await p2
        assert result == ['f', 'g', 'h']

    @async_test
    async def test_aplus_2_2_7(self):
        """Test that then() returns a new promise."""
        p = Promise()
        assert isinstance(p.then(), Promise)

    @async_test
    async def test_aplus_2_2_7_2_a(self):
        """Test that an exception raised in on_resolved causes the next promise
        in the chain to be rejected with that exception."""
        result = None
        error = get_fake_error()

        def f(x):
            raise error

        def g(x):
            assert False, 'should not be called'

        def h(x):
            nonlocal result
            result = x

        p = Promise()
        p2 = p.then(f).then(g, h)
        p._resolve(42)
        await p2
        assert result == error

    @async_test
    async def test_aplus_2_2_7_2_b(self):
        """Test that an exception raised in on_rejected causes the next promise
        in the chain to be rejected with that exception."""
        result = None
        error = get_fake_error()

        def f(x):
            raise error

        def g(x):
            assert False, 'should not be called'

        def h(x):
            nonlocal result
            result = x

        p = Promise()
        p2 = p.then(None, f).then(g, h)
        p._reject(get_fake_error(':2'))
        await p2
        assert result == error

    @async_test
    async def test_aplus_2_2_7_3(self):
        """Test that when a promise without on_resolved resolves, the next
        promise in the chain resolves to the same result."""
        result = None

        def f(x):
            nonlocal result
            result = x

        p = Promise()
        p2 = p.then()
        p3 = p2.then(f)
        p._resolve(42)
        await p3
        assert result == 42

    @async_test
    async def test_aplus_2_2_7_4(self):
        """Test that when a promise without on_resolved resolves, the next
        promise in the chain resolves to the same result."""
        result = None
        error = get_fake_error()

        def f(x):
            nonlocal result
            result = x

        p = Promise()
        p2 = p.then()
        p3 = p2.catch(f)
        p._reject(error)
        await p3
        assert result == error

    @async_test
    async def test_aplus_2_3_2_a(self):
        """Test that when a promise with an on_resolved that returns a promise
        resolves, the next promise in the chain adopts the state of that
        promise."""
        result = None

        def f(x):
            nonlocal result
            result = x

        p = Promise()
        q = Promise()
        p2 = p.then(lambda x: q)
        p3 = p2.then(f)
        p._resolve(42)
        q._resolve(24)
        await p3
        assert result == 24

    @async_test
    async def test_aplus_2_3_2_b(self):
        """Test that when a promise with an on_resolved that returns a promise
        rejects, the next promise in the chain adopts the state of that
        promise."""
        result = None
        error = get_fake_error()

        def f(x):
            nonlocal result
            result = x

        p = Promise()
        q = Promise()
        p2 = p.then(lambda x: q)
        p3 = p2.catch(f)
        p._resolve(42)
        q._reject(error)
        await p3
        assert result == error

    @async_test
    async def test_aplus_2_3_2_c(self):
        """Test that when a promise with an on_rejected that returns a promise
        rejects, the next promise in the chain adopts the state of that
        promise."""
        result = None
        error = get_fake_error()

        def f(x):
            nonlocal result
            result = x

        p = Promise()
        q = Promise()
        p2 = p.catch(lambda x: q)
        p3 = p2.then(f)
        p._reject(error)
        q._resolve(24)
        await p3
        assert result == 24

    @async_test
    async def test_aplus_2_3_2_d(self):
        """Test that when a promise with an on_rejected that returns a promise
        rejects, the next promise in the chain adopts the state of that
        promise."""
        result = None
        error = get_fake_error()
        error2 = get_fake_error(':2')

        def f(x):
            nonlocal result
            result = x

        p = Promise()
        q = Promise()
        p2 = p.catch(lambda x: q)
        p3 = p2.catch(f)
        p._reject(error)
        q._reject(error2)
        await p3
        assert result == error2

    @async_test
    async def test_aplus_2_3_4_a(self):
        """Test that when a promise with an on_resolved that returns a value
        resolves, the next promise in the chain resolves with the same
        value."""
        result = None

        def f(x):
            nonlocal result
            result = x

        p = Promise()
        p2 = p.then(lambda x: 24)
        p2.then(f)
        p._resolve(42)
        await p2
        assert result == 24

    @async_test
    async def test_aplus_2_3_4_b(self):
        """Test that when a promise with an on_resolved that returns a value
        resolves, the next promise in the chain resolves with the same
        value."""
        result = None

        def f(x):
            nonlocal result
            result = x

        p = Promise()
        p2 = p.then(lambda x: 24)
        p2.then(f)
        p._resolve(42)
        await p2
        assert result == 24
