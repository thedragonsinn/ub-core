import asyncio
import os
import re
from logging import (
    ERROR,
    INFO,
    WARNING,
    Handler,
    LogRecord,
    StreamHandler,
    basicConfig,
    getLogger,
    handlers,
)

from ub_core import Config, Message, bot

os.makedirs(name="logs", exist_ok=True)

LOGGER = getLogger(Config.BOT_NAME)


class TgErrorHandler(Handler):
    """
    A Custom Logging Handler to Log Error and Above Events in TG LOG CHANNEL.
    """

    def emit(self, log_record: LogRecord):
        try:
            self.format(log_record)
            self.log_to_tg(log_record)
        except Exception as e:
            print(e)

    @staticmethod
    def log_to_tg(log_record: LogRecord):
        if not (bot.is_connected and bot.is_idling):
            return

        tg_message = getattr(log_record, "tg_message", None)

        if isinstance(tg_message, Message):
            chat = tg_message.chat
            chat_name: str = chat.title or chat.first_name
            chat_id: int = chat.id
        else:
            chat_name, chat_id = "", 0

        error_message: str = log_record.exc_text or log_record.message

        if log_record.funcName in ("handler_worker", "run") and "OSError:" in error_message:
            return

        text = (
            f"#{log_record.levelname} #TRACEBACK"
            f"<b>\nChat</b>: <code>{chat_name}</code> [<code>{chat_id}</code>]"
            f"\n<b>Line No</b>: <code>{log_record.lineno}</code>"
            f"\n<b>Func</b>: <code>{log_record.funcName}</code>"
            f"\n<b>Module</b>: <pre language=python>{log_record.pathname}</pre>"
            f"\n<b>Time</b>: <code>{log_record.asctime}</code>"
            f"\n<b>Error Message</b>:\n<pre language=python>{error_message}</pre>"
        )

        asyncio.run_coroutine_threadsafe(
            coro=bot.log_text(text=text, name="traceback.txt"), loop=bot.loop
        )


class OnNetworkIssueHandler(Handler):
    def emit(self, log_record: LogRecord):
        self.format(log_record)

        if log_record.funcName not in ("handler_worker", "run"):
            return

        error_message: str = log_record.exc_text or log_record.message

        is_network_error = re.search(r"handler is closed|TimeoutError", error_message)

        if is_network_error is None:
            return

        LOGGER.info("Network Issues Detected, Restarting client(s)")

        bot.raise_sigint()


custom_error_handler = TgErrorHandler()
custom_error_handler.setLevel(ERROR)

custom_network_error_handler = OnNetworkIssueHandler()
custom_network_error_handler.setLevel(WARNING)

basicConfig(
    level=INFO,
    format="%(asctime)s    |   %(levelname)s   |   %(name)s   |   %(module)s: %(message)s",
    datefmt="%d-%m-%y %I:%M %p",
    handlers={
        handlers.RotatingFileHandler(filename="logs/app_logs.txt", maxBytes=1024 * 256),
        StreamHandler(),
        custom_error_handler,
        custom_network_error_handler,
    },
)

getLogger("pyrogram").setLevel(WARNING)
getLogger("httpx").setLevel(WARNING)
getLogger("aiohttp.access").setLevel(WARNING)
