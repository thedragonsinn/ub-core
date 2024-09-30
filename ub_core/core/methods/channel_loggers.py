import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from pyrogram import Client
from pyrogram.enums import ParseMode

from ...config import Config

if TYPE_CHECKING:
    from ..client import BOT
    from ..types.message import Message

LOGGER = logging.getLogger(Config.BOT_NAME)


class ChannelLogger(Client):
    async def log_text(
        self: "BOT",
        text,
        name="log.txt",
        disable_web_page_preview=True,
        parse_mode=ParseMode.HTML,
        type: str = "",
    ) -> "Message":
        """Log Text to Channel and to Stream/File if type matches logging method."""

        if type:
            if hasattr(LOGGER, type):
                getattr(LOGGER, type)(text)
            text = f"#{type.upper()}\n{text}"

        schedule_date = None
        if not self.me.is_bot:
            schedule_date = datetime.utcnow() + timedelta(seconds=10)

        return (await self.send_message(
            chat_id=Config.LOG_CHAT,
            text=text,
            name=name,
            disable_web_page_preview=disable_web_page_preview,
            parse_mode=parse_mode,
            schedule_date=schedule_date,
            disable_notification=False,
        ))  # fmt:skip

    async def log_message(self, message: "Message") -> "Message":
        """Log a Message to Log Channel"""
        schedule_date = None
        if not self.me.is_bot:
            schedule_date = datetime.utcnow() + timedelta(seconds=10)
        return (await message.copy(
            chat_id=Config.LOG_CHAT,
            schedule_date=schedule_date,
            disable_notification=False,
        ))  # fmt:skip
