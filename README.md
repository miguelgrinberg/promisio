# promisio

[![tests](https://code.miguelgrinberg.com/miguelgrinberg/promisio/badges/workflows/tests.yml/badge.svg)](https://code.miguelgrinberg.com/miguelgrinberg/promisio/actions)

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

- [git](https://code.miguelgrinberg.com/miguelgrinberg/promisio)
- [Change Log](https://code.miguelgrinberg.com/miguelgrinberg/promisio/src/branch/main/CHANGES.md)
- [Documentation](https://promisio.readthedocs.io/)
- [PyPI](https://pypi.python.org/pypi/promisio)
- [Contributor's guide](CONTRIBUTING.md)
- [Security policy](SECURITY.md)

Sponsor this project
--------------------

This project relies on contributions from its users. If you benefit from it please consider making a single or ongoing monetary contribution in one of the following platforms:

- [Github Sponsors](https://github.com/sponsors/miguelgrinberg)
- [Patreon](https://patreon.com/miguelgrinberg)
- [Buy me a Coffee](https://buymeacoffee.com/miguelgrinberg)
- [thanks.dev](https://thanks.dev/u/gh/miguelgrinberg)
- [PayPal](https://paypal.me/miguelgrinberg)

Thank you!
