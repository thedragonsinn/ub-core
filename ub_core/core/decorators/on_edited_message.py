from collections.abc import Callable
from functools import wraps
from typing import TYPE_CHECKING

from pyrogram import Client
from pyrogram.filters import Filter
from pyrogram.handlers import EditedMessageHandler

if TYPE_CHECKING:
    from ..client import DualClient


class OnEditedMessage(Client):
    def on_edited_message(
        self: "DualClient" = None,
        filters=None,
        group: int = 2,
        mode_sensitive: bool = False,
        check_for_reactions: bool = False,
        is_command: bool = False,
        register_on_bot_too: bool = False,
    ):
        from ..handlers import cmd_dispatcher

        # noinspection PyUnresolvedReferences
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def dispatch_wrapper(client, message):
                await cmd_dispatcher(
                    client=client,
                    update=message,
                    func=func,
                    check_for_reactions=check_for_reactions,
                    mode_sensitive=mode_sensitive,
                    is_command=is_command,
                )

            if isinstance(self, Client):
                self.add_handler(EditedMessageHandler(dispatch_wrapper, filters), group)

                if register_on_bot_too and self.has_bot:
                    self.bot.add_handler(EditedMessageHandler(dispatch_wrapper, filters), group)

            elif isinstance(self, Filter) or self is None:
                if not hasattr(func, "handlers"):
                    func.handlers = []

                func.handlers.append(
                    (
                        EditedMessageHandler(dispatch_wrapper, self),
                        group if filters is None else filters,
                    )
                )

            return dispatch_wrapper

        return decorator
