import asyncio
from functools import partial, wraps
import inspect

if not hasattr(asyncio, 'create_task'):  # pragma: no cover
    asyncio.create_task = asyncio.ensure_future


class AggregateError(RuntimeError):
    def __init__(self, errors):
        self.errors = errors


class Promise:
    def __init__(self, f=None):
        self.future = asyncio.Future()
        if f:
            f(self._resolve, self._reject)

    def then(self, on_resolved=None, on_rejected=None):
        promise = Promise()
        self.future.add_done_callback(
            partial(self._handle_done, on_resolved, on_rejected, promise))
        return promise

    def catch(self, handler):
        return self.then(None, handler)

    def finally_(self, handler):
        def _finally(result):
            return handler()

        return self.then(_finally, _finally)

    def cancel(self):
        # not supported when there is no associated task
        pass

    def cancelled(self):
        return False

    @staticmethod
    def resolve(result):
        promise = Promise()
        if isinstance(result, Promise):
            result.then(lambda res: promise._resolve(res),
                        lambda err: promise._reject(err))
        else:
            promise._resolve(result)
        return promise

    @staticmethod
    def reject(error):
        promise = Promise()
        promise._reject(error)
        return promise

    @staticmethod
    def all(promises):
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
        return Promise.all([promise.then(
            lambda value: {'status': 'fulfilled', 'value': value}).catch(
                lambda reason: {'status': 'rejected', 'reason': reason})
            for promise in promises])

    @staticmethod
    def any(promises):
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


class CancellablePromise(Promise):
    def __init__(self, task):
        super().__init__()
        self.task = task

    def cancel(self):
        self.task.cancel()

    def cancelled(self):
        return self.task.cancelled()


def promisify(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
        except BaseException as error:
            return Promise.reject(error)
        if inspect.iscoroutine(result):
            task = asyncio.create_task(result)
            promise = CancellablePromise(task)
            task.add_done_callback(
                partial(Promise._handle_done, None, None, promise))
            return promise
        else:
            return Promise.resolve(result)

    return wrapper


def run(func, *args, **kwargs):
    async def _run():
        return await Promise.resolve(func(*args, **kwargs))

    return asyncio.get_event_loop().run_until_complete(_run())
