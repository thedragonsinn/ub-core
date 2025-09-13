from collections.abc import Callable
from functools import wraps
from typing import TYPE_CHECKING

from pyrogram import Client
from pyrogram.filters import Filter
from pyrogram.handlers import CallbackQueryHandler

if TYPE_CHECKING:
    from ..client import DualClient


class OnCallbackQuery(Client):
    def on_callback_query(
        self: "DualClient" = None,
        filters: Filter = None,
        group: int = 2,
    ) -> Callable:
        def decorator(func: Callable) -> Callable:
            from ..handlers import cmd_dispatcher

            @wraps(func)
            async def dispatch_wrapper(client, callback_query):
                await cmd_dispatcher(
                    client=client,
                    update=callback_query,
                    func=func,
                    check_for_reactions=False,
                    mode_sensitive=False,
                    is_command=False,
                )

            if isinstance(self, Client):
                self.add_handler(CallbackQueryHandler(dispatch_wrapper, filters), group)
            elif isinstance(self, Filter) or self is None:
                if not hasattr(func, "handlers"):
                    func.handlers = []

                func.handlers.append(
                    (
                        CallbackQueryHandler(dispatch_wrapper, self),
                        group if filters is None else filters,
                    )
                )

            return dispatch_wrapper

        return decorator
