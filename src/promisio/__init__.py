import asyncio
from functools import partial, wraps
import inspect

if not hasattr(asyncio, 'create_task'):  # pragma: no cover
    asyncio.create_task = asyncio.ensure_future


class AggregateError(RuntimeError):
    """An exception that holds a list of errors.

    This exception is raised by :func:`Promise.any` when all of the input
    promises are rejected.

    :param errors: the list of erros.
    """
    def __init__(self, errors):
        self.errors = errors


class Promise:
    """A promise class.

    :param f: the promise function. If this argument is omitted, the promise is
              created without an associated function. The provided function
              must accept two arguments, ``resolve`` and ``reject`` that settle
              the promise by fullfilling it or rejecting it respectively.

    Note: Creating a promise object directly is often unnecessary. The
    :func:`promisify` decorator is a much more convenient option.
    """
    def __init__(self, f=None):
        self.future = asyncio.Future()
        if f:
            f(self._resolve, self._reject)

    def then(self, on_resolved=None, on_rejected=None):
        """Appends fulfillment and rejection handlers to the promise.

        :param on_resolved: an optional fulfillment handler.
        :param on_rejected: an optional rejection handler.

        Returns a new promise that resolves to the return value of the called
        handler, or to the original settled value if a handler was not
        provided.
        """
        promise = Promise()
        self.future.add_done_callback(
            partial(self._handle_done, on_resolved, on_rejected, promise))
        return promise

    def catch(self, on_rejected):
        """Appends a rejection handler callback to the promise.

        :param on_rejected: the rejection handler.

        Returns a new promise that resolves to the return value of the
        handler.
        """
        return self.then(None, on_rejected)

    def finally_(self, on_settled):
        """Appends a fulfillment and reject handler to the promise.

        :param on_settled: the handler.

        The handler is invoked when the promise is fulfilled or rejected.
        Returns a new promise that resolves when the original promise settles.
        """
        def _finally(result):
            return on_settled()

        return self.then(_finally, _finally)

    def cancel(self):
        """Cancels a promise, if possible.

        A promise that is cancelled rejects with a ``asyncio.CancelledError``.
        """
        return self.future.cancel()

    def cancelled(self):
        """Checks if a promise has been cancelled."""
        return self.future.cancelled()

    @staticmethod
    def resolve(value):
        """Returns a new Promise object that resolves to the given value.

        :param value: the value the promise will resolve to.

        If the value is another ``Promise`` instance, the new promise will
        resolve or reject when this promise does. If the value is an asyncio
        ``Task`` object, the new promise will be associated with the task and
        will pass cancellation requests to it if its :func:`Promise.cancel`
        method is invoked. Any other value creates a promise that immediately
        resolves to the value.
        """
        promise = None
        if isinstance(value, Promise):
            promise = Promise()
            value.then(lambda res: promise._resolve(res),
                       lambda err: promise._reject(err))
        elif isinstance(value, asyncio.Task):
            promise = TaskPromise(value)
            value.add_done_callback(
                partial(Promise._handle_done, None, None, promise))
        else:
            promise = Promise()
            promise._resolve(value)
        return promise

    @staticmethod
    def reject(reason):
        """Returns a new promise object that is rejected with the given reason.

        :param reason: the rejection reason. Must be an ``Exception`` instance.
        """
        promise = Promise()
        promise._reject(reason)
        return promise

    @staticmethod
    def all(promises):
        """Wait for all promises to be resolved, or for any to be rejected.

        :param promises: a list of promises to wait for.

        Returns a promise that resolves to a aggregating list of all the values
        from the resolved input promises, in the same order as given. If one or
        more of the input promises are rejected, the returned promise is
        rejected with the reason of the first rejected promise.
        """
        new_promise = Promise()
        results = []
        total = len(promises)
        resolved = 0

        def _resolve(index, result):
            nonlocal results, resolved

            if len(results) < index + 1:
                results += [None] * (index + 1 - len(results))
            results[index] = result
            resolved += 1
            if resolved == total:
                new_promise._resolve(results)

        index = 0
        for promise in promises:
            Promise.resolve(promise).then(partial(_resolve, index),
                                          new_promise._reject)
            index += 1

        if total == resolved:
            new_promise._resolve(results)
        return new_promise

    @staticmethod
    def all_settled(promises):
        """Wait until all promises are resolved or rejected.

        :param promises: a list of promises to wait for.

        Returns a promise that resolves to a list of dicts, where each dict
        describes the outcome of each promise. For a promise that was
        fulfilled, the dict has this format::

            {'status': 'fulfilled', 'value': <resolved-value>}

        For a promise that was rejected, the dict has this format::

            {'status': 'rejected', 'reason': <rejected-reason>}
        """
        return Promise.all([promise.then(
            lambda value: {'status': 'fulfilled', 'value': value}).catch(
                lambda reason: {'status': 'rejected', 'reason': reason})
            for promise in promises])

    @staticmethod
    def any(promises):
        """Wait until any of the promises given resolves.

        :oaram promises: a list of promises to wait for.

        Returns a promise that resolves with the value of the first input
        promise. Promise rejections are ignored, except when all the input
        promises are rejected, in which case the returned promise rejects with
        an :class:`AggregateError`.
        """
        new_promise = Promise()
        errors = []
        total = len(promises)
        rejected = 0

        def _reject(index, error):
            nonlocal errors, rejected

            if len(errors) < index + 1:
                errors += [None] * (index + 1 - len(errors))
            errors[index] = error
            rejected += 1
            if rejected == total:
                new_promise._reject(AggregateError(errors))

        index = 0
        for promise in promises:
            Promise.resolve(promise).then(new_promise._resolve,
                                          partial(_reject, index))
            index += 1

        if total == rejected:
            new_promise._reject(AggregateError(errors))
        return new_promise

    @staticmethod
    def race(promises):
        """Wait until any of the promises is fulfilled or rejected.

        :param promises: a list of promises to wait for.

        Returns a promise that resolves or rejects with the first input
        promise that settles.
        """
        new_promise = Promise()
        settled = False

        def _resolve(result):
            nonlocal settled

            if not settled:
                settled = True
                new_promise._resolve(result)

        def _reject(error):
            nonlocal settled

            if not settled:
                settled = True
                new_promise._reject(error)

        for promise in promises:
            Promise.resolve(promise).then(_resolve, _reject)
        return new_promise

    def _resolve(self, result):
        self.future.set_result(result)

    def _reject(self, error):
        self.future.set_exception(error)

    @staticmethod
    def _handle_callback(result, callback, promise, resolve=True):
        if callable(callback):
            try:
                callback_result = callback(result)
                if isinstance(callback_result, Promise):
                    callback_result.then(lambda res: promise._resolve(res),
                                         lambda err: promise._reject(err))
                else:
                    promise._resolve(callback_result)
            except BaseException as error:
                promise._reject(error)
        elif resolve:
            promise._resolve(result)
        else:
            promise._reject(result)

    @staticmethod
    def _handle_done(on_resolved, on_rejected, promise, future):
        try:
            result = future.result()
            Promise._handle_callback(result, on_resolved, promise)
        except BaseException as error:
            Promise._handle_callback(error, on_rejected, promise,
                                     resolve=False)

    def __await__(self):
        def _reject(error):
            raise error

        return self.catch(_reject).future.__await__()


class TaskPromise(Promise):
    def __init__(self, task):
        super().__init__()
        self.task = task

    def cancel(self):
        # cancel the task associated with this future
        # (the future will receive the cancellation error)
        return self.task.cancel()

    def cancelled(self):
        return self.task.cancelled()


def promisify(func):
    """Create a promise-based async function from regular or async functions.

    Examples::

        @promisify
        def add(arg1, arg2):
            return arg1 + arg2

        @promisify
        async def random_sleep():
            await asyncio.sleep(random.random())

        async def test():
            result = await add(1, 2)
            await random_sleep()
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
        except BaseException as error:
            return Promise.reject(error)
        if inspect.iscoroutine(result):
            result = asyncio.create_task(result)
        return Promise.resolve(result)

    return wrapper


def run(func, *args, **kwargs):
    """Run an async loop until the given promise-based function returns.

    :param func: the promise-based function to run.
    :param args: positional arguments to pass to the function.
    :param kwargs: keyword arguments to pass to the function.
    """
    async def _run():
        return await func(*args, **kwargs)

    return asyncio.get_event_loop().run_until_complete(_run())
