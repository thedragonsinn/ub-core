from functools import cached_property
from typing import Self

from pyrogram.types import CallbackQuery as CQ

from ub_core import Config
from ub_core.core.types.message import Message


def construct_properties(inline_query_id: str) -> tuple[str, list, str, str]:
    cmd, text = (Config.INLINE_QUERY_CACHE.pop(inline_query_id)).values()
    flags = [i for i in text.split() if i.startswith("-")]
    input = text
    split_lines = input.split(sep="\n", maxsplit=1)
    split_lines[0] = " ".join(
        [word for word in split_lines[0].split(" ") if word not in flags]
    )
    filtered_input = "\n".join(split_lines)
    return cmd, flags, input, filtered_input


class CallbackQuery(CQ):
    """A Custom CallbackQuery Class with ease of access methods"""

    def __init__(self, callback_query: CQ | Self) -> None:
        kwargs = self.sanitize_cq(callback_query)
        super().__init__(**kwargs)
        if isinstance(self.data, bytes):
            self.data = self.data.decode("utf-8")
        self.cmd, self.flags, self.input, self.filtered_input = construct_properties(
            self.data
        )
        self.replied = self.reply_id = self.replied_task_id = None

    @cached_property
    def message(self):
        if super().message:
            return Message.parse(super().message)

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
        text: str,
        parse_mode=None,
        disable_web_page_preview: bool = False,
        reply_markup=None,
        name: str = "output.txt",
        del_in: int = 0,
        block=True,
        **kwargs,
    ):
        if not isinstance(text, str):
            text = str(text)
        if len(text) < 4096:
            await super().edit_message_text(
                text, parse_mode, disable_web_page_preview, reply_markup
            )
        else:
            doc = BytesIO(bytes(text, encoding="utf-8"))
            doc.name = name
            await super().send_document(
                chat_id=self.from_user.id, document=doc, **kwargs
            )
        return self

    edit = reply = edit_message_text

    @staticmethod
    def sanitize_cq(callback_query):
        """Remove Extra/Custom Attrs from Message Object"""
        kwargs = vars(callback_query).copy()
        kwargs["client"] = kwargs.pop("_client", callback_query._client)
        for arg in dir(CallbackQuery):
            if isinstance(
                getattr(CallbackQuery, arg, 0), (cached_property, property)
            ) and not hasattr(CQ, arg):
                kwargs.pop(arg, 0)
        return kwargs

    @classmethod
    def parse(cls, callback_query: CQ) -> "CallbackQuery":
        return cls(callback_query)