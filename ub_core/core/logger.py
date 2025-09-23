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

from pyrogram.types import CallbackQuery, ChosenInlineResult

from ub_core import Config, Message, bot

os.makedirs(name="logs", exist_ok=True)

LOGGER = getLogger(Config.BOT_NAME)

UPDATE_TYPES = CallbackQuery, Message, ChosenInlineResult


def extract_message_from_traceback(tb) -> Message | None:
    while tb is not None:
        frame_locals = tb.tb_frame.f_locals
        if "message" in frame_locals:
            return frame_locals["message"]
        else:
            for value in frame_locals.values():
                if isinstance(value, UPDATE_TYPES):
                    return value
        tb = tb.tb_next
    return None


def extract_message_info(message: Message | None) -> tuple[int, int, str]:
    message_id = getattr(message, "id", 0)
    chat = getattr(message, "chat", None)

    if chat is not None:
        chat_name: str = chat.title or chat.first_name
        chat_id: int = chat.id
        return message_id, chat_id, chat_name
    else:
        return message_id, 0, ""


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

        error_message: str = log_record.exc_text or log_record.message

        if log_record.funcName in ("handler_worker", "run") and (
            "OSError:" in error_message or "The server sent an unknown constructor" in error_message
        ):
            return

        if hasattr(log_record, "tg_message"):
            tg_message = log_record.tg_message
        elif log_record.exc_info:
            tg_message = extract_message_from_traceback(log_record.exc_info[-1])
        else:
            tg_message = None

        message_id, chat_id, chat_name = extract_message_info(tg_message)

        text = (
            f"#{log_record.levelname} #TRACEBACK"
            f"\n<b>Chat</b>: <code>{chat_name}</code> [<code>{chat_id}</code>]"
            f"\n<b>Message ID</b>: <code>{message_id}</code>"
            f"\n<b>Line No</b>: <code>{log_record.lineno}</code>"
            f"\n<b>Func</b>: <code>{log_record.funcName}</code>"
            f"\n<b>Module</b>: <blockquote>{log_record.pathname}</blockquote>"
            f"\n<b>Time</b>: <code>{log_record.asctime}</code>"
            f"\n<b>Error Message</b>:\n<pre language=python>{error_message}</pre>"
        )

        if not hasattr(log_record, "tg_message") and tg_message:
            text += f"\nUpdate Object: <pre language=json>{tg_message}</pre>"

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
