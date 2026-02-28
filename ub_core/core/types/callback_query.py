from io import BytesIO
from typing import TYPE_CHECKING, Any, Self

from pyrogram import types, utils

from .extra_properties import Properties
from ...config import Config

if TYPE_CHECKING:
    from pyrogram.enums import ParseMode

    from ..client import DualClient


class CallbackQuery(Properties, types.CallbackQuery):
    """A Custom CallbackQuery Class with ease of access methods"""

    _client: "DualClient"
    text: str

    def __init__(self, callback_query: types.CallbackQuery | Self) -> None:
        super().__init__(
            **self.sanitize_update(
                callback_query,
                _Super=types.CallbackQuery,
                _SubClass=CallbackQuery,
                instance_variables_to_rm=["text"],
            )
        )

        if isinstance(self.data, bytes):
            self.data = self.data.decode()

        if isinstance(callback_query, CallbackQuery):
            self.text = callback_query.text
            return

        if inline_data := Config.INLINE_QUERY_CACHE.pop(self.data, {}):
            self.text = inline_data["text"]
        else:
            self.text = ""

    @classmethod
    def parse(cls, update) -> Self:
        return update if isinstance(update, CallbackQuery) else cls(update)

    async def edit_message_text(
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
        **kwargs,
    ) -> Self:
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

            await super().edit_message_text(
                text=text,
                parse_mode=parse_mode,
                link_preview_options=link_preview_options,
                reply_markup=reply_markup,
            )

        else:
            doc = BytesIO(bytes(text, encoding="utf-8"))
            doc.name = name
            await self.edit_message_media(
                media=types.InputMediaDocument(media=doc, file_name=doc.name)
            )
        return self

    async def edit_message_media(self, *args, **kwargs) -> Self:
        await super().edit_message_media(*args, **kwargs)
        return self

    edit = edit_text = reply = reply_text = edit_message_text
    edit_media = edit_message_media
    edit_reply_markup = types.CallbackQuery.edit_message_reply_markup
