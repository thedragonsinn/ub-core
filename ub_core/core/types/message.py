import asyncio
from functools import cached_property
from typing import TYPE_CHECKING, Self

from pyrogram.enums import MessageEntityType
from pyrogram.errors import MessageDeleteForbidden
from pyrogram.filters import Filter
from pyrogram.types import Message as MessageUpdate
from pyrogram.types import User

from .. import Convo
from ...config import Config

if TYPE_CHECKING:
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
        del_task = asyncio.create_task(
            async_deleter(del_in=del_in, task=task, block=True)
        )
        Config.BACKGROUND_TASKS.append(del_task)
        del_task.add_done_callback(del_task_cleaner)


class Message(MessageUpdate):
    """A Custom Message Class with ease of access methods"""

    _client: "DualClient"

    def __init__(self, message: MessageUpdate | Self) -> None:
        kwargs = self.sanitize_message(message)
        super().__init__(**kwargs)

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
        Returns list of text that start with - i.e flags. \n
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
    def replied(self) -> "Message":
        """Returns Custom Message object for message.reply_to_message"""
        if self.reply_to_message:
            return Message.parse(self.reply_to_message)

    @cached_property
    def reply_id(self) -> int | None:
        """Returns message.reply_to_message.id if message.reply_to_message"""
        return self.replied.id if self.replied else None

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
    def trigger(self) -> str:
        """Returns Cmd or Sudo Trigger"""
        # Legacy w/o db and sudo support
        if hasattr(Config, "TRIGGER"):
            return Config.TRIGGER

        return (
            Config.CMD_TRIGGER
            if self.is_from_owner and not self._client.is_bot
            else Config.SUDO_TRIGGER
        )

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
        self, text, del_in: int = 0, block=True, name: str = "output.txt", **kwargs
    ) -> "Message":
        """Edit Self.text or send a file with text if text length exceeds 4096 chars"""
        if len(str(text)) < 4096:
            task = super().edit_text(text=text, **kwargs)
            if del_in:
                reply = await async_deleter(task=task, del_in=del_in, block=block)
            else:
                reply = Message.parse((await task))  # fmt:skip
            self.text = reply.text
        else:
            _, reply = await asyncio.gather(
                super().delete(), self.reply(text, name=name, **kwargs)
            )
        return reply

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

    async def get_response(self, filters: Filter = None, timeout: int = 8):
        """Get a Future Incoming message in chat where message was sent."""
        response: Message | None = await Convo.get_resp(
            client=self._client, chat_id=self.chat.id, filters=filters, timeout=timeout
        )
        return response

    async def log(self):
        """Forward Self to Log Channel"""
        return (await self.copy(Config.LOG_CHAT))  # fmt:skip

    async def reply(
        self, text, del_in: int = 0, block: bool = True, **kwargs
    ) -> "Message":
        """reply text or send a file with text if text length exceeds 4096 chars"""
        task = self._client.send_message(
            chat_id=self.chat.id, text=text, reply_to_message_id=self.id, **kwargs
        )
        if del_in:
            await async_deleter(task=task, del_in=del_in, block=block)
        else:
            return Message.parse((await task))  # fmt:skip

    @staticmethod
    def sanitize_message(message):
        """Remove Extra/Custom Attrs from Message Object"""
        kwargs = vars(message).copy()
        kwargs["client"] = kwargs.pop("_client", message._client)
        for arg in dir(Message):
            if isinstance(
                getattr(Message, arg, 0), (cached_property, property)
            ) and not hasattr(MessageUpdate, arg):
                kwargs.pop(arg, 0)
        return kwargs

    @classmethod
    def parse(cls, message: MessageUpdate) -> "Message":
        return cls(message)
