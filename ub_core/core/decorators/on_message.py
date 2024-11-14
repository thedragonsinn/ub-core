from functools import wraps
from typing import Callable

from pyrogram import Client
from pyrogram.filters import Filter
from pyrogram.handlers import MessageHandler


class OnMessage(Client):
    """
    Override OG on_message to re-add edited support which was removed in Pyro V2.
    Also use a custom dispatcher to gracefully handle command cancellation and other errors.
    """

    def on_message(
        self=None,
        filters=None,
        group: int = 2,
        mode_sensitive: bool = False,
        is_command: bool = False,
        check_for_reactions: bool = False,
        filters_edited: bool = False,
    ):
        from ..handlers import UnifiedHandler, cmd_dispatcher

        handler = UnifiedHandler if filters_edited else MessageHandler

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
                self.add_handler(handler(dispatch_wrapper, filters), group)

            elif isinstance(self, Filter) or self is None:
                if not hasattr(func, "handlers"):
                    func.handlers = []

                func.handlers.append(
                    (
                        handler(dispatch_wrapper, self),
                        group if filters is None else filters,
                    )
                )

            return dispatch_wrapper

        return decorator
