import os
from logging import ERROR, INFO, WARNING, Formatter, StreamHandler, basicConfig, getLogger, handlers

from .telegram_log_record_handler import OnNetworkIssueHandler, TgErrorHandler
from ... import Config

os.makedirs(name="logs", exist_ok=True)

LOGGER = getLogger(Config.BOT_NAME)

COLORS = {
    INFO: "\033[32m",  # GREEN
    WARNING: "\033[33m",  # YELLOW
    ERROR: "\033[31m",  # RED
}
DIM = "\033[2m"
RESET = "\033[0m"


class ColorFormatter(Formatter):
    def __init__(self, handler_name: str, datefmt="%d-%m-%y %I:%M %p", **kwargs):
        super().__init__(datefmt=datefmt, **kwargs)
        self.handler_name = handler_name

    def format(self, record):
        super().format(record)

        if getattr(record, "raw", False):
            return record.getMessage() or record.exc_text

        record.asctime = self.formatTime(record, self.datefmt)

        if self.handler_name == "stream_handler" and os.getenv("COLORTERM") == "truecolor":
            level_color = COLORS.get(record.levelno, "")
            if record.levelno >= ERROR:
                level_color = COLORS[ERROR]

            timestamp = DIM + record.asctime + RESET
            level = f"{level_color}{record.levelname}{RESET}"
            message = f"{level_color}{record.getMessage()}{RESET}"
            formatted_text = f"{level}  {timestamp}  [{record.name} : {record.module}]  {message}"
        else:
            formatted_text = f"{record.levelname}  {record.asctime}  [{record.name} : {record.module}]  {record.getMessage()}"

        if record.exc_text:
            formatted_text += f"\n{record.exc_text}"

        return formatted_text


custom_error_handler = TgErrorHandler()
custom_error_handler.setLevel(ERROR)
custom_error_handler.setFormatter(ColorFormatter("tg_error_handler"))

custom_network_error_handler = OnNetworkIssueHandler()
custom_network_error_handler.setLevel(WARNING)
custom_network_error_handler.setFormatter(ColorFormatter("network_error_handler"))


file_handler = handlers.TimedRotatingFileHandler(filename="logs/app_logs.txt", when="W3", encoding="utf-8")
file_handler.setFormatter(ColorFormatter("file_handler"))

stream_handler = StreamHandler()
stream_handler.setFormatter(ColorFormatter("stream_handler"))

basicConfig(
    level=INFO,
    handlers={
        file_handler,
        stream_handler,
        custom_error_handler,
        custom_network_error_handler,
    },
)


getLogger("pyrogram").setLevel(WARNING)
getLogger("httpx").setLevel(WARNING)
getLogger("aiohttp.access").setLevel(WARNING)
