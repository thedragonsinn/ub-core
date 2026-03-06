import inspect
from collections.abc import Callable

from ...config import Config


class RegisterTask:
    @staticmethod
    def register_init(fn: Callable) -> Callable:
        Config.TASK_MANAGER.add_init(fn())
        return fn

    @staticmethod
    def register_exit(fn: Callable) -> Callable:
        Config.TASK_MANAGER.add_exit(fn)
        return fn

    @staticmethod
    def register_bg_task(
        name: str = None,
        replace: bool = False,
        ignore_if_exists: bool = False,
    ) -> Callable:
        """
        Adds tasks to init | bg | exit sets in Config.TaskManager
        init and bg tasks expect an async function.
        """

        name = name or inspect.stack()[1][1]

        def inner(func: Callable):
            tasks_with_same_name = Config.TASK_MANAGER.get_tasks(name, "bg")

            if tasks_with_same_name:
                if ignore_if_exists:
                    return func

                if replace is False:
                    raise RuntimeError(
                        f"create_task: a task with name:{name} already is running in background.\n"
                        f"pass replace=True to cancel previous task."
                    )

                Config.TASK_MANAGER.create_bg_task(func(), name=name, replace=replace)
            return func

        return inner
