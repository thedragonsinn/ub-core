import asyncio
from functools import cached_property
from typing import TYPE_CHECKING, Self

from pyrogram.enums import MessageEntityType, MessageServiceType
from pyrogram.errors import MessageDeleteForbidden
from pyrogram.filters import Filter
from pyrogram.types import LinkPreviewOptions
from pyrogram.types import Message as MessageUpdate
from pyrogram.types import ReplyParameters, User
from pyrogram.utils import parse_text_entities

from .. import Convo
from ...config import Config

if TYPE_CHECKING:
    from pyrogram.enums import ParseMode
    from pyrogram.types import MessageEntity

    from ..client import BOT


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


class Message(MessageUpdate):
    """A Custom Message Class with ease of access methods"""

    _client: "BOT"

    def __init__(self, message: MessageUpdate | Self) -> None:
        message_vars = vars(message).copy()
        message_vars["client"] = message_vars.pop("_client", message._client)

        super().__init__(**self.sanitize_message(message_vars))

        self._replied = None
        self._reply_to_message: MessageUpdate | None = message.reply_to_message

        if self._reply_to_message:
            self._replied = Message(self._reply_to_message)

        self._raw = message._raw

    @cached_property
    def cmd(self) -> str | None:
        """Returns First Word of text if it's a valid command."""
        if not self.text_list:
            return

        raw_cmd = self.text_list[0]
        cmd = raw_cmd.replace(self.trigger, "", 1)

        return cmd if cmd in Config.CMD_DICT.keys() else None

    @cached_property
    def flags(self) -> list:
        """
        Returns list of text that start with - i.e. flags. \n
        text: .example -d -s something \n
        returns: [-d, -s]
        """
        return [i for i in self.text_list if i.startswith("-")]

    @cached_property
    def filtered_input(self) -> str:
        """
        Returns all text except command and flags. \n
        text: .example -d -s do something here \n
        returns: do something here
        """
        split_lines = self.input.split(sep="\n", maxsplit=1)
        split_lines[0] = " ".join(
            [word for word in split_lines[0].split(" ") if word not in self.flags]
        )
        return "\n".join(split_lines)

    @cached_property
    def input(self) -> str:
        """
        Returns raw text except command. \n
        text: .example -d -s do something here \n
        returns: -d -s do something here
        """
        if len(self.text_list) > 1:
            return self.text.split(maxsplit=1)[-1]
        return ""

    @cached_property
    def is_from_owner(self) -> bool:
        """Returns True if message is from Owner of bot."""
        return self.from_user and self.from_user.id == Config.OWNER_ID

    @cached_property
    def replied(self) -> Self | None:
        """
        Returns Custom Message object for message.reply_to_message
        If replied isn't the Thread Origin Message.
        """
        if self._replied and not self._replied.is_thread_origin:
            return self._replied

    @property
    def reply_to_message(self) -> MessageUpdate | None:
        """
        Returns Pyrogram's Message object if replied isn't a Thread Origin Message.
        """
        if self._replied and not self._replied.is_thread_origin:
            return self._reply_to_message

    @reply_to_message.setter
    def reply_to_message(self, value) -> None:
        pass

    @cached_property
    def reply_id(self) -> int | None:
        """Returns message.reply_to_message.id if message.reply_to_message"""
        return self.reply_to_message_id

    @cached_property
    def replied_task_id(self) -> str | None:
        """Returns message.reply_to_message.task_id if message.reply_to_message"""
        return self.replied.task_id if self.replied else None

    @cached_property
    def reply_text_list(self) -> list:
        """Returns list of message.reply_to_message.text.split()"""
        return self.replied.text_list if self.replied else []

    @cached_property
    def task_id(self) -> str:
        """Task ID to Cancel/Track Command Progress."""
        return f"{self.chat.id}-{self.id}"

    @cached_property
    def text_list(self) -> list:
        """Returns list of message.text.split()"""
        return self.text.split() if self.text else []

    @cached_property
    def is_thread_origin(self) -> bool:
        return self.service == MessageServiceType.FORUM_TOPIC_CREATED

    @cached_property
    def thread_origin_message(self) -> Self | None:
        """
        Returns Custom Message object for message.reply_to_message
        If replied is the Thread Origin Message.
        """
        if self._replied and self._replied.is_thread_origin:
            return self._replied

    @cached_property
    def trigger(self) -> str:
        """Returns Cmd or Sudo Trigger"""
        # Legacy w/o db and sudo support
        if hasattr(Config, "TRIGGER"):
            return Config.TRIGGER

        if self.is_from_owner:
            return Config.CMD_TRIGGER
        else:
            return Config.SUDO_TRIGGER

    @cached_property
    def unique_chat_user_id(self) -> int | str:
        return f"{self.chat.id}-{self.from_user.id}" if self.from_user else 0

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
            client=self._client, text=text, parse_mode=parse_mode, entities=entities
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
            return ("Unable to Extract User info.\nReply to a user or input @ | id.", None)

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
            client=self._client, chat_id=self.chat.id, filters=filters, timeout=timeout, **kwargs
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

    @staticmethod
    def sanitize_message(kwargs):
        """Remove Extra/Custom Attrs from Message Object"""

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
