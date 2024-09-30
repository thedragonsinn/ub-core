import asyncio
import os
import re
from logging import (
    ERROR,
    INFO,
    WARNING,
    Handler,
    StreamHandler,
    basicConfig,
    getLogger,
    handlers,
)

from ub_core import Config, bot

os.makedirs(name="logs", exist_ok=True)

LOGGER = getLogger(Config.BOT_NAME)


class TgErrorHandler(Handler):
    """
    A Custom Logging Handler to Log Error and Above Events in TG LOG CHANNEL.
    """

    def emit(self, log_record):
        try:
            self.format(log_record)
            self.log_to_tg(log_record)
        except Exception as e:
            print(e)

    @staticmethod
    def log_to_tg(log_record):
        if not (bot.is_connected and bot.is_idling):
            return

        try:
            chat = (
                log_record.tg_message.chat.title
                or log_record.tg_message.chat.first_name
            )
        except BaseException:
            chat = ""

        text = (
            f"#{log_record.levelname} #TRACEBACK"
            f"<b>\nChat</b>: {chat}"
            f"\n<b>Line No</b>: <code>{log_record.lineno}</code>"
            f"\n<b>Func</b>: <code>{log_record.funcName}</code>"
            f"\n<b>Module</b>: <pre language=python>{log_record.pathname}</pre>"
            f"\n<b>Time</b>: <code>{log_record.asctime}</code>"
            f"\n<b>Error Message</b>:\n<pre language=python>{log_record.exc_text or log_record.message}</pre>"
        )

        asyncio.run_coroutine_threadsafe(
            coro=bot.log_text(text=text, name="traceback.txt"), loop=bot.loop
        )


class NetworkAndPyroHandlerIssuesHandler(Handler):
    CLOSED_HANDLER_REGEX = (
        r"\[WARNING\] \[\d{2}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} [AP]M\]"
        r" \[pyrogram\.session\.session\] \[session\]: \[\d+\] "
        r'Retrying "[^"]+" due to: unable to perform operation on '
        r"<TCPTransport closed=True reading=False [^>]+>; the handler is closed"
    )

    def emit(self, log_record):
        warning = self.format(log_record)

        if log_record.levelno != WARNING:
            return

        if re.search(self.CLOSED_HANDLER_REGEX, warning):
            LOGGER.info("Network Issues Detected, Restarting client(s)")
            bot.raise_sigint()


custom_error_handler = TgErrorHandler()
custom_error_handler.setLevel(ERROR)

custom_network_error_handler = NetworkAndPyroHandlerIssuesHandler()
custom_network_error_handler.setLevel(WARNING)

basicConfig(
    level=INFO,
    format="[%(levelname)s] [%(asctime)s] [%(name)s] [%(module)s]: %(message)s",
    datefmt="%d-%m-%y %I:%M:%S %p",
    handlers={
        handlers.RotatingFileHandler(
            filename="logs/app_logs.txt",
            mode="a",
            maxBytes=5 * 1024 * 1024,
            backupCount=2,
            encoding=None,
            delay=False,
        ),
        StreamHandler(),
        custom_error_handler,
        custom_network_error_handler,
    },
)

getLogger("pyrogram").setLevel(WARNING)
getLogger("httpx").setLevel(WARNING)
getLogger("aiohttp.access").setLevel(WARNING)
