from functools import cached_property
from io import BytesIO
from typing import TYPE_CHECKING, Any, Self

from pyrogram.types import ChosenInlineResult as InlineResultUpdate
from pyrogram.types import InputMedia, InputMediaDocument, LinkPreviewOptions
from pyrogram.utils import parse_text_entities

from .extra_properties import Properties

if TYPE_CHECKING:
    from pyrogram.enums import ParseMode
    from pyrogram.types import InlineKeyboardMarkup, MessageEntity

    from ..client import DualClient


class InlineResult(Properties, InlineResultUpdate):
    _client: "DualClient"
    text: str
    id: str

    def __init__(self, inline_result: InlineResultUpdate | Self) -> None:
        kwargs = self.sanitize_inline_result(inline_result)
        super().__init__(**kwargs)

        if isinstance(inline_result, InlineResult):
            self.text = inline_result.text
            self.id = self.inline_message_id
            return

        self.id = self.inline_message_id
        self.text = self.query

    @staticmethod
    def sanitize_inline_result(inline_result) -> dict:
        """Remove Extra/Custom Attrs from Message Object"""
        kwargs = vars(inline_result).copy()

        kwargs["client"] = kwargs.pop("_client", inline_result._client)

        kwargs.pop("id", 0)

        kwargs.pop("text", 0)

        for arg in dir(InlineResult):
            is_property = isinstance(getattr(InlineResult, arg, 0), cached_property | property)
            is_present_in_super = hasattr(InlineResultUpdate, arg)

            if is_property and not is_present_in_super:
                kwargs.pop(arg, 0)

        return kwargs

    @classmethod
    def parse(cls, update) -> Self:
        return update if isinstance(update, InlineResult) else cls(update)

    async def edit_text(
        self,
        text: str | Any,
        name: str = "output.txt",
        del_in: int = 0,
        block: bool = True,
        disable_preview: bool = None,
        entities: list["MessageEntity"] = None,
        parse_mode: "ParseMode" = None,
        link_preview_options: LinkPreviewOptions = None,
        reply_markup: "InlineKeyboardMarkup" = None,
        **_,
    ):
        if not isinstance(text, str):
            text = str(text)

        text_and_entities = await parse_text_entities(
            client=self._client,
            text=text,
            parse_mode=parse_mode or self._client.parse_mode,
            entities=entities,
        )
        if len(text_and_entities["message"]) <= 4096:
            if isinstance(disable_preview, bool):
                link_preview_options = LinkPreviewOptions(is_disabled=disable_preview)

            await self._client.edit_inline_text(
                inline_message_id=self.inline_message_id,
                text=text,
                parse_mode=parse_mode,
                entities=entities,
                link_preview_options=link_preview_options,
                reply_markup=reply_markup,
            )
        else:
            doc = BytesIO(bytes(text, encoding="utf-8"))
            doc.name = name
            await self.edit_media(media=InputMediaDocument(media=doc, file_name=doc.name))

        return self

    edit = reply = reply_text = edit_text

    async def edit_media(
        self, media: InputMedia, *_, reply_markup: "InlineKeyboardMarkup" = None, **__
    ):
        await self._client.edit_inline_media(
            inline_message_id=self.inline_message_id,
            media=media,
            reply_markup=reply_markup,
        )

    async def edit_reply_markup(self, reply_markup: "InlineKeyboardMarkup" = None):
        return await self._client.edit_inline_reply_markup(
            inline_message_id=self.inline_message_id, reply_markup=reply_markup
        )
