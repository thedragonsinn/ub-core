from functools import cached_property
from io import BytesIO
from typing import TYPE_CHECKING, Any, Self

from pyrogram.types import CallbackQuery as CallbackQueryUpdate
from pyrogram.types import LinkPreviewOptions
from pyrogram.utils import parse_text_entities

from .message import Message
from ...config import Config

if TYPE_CHECKING:
    from pyrogram.enums import ParseMode
    from pyrogram.types import InlineKeyboardMarkup, MessageEntity

    from ..client import DualClient


def construct_properties(inline_query_id: str) -> tuple[str, list[str], str, str]:

    if inline_query_id not in Config.INLINE_QUERY_CACHE:
        return "", [], "", ""

    cmd, text = (Config.INLINE_QUERY_CACHE.pop(inline_query_id)).values()

    flags = [i for i in text.split() if i.startswith("-")]

    input = text

    split_lines = input.split(sep="\n", maxsplit=1)

    split_lines[0] = " ".join(
        [word for word in split_lines[0].split(" ") if word not in flags]
    )

    filtered_input = "\n".join(split_lines)

    return cmd, flags, input, filtered_input


class CallbackQuery(CallbackQueryUpdate):
    """A Custom CallbackQuery Class with ease of access methods"""

    _client: "DualClient"
    _fake_properties = (
        "cmd",
        "flags",
        "input",
        "filtered_input",
        "reply_text_list",
        "replied",
        "reply_id",
        "replied_task_id",
    )

    def __init__(self, callback_query: CallbackQueryUpdate | Self) -> None:
        kwargs = self.sanitize_cq(callback_query)
        super().__init__(**kwargs)

        if isinstance(self.data, bytes):
            self.data = self.data.decode("utf-8")

        if isinstance(callback_query, CallbackQuery):
            for attr in self._fake_properties:
                old_attr = getattr(callback_query, attr)
                setattr(self, attr, old_attr)

            return

        self.cmd, self.flags, self.input, self.filtered_input = construct_properties(
            self.data
        )

        self.reply_text_list = []
        self.replied = self.reply_id = self.replied_task_id = None

    @cached_property
    def is_from_owner(self) -> bool:
        """Returns True if message is from Owner of bot."""
        return self.from_user and self.from_user.id == Config.OWNER_ID

    @cached_property
    def task_id(self) -> str:
        """Task ID to Cancel/Track Command Progress."""
        return self.id

    @cached_property
    def trigger(self) -> str:
        """Returns Cmd or Sudo Trigger"""
        # Legacy w/o db and sudo support
        if hasattr(Config, "TRIGGER"):
            return Config.TRIGGER

        return Config.CMD_TRIGGER if self.is_from_owner else Config.SUDO_TRIGGER

    @cached_property
    def unique_chat_user_id(self) -> int | str:
        return self.id

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
            await self._client.send_document(
                chat_id=self.from_user.id, document=doc, **kwargs
            )
        return self

    async def edit_message_media(self, *args, **kwargs) -> Self:
        await super().edit_message_media(*args, **kwargs)
        return self

    edit = edit_text = reply = reply_text = edit_message_text
    edit_media = edit_message_media

    @staticmethod
    def sanitize_cq(callback_query):
        """Remove Extra/Custom Attrs from Message Object"""
        kwargs = vars(callback_query).copy()
        kwargs["client"] = kwargs.pop("_client", callback_query._client)

        if callback_query.message:
            kwargs["message"] = Message(kwargs.pop("message"))

        for arg in dir(CallbackQuery):
            is_property = isinstance(
                getattr(CallbackQuery, arg, 0), (cached_property, property)
            )
            is_present_in_super = hasattr(CallbackQueryUpdate, arg)

            if is_property and not is_present_in_super:
                kwargs.pop(arg, 0)

        [kwargs.pop(_property, 0) for _property in CallbackQuery._fake_properties]

        return kwargs
