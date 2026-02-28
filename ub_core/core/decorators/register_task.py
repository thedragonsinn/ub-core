import inspect
from collections.abc import Callable

from ...config import Config


class RegisterTask:
    @staticmethod
    def register_task(
        task_type: str, name: str = None, replace: bool = False, ignore_if_exists: bool = False
    ):
        """
        Adds tasks to init | bg | exit sets in Config.TaskManager
        init and bg tasks expect an async function.
        """

        name = name or inspect.stack()[1][1]

        def inner(func: Callable):
            tasks_with_same_name = Config.TASK_MANAGER.get_tasks(name, task_type)

            if tasks_with_same_name:
                if ignore_if_exists:
                    return func

                if replace is False:
                    raise RuntimeError(
                        f"create_task: a task with name:{name} already is running in type:{task_type}.\n"
                        f"pass replace=True to cancel previous task."
                    )

            if task_type == "exit":
                Config.TASK_MANAGER.create_task(func, name=name, task_type=task_type, replace=replace)
            else:
                Config.TASK_MANAGER.create_task(func(), name=name, task_type=task_type, replace=replace)
            return func

        return inner
