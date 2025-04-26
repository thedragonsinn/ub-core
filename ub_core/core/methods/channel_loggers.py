import logging
from typing import TYPE_CHECKING

from pyrogram import Client
from pyrogram.enums import ParseMode

from ...config import Config

if TYPE_CHECKING:
    from ..client import DualClient
    from ..types.message import Message

LOGGER = logging.getLogger(Config.BOT_NAME)


class ChannelLogger(Client):
    async def log_text(
        self: "DualClient",
        text,
        name="log.txt",
        disable_preview=True,
        parse_mode=ParseMode.HTML,
        type: str = "",
    ) -> "Message":
        """Log Text to Channel and to Stream/File if type matches logging method."""

        if type:
            if hasattr(LOGGER, type):
                getattr(LOGGER, type)(text)
            text = f"#{type.upper()}\n{text}"

        if self.bot:
            client = self.bot
        else:
            client = self

        return (await client.send_message(
            chat_id=Config.LOG_CHAT,
            text=text,
            name=name,
            disable_preview=disable_preview,
            parse_mode=parse_mode,
            disable_notification=False,
            message_thread_id=Config.LOG_CHAT_THREAD_ID
        ))  # fmt:skip

    @staticmethod
    async def log_message(message: "Message") -> "Message":
        """Log a Message to Log Channel"""
        return (await message.copy(
            chat_id=Config.LOG_CHAT,
            disable_notification=False,
            message_thread_id=Config.LOG_CHAT_THREAD_ID
        ))  # fmt:skip
