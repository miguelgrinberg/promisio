Quick Start
-----------

This package implements JavaScript-style promises. The
`JavaScript Promise documentation <https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Promise>`_
is a good introductory reference.

To create a promise-based async function use the :func:`promisio.promisify`
decorator. This decorator works on both sync and async functions. Regardless of
the type of source function, the resulting function is always asynchronous.

Example::

    import asyncio
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

    asyncio.run(main())

The return value of a function that is decorated with ``promisify`` is a
JavaScript-style promise object. Promises are awaitable, so the syntax to call
and wait for a promise-based function is identical to that of a coroutine-based
function.

The main difference is that promise-based functions can be called like regular
functions and do not have to be awaited for them to start. When a promise-based
function is called without awaiting, the function starts running while the
calling function continues to execute.

Promise objects offer the :func:`promisio.Promise.then`,
:func:`promisio.Promise.catch` and :func:`promisio.Promise.finally_` methods to
chain promises as in JavaScript. These can be used in sync or async functions
to work asychronously through promise callbacks. Once again, these methods work
as their JavaScript counterparts.

The :func:`promisio.Promise.all`, :func:`promisio.Promise.all_settled`,
:func:`promisio.Promise.any`, :func:`promisio.Promise.race`,
:func:`promisio.Promise.resolve` and :func:`promisio.Promise.reject`
functions are also available.

While promise cancellation is not possible with JavaScript promises, this 
package is extended to support cancellation via the
:func:`promisio.Promise.cancel` and :func:`promisio.Promise.cancelled` methods.
A cancelled promise gets rejected with a ``asyncio.CancelledError`` exception.
