import asyncio
import json
import logging
import threading
from collections.abc import Awaitable, Callable, Coroutine, Generator
from functools import wraps
from inspect import isawaitable, iscoroutine

LOGGER = logging.getLogger("Config")


def ensure_is_not_closed(function):
    @wraps(function)
    def inner(self: "TaskManager", *args, **kwargs):
        if self.is_closed:
            raise RuntimeError("Task Manager is closed.")
        return function(self, *args, **kwargs)

    return inner


class TaskManager:
    __instance = None

    def __new__(cls, *args, **kwargs):
        """
        To ensure everything gets cleaned on exit
        Prevent multiple instances of Task Manager
        """
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
        return cls.__instance

    def __init__(self):
        self._store = {"init": set(), "bg": set(), "exit": set(), "temp": set(), "workers": set()}

        self._closed: bool = False
        self._loop = None
        self.lock = threading.Lock()
        self.async_lock = asyncio.Lock()

    def __str__(self) -> str:
        return json.dumps(self._store, indent=4, ensure_ascii=False, default=str)

    def clear(self):
        [v.clear() for v in self._store.values()]

    @property
    def loop(self):
        if self._loop is None:
            raise RuntimeError("Event loop not found.")
        return self._loop

    @loop.setter
    def loop(self, loop):
        self._loop = loop

    @property
    def is_closed(self):
        return self._closed

    @property
    def all_tasks(self) -> Generator:
        for tasks in list(self._store.values()):
            for task in tasks:
                if isinstance(task, asyncio.Task):
                    yield task

    @property
    def locked(self):
        return self.lock.locked() or self.async_lock.locked()

    @ensure_is_not_closed
    def add_init(self, coro: Coroutine | Awaitable) -> None:
        """
        type:
            must be coroutines/awaitable
        life:
            cleared after call to run_init_tasks
        info:
            to register an init task on module level, name it init_task
            they are automatically loaded via core.client.import_modules
            init_task and @register_task(type=init) are mutually exclusive
            DO NOT NAME FUNCTION init_task and then do @bot.register_task(type=init)
            THIS WILL DUPLICATE IT.
        ex:
            funcs to extract and set data from db / files etc
        """
        with self.lock:
            if not isawaitable(coro):
                raise TypeError(f"INIT requires awaitable got: {coro}")
            self._store["init"].add(coro)
            return None

    @ensure_is_not_closed
    def add_exit(self, fn: Callable) -> None:
        """
        type:
            can be any kind of function
        life:
            till end of run
        info:
            functions to call before bot exits and closes interpreter
        ex:
            closing open fds, connections, objects, dumping runtime data
        """
        with self.lock:
            self._store["exit"].add(fn)
            return None

    @ensure_is_not_closed
    def create_bg_task(self, coro: Coroutine, name: str | None = None, replace: bool = False) -> asyncio.Task:
        """
        type:
            must be coroutines
            are stored as Tasks
        life:
            forever
        info:
            long-running tasks that need to be active in background
        ex:
            scheduled periodical tasks
        """
        with self.lock:
            if not iscoroutine(coro):
                raise TypeError(f"BG requires coroutine got: {coro}")

            if replace:
                self.cancel_tasks(name, "bg")

            task = self.loop.create_task(coro, name=name or str(coro))
            self._store["bg"].add(task)
            return task

    @ensure_is_not_closed
    def create_temp_task(self, coro: Coroutine, name: str, extra_callback: Callable = None) -> asyncio.Task:
        with self.lock:
            from .utils.helpers import run_unknown_callable

            temp_task: asyncio.Task = self.loop.create_task(coro, name=name)
            self._store["temp"].add(temp_task)
            temp_task.add_done_callback(
                lambda t: (
                    self._store["temp"].discard(t),
                    self.loop.create_task(run_unknown_callable(resource=extra_callback)),
                )
            )
            return temp_task

    @staticmethod
    async def _worker(function: Callable, interval: int, break_condition: Callable, name: str):
        from .utils.helpers import run_unknown_callable

        while True:
            if break_condition and await run_unknown_callable(break_condition):
                LOGGER.info(f"{name}: break_condition returned True... terminating worker...")
                return "break_condition returned True... terminating worker..."

            try:
                await run_unknown_callable(function)
            except asyncio.CancelledError:
                LOGGER.info(f"{name}: cancelled...")
                return
            except Exception as e:
                LOGGER.exception(e)

            await asyncio.sleep(interval)

    @ensure_is_not_closed
    def create_worker(self, function: Callable, interval: int, name: str = None, break_condition: Callable = None):
        """
        just a while loop wrapper for bg tasks,
        so you don't have to write worker code again and again

        @param function: any kind of function/awaitable
        @param interval: amount to sleep before next call
        @param break_condition: optional lambda/function that returns true to stop worker
        @param name: name for the worker
        @return: None
        """
        with self.lock:
            name = name or f"{function.__name__}-worker"
            coro = self._worker(function, interval, break_condition, name)
            task = self.loop.create_task(coro, name=name)
            self._store["workers"].add(task)
            return task

    @ensure_is_not_closed
    def get_tasks(self, name: str = None, task_type: str = None) -> Generator[asyncio.Task]:
        """
        get a specific task matching name and type
        if no args are given, get all tasks
        """
        if task_type and task_type not in self._store.keys():
            raise TypeError(f"get_tasks: Got unexpected type: {task_type}\nAvailable: {self._store.keys()}")

        set_to_search = self._store.get(task_type, []).copy() or self.all_tasks

        if name:
            yield from filter(lambda t: t.get_name() == name, set_to_search)
        else:
            yield from set_to_search

    @ensure_is_not_closed
    def cancel_tasks(self, name: str = None, task_type: str = None) -> set[asyncio.Task]:
        """
        cancel a specific task matching name and type
        if no args are given, cancel all tasks
        """
        tasks: set[asyncio.Task] = set(self.get_tasks(name, task_type))
        [task.cancel() for task in tasks if not (task.done() or task.cancelled())]
        return tasks

    @ensure_is_not_closed
    async def run_init_tasks(self):
        async with self.async_lock:
            results = await asyncio.gather(*self._store["init"], return_exceptions=True)
            [LOGGER.exception(result) for result in results if isinstance(result, BaseException)]
            LOGGER.info("Init Tasks Completed.")
            self._store["init"].clear()

    @ensure_is_not_closed
    async def close_and_run_exit_tasks(self):
        async with self.async_lock:
            LOGGER.info("Running exit tasks...")
            self.cancel_tasks()
            from .utils.helpers import run_unknown_callable

            for resource in self._store["exit"]:
                await run_unknown_callable(resource, ignore_errors=False)

            self.clear()
            self._closed = True
            LOGGER.info("Exit tasks Completed and Task manager is closed...")
