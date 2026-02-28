import asyncio
import json
import logging
from asyncio import Task
from collections.abc import Callable, Coroutine
from functools import wraps
from inspect import isawaitable, iscoroutine

LOGGER = logging.getLogger("Config")


def ensure_is_not_closed(function):
    @wraps(function)
    def inner(self, *args, **kwargs):
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
        """
        INIT:
            type:
                must be coroutines/awaitable
            life:
                cleared after call to run_ini_tasks before bot idles
            info:
                to register an init task on module level, name it init_task
                they are automatically loaded via core.client.import_modules
                init_task and @register_task(type=init) are mutually exclusive
                DO NOT NAME FUNCTION init_task and then do @bot.register_task(type=init)
                THIS WILL DUPLICATE IT.
            ex:
                funcs to extract and set data from db / files etc

        BG:
            type:
                must be coroutines and are stored as Tasks
            life:
                forever
            info:
                long-running tasks that need to be active in background
            ex:
                scheduled periodical tasks

        EXIT:
            type:
                can be any kind of function
            life:
                till end of run
            info:
                functions to call before bot exits and closes interpreter
            ex:
                closing open fds, connections, objects, dumping runtime data

        TEMP:
            type:
                must be coroutines and are stored as Tasks
            life:
                until function completes
            info:
                better alternative to unassigned asyncio.create_task that stores tasks
                and doesn't let them get garbage collected until finished
            ex:
                sleep(10)
                do something
                run optional done callback

        WORKERS:
            type, life: same as background
            info:
                just has a while loop wrapper,
                so you don't have to write worker code again and again
        """

        self._closed: bool = False
        self._store = {
            "init": set(),
            "bg": set(),
            "exit": set(),
            "temp": set(),
            "workers": set(),
        }

    def __str__(self) -> str:
        return json.dumps(self._store, indent=4, ensure_ascii=False, default=str)

    @property
    def is_closed(self):
        return self._closed

    @property
    def all_tasks(self) -> set:
        return set.union(*self._store.values())

    @ensure_is_not_closed
    def create_task(
        self, t: Coroutine | Callable, task_type: str, name: str = None, replace: bool = False
    ) -> Task | Coroutine | Callable:
        match task_type:
            case "init":
                if not isawaitable(t):
                    raise TypeError(f"INIT requires an awaitable got: {t}")
                self._store["init"].add(t)
                return t

            case "bg":
                if not iscoroutine(t):
                    raise TypeError(f"BG requires a coroutine got: {t}")

                if replace:
                    self.cancel_tasks(name, "bg")

                new_task = asyncio.create_task(t, name=name or str(t))
                self._store["bg"].add(new_task)
                return new_task

            case "exit":
                self._store["exit"].add(t)
                return t

            case _:
                raise TypeError(
                    f"create_task: Got unexpected task_type: {task_type}\nAvailable: init, bg, exit"
                )

    @ensure_is_not_closed
    def create_temp_task(self, coro: Coroutine, name: str, extra_callback: Callable = None) -> Task:
        from .utils.helpers import run_unknown_callable

        temp_task: Task = asyncio.create_task(coro, name=name)
        self._store["temp"].add(temp_task)
        temp_task.add_done_callback(
            lambda t: (
                self._store["temp"].discard(t),
                asyncio.create_task(run_unknown_callable(resource=extra_callback)),
            )
        )
        return temp_task

    @ensure_is_not_closed
    def create_worker(
        self, function: Callable, interval: int, break_condition: Callable = None, name: str = None
    ):
        """
        @param function: any kind of function/awaitable
        @param interval: amount to sleep before next call
        @param break_condition: optional lambda/function that returns true to stop worker
        @param name: name for the worker
        @return: None
        """
        name = name or f"{function.__name__}-worker"

        async def worker():
            from .utils.helpers import run_unknown_callable

            while True:
                if break_condition and await run_unknown_callable(break_condition):
                    LOGGER.info(f"{name}: break_condition returned True... terminating worker...")
                    return
                try:
                    await run_unknown_callable(function)
                except asyncio.CancelledError:
                    LOGGER.info(f"{name}: cancelled...")
                    return
                except Exception as e:
                    LOGGER.exception(e)
                await asyncio.sleep(interval)

        task = asyncio.create_task(worker(), name=name)
        self._store["workers"].add(task)
        return task

    @ensure_is_not_closed
    def get_tasks(self, name: str = None, task_type: str = None) -> set[Task]:
        """
        get a specific task matching name and type
        if no args are given, get all tasks
        """
        if task_type and task_type not in self._store.keys():
            raise TypeError(
                f"get_tasks: Got unexpected type: {task_type}\nAvailable: {self._store.keys()}"
            )

        set_to_search = (self._store.get(task_type) or self.all_tasks).copy()

        if name:
            return filter(lambda t: isinstance(t, Task) and t.get_name() == name, set_to_search)
        else:
            return filter(lambda t: isinstance(t, Task), set_to_search)

    @ensure_is_not_closed
    def cancel_tasks(self, name: str = None, task_type: str = None) -> set[Task]:
        """
        cancel a specific task matching name and type
        if no args are given, cancel all tasks
        """
        tasks: set[Task] = self.get_tasks(name, task_type)
        [task.cancel() for task in tasks if not (task.done() or task.cancelled())]
        return tasks

    @ensure_is_not_closed
    async def run_init_tasks(self):
        results = await asyncio.gather(*self._store["init"], return_exceptions=True)
        [LOGGER.exception(result) for result in results if isinstance(result, BaseException)]
        LOGGER.info("Init Tasks Completed.")
        self._store["init"].clear()

    @ensure_is_not_closed
    async def close_and_run_exit_tasks(self):
        LOGGER.info("Running exit tasks...")
        self.cancel_tasks()
        from .utils.helpers import run_unknown_callable

        for resource in self._store["exit"]:
            await run_unknown_callable(resource, ignore_errors=True)

        self._store.clear()
        self._closed = True
        LOGGER.info("Exit tasks Completed and Task manager is closed...")
