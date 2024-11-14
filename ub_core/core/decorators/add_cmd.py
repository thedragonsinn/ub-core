import inspect
from typing import Callable

from ...config import Cmd, Config


class AddCmd:
    @staticmethod
    def add_cmd(cmd: str | list[str], allow_sudo: bool = True):
        """A Custom Decorator to add commands to bot and alternative to pyro's on_message"""

        def the_decorator(func: Callable):
            path = inspect.stack()[1][1]
            if isinstance(cmd, list):
                for _cmd in cmd:
                    Config.CMD_DICT[_cmd] = Cmd(
                        cmd=_cmd, func=func, cmd_path=path, sudo=allow_sudo
                    )
            else:
                Config.CMD_DICT[cmd] = Cmd(
                    cmd=cmd, func=func, cmd_path=path, sudo=allow_sudo
                )

            return func

        return the_decorator
