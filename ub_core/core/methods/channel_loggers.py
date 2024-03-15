import logging

from pyrogram import Client
from pyrogram.enums import ParseMode

from ub_core import Config
from ub_core.core.types.message import Message

LOGGER = logging.getLogger(Config.BOT_NAME)


class ChannelLogger(Client):
    async def log_text(
        self,
        text,
        name="log.txt",
        disable_web_page_preview=True,
        parse_mode=ParseMode.HTML,
        type: str = "",
    ) -> Message:
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
            disable_web_page_preview=disable_web_page_preview,
            parse_mode=parse_mode,
            disable_notification=False,
        ))  # fmt:skip

    async def log_message(self, message: Message):
        """Log a Message to Log Channel"""
        return (await message.copy(
            chat_id=Config.LOG_CHAT,
            disable_notification=False,
        ))  # fmt:skip
