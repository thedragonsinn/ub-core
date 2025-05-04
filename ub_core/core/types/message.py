import asyncio
from functools import cached_property
from typing import TYPE_CHECKING, Self

from pyrogram.enums import MessageEntityType
from pyrogram.errors import MessageDeleteForbidden
from pyrogram.filters import Filter
from pyrogram.types import LinkPreviewOptions
from pyrogram.types import Message as MessageUpdate
from pyrogram.types import ReplyParameters, User
from pyrogram.utils import parse_text_entities

from .extra_properties import Properties
from .. import Convo
from ...config import Config

if TYPE_CHECKING:
    from pyrogram.enums import ParseMode
    from pyrogram.types import MessageEntity

    from ..client import DualClient


def del_task_cleaner(del_task):
    Config.BACKGROUND_TASKS.remove(del_task)


async def async_deleter(del_in, task, block) -> MessageUpdate | None:
    """Delete Message w/wo blocking code execution."""
    if block:
        task_result: MessageUpdate = await task
        await asyncio.sleep(del_in)
        await task_result.delete()
        return task_result
    else:
        del_task = asyncio.create_task(async_deleter(del_in=del_in, task=task, block=True))
        Config.BACKGROUND_TASKS.append(del_task)
        del_task.add_done_callback(del_task_cleaner)


class Message(Properties, MessageUpdate):
    """A Custom Message Class with ease of access methods"""

    _client: "DualClient"

    def __init__(self, message: MessageUpdate | Self) -> None:

        super().__init__(**self.sanitize_message(message))

        self._replied = None
        self._reply_to_message: MessageUpdate | None = message.reply_to_message

        if self._reply_to_message:
            self._replied = Message.parse(self._reply_to_message)

        self._raw = message._raw

    @staticmethod
    def sanitize_message(message) -> dict:
        """Remove Extra/Custom Attrs from Message Object"""
        kwargs = vars(message).copy()
        kwargs["client"] = kwargs.pop("_client", message._client)

        # Pop Private Variables
        for attr_name in list(kwargs.keys()):
            if attr_name.startswith("_"):
                kwargs.pop(attr_name)

        # Pop Custom Properties
        for arg in dir(Message):
            is_property = isinstance(getattr(Message, arg, 0), (cached_property, property))
            is_present_in_super = hasattr(MessageUpdate, arg)

            if is_property and not is_present_in_super:
                kwargs.pop(arg, 0)

        return kwargs

    @classmethod
    def parse(cls, update) -> Self:
        return update if isinstance(update, Message) else cls(update)

    async def delete(self, reply: bool = False) -> None:
        """Delete Self and Replied if True"""
        try:
            await super().delete()
            if reply and self.replied:
                await self.replied.delete()
        except MessageDeleteForbidden:
            pass

    async def edit(
        self,
        text,
        del_in: int = 0,
        block=True,
        name: str = "output.txt",
        disable_preview: bool = None,
        parse_mode: "ParseMode" = None,
        entities: list["MessageEntity"] = None,
        **kwargs,
    ) -> "Message":
        """Edit self.text or send a file with text if text length exceeds 4096 chars"""

        if isinstance(disable_preview, bool):
            kwargs["link_preview_options"] = LinkPreviewOptions(is_disabled=disable_preview)

        parse_mode = parse_mode or self._client.parse_mode

        text_and_entities = await parse_text_entities(
            client=self._client,
            text=text,
            parse_mode=parse_mode,
            entities=entities,
        )

        # text, entities = text_and_entities.values()

        if len(text_and_entities["message"]) <= 4096:
            task = super().edit_text(text=text, parse_mode=parse_mode, entities=entities, **kwargs)

            if del_in:
                edited_message = await async_deleter(task=task, del_in=del_in, block=block)
            else:
                edited_message = Message((await task))  # fmt:skip

            if edited_message is not None:
                self.text = edited_message.text

        else:
            _, edited_message = await asyncio.gather(
                super().delete(),
                self.reply(
                    text=text,
                    name=name,
                    block=block,
                    del_in=del_in,
                    disable_preview=disable_preview,
                    parse_mode=parse_mode,
                    entities=entities,
                    **kwargs,
                ),
            )
        return edited_message

    async def extract_user_n_reason(self) -> tuple[User | str | Exception, str | None]:
        if self.replied:
            return self.replied.from_user, self.filtered_input

        input_text_list = self.filtered_input.split(maxsplit=1)

        if not input_text_list:
            return (
                "Unable to Extract User info.\nReply to a user or input @ | id.",
                None,
            )

        user = input_text_list[0]
        reason = None

        if len(input_text_list) >= 2:
            reason = input_text_list[1]
        if self.entities:
            for entity in self.entities:
                if entity == MessageEntityType.MENTION:
                    return entity.user, reason

        if user.isdigit():
            user = int(user)
        elif user.startswith("@"):
            user = user.strip("@")

        try:
            return (await self._client.get_users(user_ids=user)), reason
        except Exception:
            return user, reason

    async def get_response(self, filters: Filter = None, timeout: int = 8, **kwargs):
        """Get a Future Incoming message in chat where message was sent."""
        response: Message | None = await Convo.get_resp(
            client=self._client,
            chat_id=self.chat.id,
            filters=filters,
            timeout=timeout,
            **kwargs,
        )
        return response

    async def log(self):
        """Forward Self to Log Channel"""
        return (await self._client.log_message(self))  # fmt:skip

    async def reply(
        self,
        text,
        del_in: int = 0,
        block: bool = True,
        disable_preview: bool = False,
        reply_parameters: ReplyParameters = None,
        **kwargs,
    ) -> "Message":
        """reply text or send a file with text if text length exceeds 4096 chars"""
        task = self._client.send_message(
            chat_id=self.chat.id,
            text=text,
            disable_preview=disable_preview,
            reply_parameters=reply_parameters or ReplyParameters(message_id=self.id),
            **kwargs,
        )
        if del_in:
            await async_deleter(task=task, del_in=del_in, block=block)
        else:
            return Message((await task))  # fmt:skip
