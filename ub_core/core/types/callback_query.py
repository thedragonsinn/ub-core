from functools import cached_property
from io import BytesIO
from typing import TYPE_CHECKING, Any, Self

from pyrogram.types import CallbackQuery as CallbackQueryUpdate
from pyrogram.types import InputMediaDocument, LinkPreviewOptions
from pyrogram.utils import parse_text_entities

from .extra_properties import Properties
from .message import Message
from ...config import Config

if TYPE_CHECKING:
    from pyrogram.enums import ParseMode
    from pyrogram.types import InlineKeyboardMarkup, MessageEntity

    from ..client import DualClient


class CallbackQuery(Properties, CallbackQueryUpdate):
    """A Custom CallbackQuery Class with ease of access methods"""

    _client: "DualClient"
    text: str

    def __init__(self, callback_query: CallbackQueryUpdate | Self) -> None:
        kwargs = self.sanitize_callback_query(callback_query)
        super().__init__(**kwargs)

        if isinstance(self.data, bytes):
            self.data = self.data.decode()

        if isinstance(callback_query, CallbackQuery):
            self.text = callback_query.text
            return

        if inline_data := Config.INLINE_QUERY_CACHE.pop(self.data, {}):
            self.text = inline_data["text"]
        else:
            self.text = ""

    @staticmethod
    def sanitize_callback_query(callback_query) -> dict:
        """Remove Extra/Custom Attrs from Message Object"""
        kwargs = vars(callback_query).copy()
        kwargs["client"] = kwargs.pop("_client", callback_query._client)
        kwargs.pop("text", 0)

        if callback_query.message:
            kwargs["message"] = Message(kwargs.pop("message"))

        for arg in dir(CallbackQuery):
            is_property = isinstance(getattr(CallbackQuery, arg, 0), (cached_property, property))
            is_present_in_super = hasattr(CallbackQueryUpdate, arg)

            if is_property and not is_present_in_super:
                kwargs.pop(arg, 0)

        return kwargs

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
        entities: list["MessageEntity"] = None,
        parse_mode: "ParseMode" = None,
        link_preview_options: LinkPreviewOptions = None,
        reply_markup: "InlineKeyboardMarkup" = None,
        **kwargs,
    ) -> Self:

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

            await super().edit_message_text(
                text=text,
                parse_mode=parse_mode,
                link_preview_options=link_preview_options,
                reply_markup=reply_markup,
            )

        else:
            doc = BytesIO(bytes(text, encoding="utf-8"))
            doc.name = name
            await self.edit_message_media(media=InputMediaDocument(media=doc, file_name=doc.name))
        return self

    async def edit_message_media(self, *args, **kwargs) -> Self:
        await super().edit_message_media(*args, **kwargs)
        return self

    edit = edit_text = reply = reply_text = edit_message_text
    edit_media = edit_message_media
    edit_reply_markup = CallbackQueryUpdate.edit_message_reply_markup
