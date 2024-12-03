from io import BytesIO
from typing import TYPE_CHECKING

from pyrogram import Client
from pyrogram.types import LinkPreviewOptions, ReplyParameters

from ..types.message import Message

if TYPE_CHECKING:
    from ..client import BOT


class SendMessage(Client):

    # noinspection PyMethodOverriding
    async def send_message(
        self: "BOT",
        chat_id: int | str,
        text: str,
        name: str = "output.txt",
        disable_preview: bool = None,
        reply_to_id: int = 0,
        **kwargs,
    ) -> Message | None:
        """
        Custom Method to Gracefully Handle text over 4096 chars. \n
        Sends a document if text goes over the limit.
        """

        if reply_to_id:
            kwargs["reply_parameters"] = ReplyParameters(message_id=reply_to_id)

        if not isinstance(text, str):
            text = str(text)

        if len(text) < 4096:
            if isinstance(disable_preview, bool):
                kwargs["link_preview_options"] = LinkPreviewOptions(
                    is_disabled=disable_preview
                )
            message = await super().send_message(
                chat_id=chat_id,
                text=text,
                **kwargs,
            )
            return Message(message=message)

        doc = BytesIO(bytes(text, encoding="utf-8"))
        doc.name = name
        return (await super().send_document(
            chat_id=chat_id, document=doc, **kwargs
        ))  # fmt: skip
