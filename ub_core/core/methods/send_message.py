from io import BytesIO
from typing import TYPE_CHECKING

from pyrogram import Client

from ..types.message import Message

if TYPE_CHECKING:
    from ..client import BOT


class SendMessage(Client):
    async def send_message(
        self: "BOT",
        chat_id: int | str,
        text,
        name: str = "output.txt",
        disable_web_page_preview: bool = False,
        **kwargs,
    ) -> Message:
        """
        Custom Method to Gracefully Handle text over 4096 chars. \n
        Sends a document if text goes over the limit.
        """

        if not isinstance(text, str):
            text = str(text)

        if len(text) < 4096:
            message = await super().send_message(
                chat_id=chat_id,
                text=text,
                disable_web_page_preview=disable_web_page_preview,
                **kwargs,
            )
            return Message.parse(message=message)

        doc = BytesIO(bytes(text, encoding="utf-8"))
        doc.name = name
        return (await super().send_document(
            chat_id=chat_id, document=doc, **kwargs
        ))  # fmt: skip
