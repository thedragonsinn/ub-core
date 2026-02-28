from collections.abc import Callable

from ...config import Config


class RegisterWorker:
    @staticmethod
    def register_worker(
        interval: int,
        break_condition: Callable = None,
        name: str = None,
        ignore_if_exists: bool = True,
    ):
        def inner(function: Callable):
            _name = name or f"{function.__name__}-worker"

            tasks_with_same_name = Config.TASK_MANAGER.get_tasks(_name, "workers")

            if tasks_with_same_name:
                if ignore_if_exists:
                    return function

            Config.TASK_MANAGER.create_worker(
                function=function, interval=interval, name=_name, break_condition=break_condition
            )
            return function

        return inner
