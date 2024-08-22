from typing import Callable

from pyrogram import Client
from pyrogram.filters import Filter
from pyrogram.handlers import MessageHandler


class OnMessage(Client):
    def on_message(
        self=None,
        filters=None,
        group: int = 2,
        mode_sensitive: bool = False,
        is_command: bool = False,
    ):
        from ub_core.core.handlers import cmd_dispatcher

        def decorator(func: Callable) -> Callable:

            async def dispatch_wrapper(client, message):
                await cmd_dispatcher(
                    client=client,
                    message=message,
                    func=func,
                    check_for_reactions=False,
                    mode_sensitive=mode_sensitive,
                    is_command=is_command,
                )

            if isinstance(self, Client):
                self.add_handler(MessageHandler(dispatch_wrapper, filters), group)

            elif isinstance(self, Filter) or self is None:
                if not hasattr(func, "handlers"):
                    func.handlers = []

                func.handlers.append(
                    (MessageHandler(func, self), group if filters is None else filters)
                )

            return dispatch_wrapper

        return decorator
