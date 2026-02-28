from io import BytesIO
from typing import TYPE_CHECKING, Any, Self

from pyrogram import types, utils

from .extra_properties import Properties

if TYPE_CHECKING:
    from pyrogram.enums import ParseMode

    from ..client import DualClient


class InlineResult(Properties, types.ChosenInlineResult):
    _client: "DualClient"
    text: str
    id: str

    def __init__(self, inline_result: types.ChosenInlineResult | Self) -> None:
        super().__init__(
            **self.sanitize_update(
                inline_result,
                _Super=types.ChosenInlineResult,
                _SubClass=InlineResult,
                instance_variables_to_rm=["id", "text"],
            )
        )

        if isinstance(inline_result, InlineResult):
            self.text = inline_result.text
            self.id = self.inline_message_id
            return

        self.id = self.inline_message_id
        self.text = self.query

    @classmethod
    def parse(cls, update) -> Self:
        return update if isinstance(update, cls) else cls(update)

    async def edit_text(
        self,
        text: str | Any,
        name: str = "output.txt",
        del_in: int = 0,
        block: bool = True,
        disable_preview: bool = None,
        entities: list["types.MessageEntity"] = None,
        parse_mode: "ParseMode" = None,
        link_preview_options: types.LinkPreviewOptions = None,
        reply_markup: "types.InlineKeyboardMarkup" = None,
        **_,
    ):
        if not isinstance(text, str):
            text = str(text)

        text_and_entities = await utils.parse_text_entities(
            client=self._client,
            text=text,
            parse_mode=parse_mode or self._client.parse_mode,
            entities=entities,
        )
        if len(text_and_entities["message"]) <= 4096:
            if isinstance(disable_preview, bool):
                link_preview_options = types.LinkPreviewOptions(is_disabled=disable_preview)

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
            await self.edit_media(media=types.InputMediaDocument(media=doc, file_name=doc.name))

        return self

    edit = reply = reply_text = edit_text

    async def edit_media(
        self, media: types.InputMedia, *_, reply_markup: "types.InlineKeyboardMarkup" = None, **__
    ):
        await self._client.edit_inline_media(
            inline_message_id=self.inline_message_id,
            media=media,
            reply_markup=reply_markup,
        )

    async def edit_reply_markup(self, reply_markup: "types.InlineKeyboardMarkup" = None):
        return await self._client.edit_inline_reply_markup(
            inline_message_id=self.inline_message_id, reply_markup=reply_markup
        )
