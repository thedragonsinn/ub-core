from io import BytesIO
from typing import TYPE_CHECKING

from pyrogram import Client
from pyrogram.types import LinkPreviewOptions, ReplyParameters
from pyrogram.utils import parse_text_entities

from ..types.message import Message

if TYPE_CHECKING:
    from pyrogram.enums import ParseMode
    from pyrogram.types import MessageEntity

    from ..client import BOT


class SendMessage(Client):

    # noinspection PyMethodOverriding
    async def send_message(
        self: "BOT",
        chat_id: int | str,
        text: str,
        parse_mode: "ParseMode" = None,
        entities: list["MessageEntity"] = None,
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

        text_and_entities = await parse_text_entities(
            client=self,
            text=text,
            parse_mode=parse_mode or self.parse_mode,
            entities=entities,
        )

        if len(text_and_entities["message"]) <= 4096:
            if isinstance(disable_preview, bool):
                kwargs["link_preview_options"] = LinkPreviewOptions(
                    is_disabled=disable_preview
                )
            message = await super().send_message(
                chat_id=chat_id,
                text=text,
                # Pyrogram Shenanigans for not accepting parsed values.
                # text=text_and_entities["message"],
                # entities=text_and_entities["entities"],
                entities=entities,
                parse_mode=parse_mode,
                **kwargs,
            )
            return Message(message=message)

        kwargs.pop("link_preview_options", None)

        doc = BytesIO(bytes(text, encoding="utf-8"))
        doc.name = name
        return (await super().send_document(
            chat_id=chat_id, document=doc, **kwargs
        ))  # fmt: skip
