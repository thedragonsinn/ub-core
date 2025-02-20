from asyncio import iscoroutine, iscoroutinefunction, to_thread
from functools import wraps
from typing import Callable


class MakeAsync:
    @staticmethod
    def make_async(function: Callable):
        """
        Wraps a non-async function in asyncio.to_thread
        and returns an async function that must be awaited.

        @param function: Callable
        @return: Any
        """

        if iscoroutinefunction(function) or iscoroutine(function):
            raise ValueError(
                f"Non-Async function expected, got async function/coroutine {function}"
            )

        @wraps(function)
        async def wrapper(*args, **kwargs):
            return await to_thread(function, *args, **kwargs)

        return wrapper
