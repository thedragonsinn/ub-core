from functools import cached_property
from typing import TYPE_CHECKING

from pyrogram.enums import MessageServiceType
from pyrogram.types import Message as MessageUpdate

from ...config import Config

if TYPE_CHECKING:

    from . import CallbackQuery, InlineResult, Message

    type Supers = Message | CallbackQuery | InlineResult

    ...


class Properties:
    @cached_property
    def cmd(self: "Supers") -> str | None:
        """Returns First Word of text if it's a valid command."""
        if not self.text_list:
            return

        raw_cmd = self.text_list[0]
        cmd = raw_cmd.replace(self.trigger, "", 1)

        return cmd if cmd in Config.CMD_DICT.keys() else None

    @cached_property
    def flags(self: "Supers") -> list:
        """
        Returns list of text that start with - i.e. flags. \n
        text: .example -d -s something \n
        returns: [-d, -s]
        """
        return [i for i in self.text_list if i.startswith("-")]

    @cached_property
    def filtered_input(self: "Supers") -> str:
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
    def input(self: "Supers") -> str:
        """
        Returns raw text except command. \n
        text: .example -d -s do something here \n
        returns: -d -s do something here
        """
        if len(self.text_list) > 1:
            return self.text.split(maxsplit=1)[-1]
        return ""

    @cached_property
    def is_from_owner(self: "Supers") -> bool:
        """Returns True if message is from Owner of bot."""
        return self.from_user and self.from_user.id == Config.OWNER_ID

    @cached_property
    def replied(self: "Supers") -> "Message":
        """
        Returns Custom Message object for message.reply_to_message
        If replied isn't the Thread Origin Message.
        """
        if self._replied and not self._replied.is_thread_origin:
            return self._replied

    @property
    def reply_to_message(self: "Supers") -> MessageUpdate | None:
        """
        Returns Pyrogram's Message object if replied isn't a Thread Origin Message.
        """
        if self._replied and not self._replied.is_thread_origin:
            return self._reply_to_message

    @reply_to_message.setter
    def reply_to_message(self, value) -> None:
        pass

    @cached_property
    def reply_id(self: "Supers") -> int | None:
        """Returns message.reply_to_message.id if message.reply_to_message"""
        return self.reply_to_message_id

    @cached_property
    def replied_task_id(self: "Supers") -> str | None:
        """Returns message.reply_to_message.task_id if message.reply_to_message"""
        return self.replied.task_id if self.replied else None

    @cached_property
    def reply_text_list(self: "Supers") -> list:
        """Returns list of message.reply_to_message.text.split()"""
        return self.replied.text_list if self.replied else []

    @cached_property
    def task_id(self: "Supers") -> str:
        """Task ID to Cancel/Track Command Progress."""
        chat_id = self.chat.id if hasattr(self, "chat") else ""
        return f"{chat_id}-{self.id}"

    @cached_property
    def text_list(self: "Supers") -> list:
        """Returns list of message.text.split()"""
        return self.text.split() if self.text else []

    @cached_property
    def is_thread_origin(self: "Supers") -> bool:
        return self.service == MessageServiceType.FORUM_TOPIC_CREATED

    @cached_property
    def thread_origin_message(self: "Supers") -> "Message":
        """
        Returns Custom Message object for message.reply_to_message
        If replied is the Thread Origin Message.
        """
        if self._replied and self._replied.is_thread_origin:
            return self._replied

    @cached_property
    def trigger(self: "Supers") -> str:
        """Returns Cmd or Sudo Trigger"""
        # Legacy w/o db and sudo support
        if hasattr(Config, "TRIGGER"):
            return Config.TRIGGER

        if self.is_from_owner and not self._client.is_bot:
            return Config.CMD_TRIGGER
        else:
            return Config.SUDO_TRIGGER

    @cached_property
    def unique_chat_user_id(self: "Supers") -> int | str:
        chat_id = self.chat.id if hasattr(self, "chat") else ""
        return f"{chat_id}-{self.from_user.id}" if self.from_user else 0
