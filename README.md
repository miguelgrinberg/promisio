# promisio

[![Build status](https://github.com/miguelgrinberg/promisio/workflows/build/badge.svg)](https://github.com/miguelgrinberg/promisio/actions) [![codecov](https://codecov.io/gh/miguelgrinberg/promisio/branch/main/graph/badge.svg)](https://codecov.io/gh/miguelgrinberg/promisio)

JavaScript-style async programming for Python.

## Examples

Create a promise-based async function using the `promisify` decorator. It works
on both sync and async functions!

```python
from promisio import promisify

@promisify
async def f():
    await asyncio.sleep(1)
    return 42

@promisify
def g(x):
    return x * 2

async def main():
    print(await f())  # prints 42
    print(await g(42))  # prints 84

    promise = f()  # runs function in the background without waiting
    # ... do other stuff here in parallel with f running
    await promise  # finally wait for f to complete
```

The return value of the decorated function is a JavaScript-style promise object
that can be awaited. The `then()`, `catch()` and `finally_()` methods to chain
promises work as in JavaScript. The `Promise.all()`, `Promise.all_settled()`,
`Promise.any()`, `Promise.race()`, `Promise.resolve()` and `Promise.reject()`
are also available. Promises in this package are extended to also support
cancellation via the `cancel()` and `cancelled()` methods.

## Resources

- [Documentation](http://promisio.readthedocs.io/en/latest/)
- [PyPI](https://pypi.python.org/pypi/promisio)
- [Change Log](https://github.com/miguelgrinberg/promisio/blob/main/CHANGES.md)

