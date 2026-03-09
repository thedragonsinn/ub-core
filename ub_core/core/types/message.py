import asyncio
from typing import TYPE_CHECKING, Self

from pyrogram import enums, errors, filters, types, utils

from .extra_properties import Properties
from ...config import Config

if TYPE_CHECKING:
    from pyrogram.enums import ParseMode
    from pyrogram.types import MessageEntity

    from ..client import BOT


async def async_deleter(del_in, coro, block) -> types.Message | None:
    """Delete Message w/wo blocking code execution."""
    if block:
        task_result: types.Message = await coro
        await asyncio.sleep(del_in)
        await task_result.delete()
        return task_result
    else:
        Config.TASK_MANAGER.create_temp_task(async_deleter(del_in=del_in, coro=coro, block=True), name=str(coro))


class Message(Properties, types.Message):
    """A Custom Message Class with ease of access methods"""

    _client: "BOT"

    def __init__(self, message: types.Message | Self) -> None:
        super().__init__(**self.sanitize_update(message, _Super=types.Message, _SubClass=Message))

        self._replied = None
        self._reply_to_message: types.Message | None = message.reply_to_message

        if self._reply_to_message:
            self._replied = Message.parse(self._reply_to_message)

    @classmethod
    def parse(cls, update) -> Self:
        return update if isinstance(update, Message) else cls(update)

    async def delete(self, reply: bool = False, revoke: bool = True) -> None:
        """Delete Self and Replied if True"""
        has_del_perm = self.chat.admin_privileges and self.chat.admin_privileges.can_delete_messages
        outgoing = self.outgoing
        is_regular_group = self.chat.type == enums.ChatType.GROUP

        if any((has_del_perm, outgoing, is_regular_group and self._client.is_user)):
            try:
                await super().delete(revoke=revoke)
            except errors.MessageDeleteForbidden:
                pass

        if reply and self.replied:
            await self.replied.delete(revoke=revoke)

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
            kwargs["link_preview_options"] = types.LinkPreviewOptions(is_disabled=disable_preview)

        parse_mode = parse_mode or self._client.parse_mode

        text_and_entities = await utils.parse_text_entities(
            client=self._client, text=text, parse_mode=parse_mode, entities=entities
        )

        # text, entities = text_and_entities.values()

        if len(text_and_entities["message"]) <= 4096:
            task = super().edit_text(text=text, parse_mode=parse_mode, entities=entities, **kwargs)

            if del_in:
                edited_message = await async_deleter(coro=task, del_in=del_in, block=block)
            else:
                edited_message = Message(await task)  # fmt:skip

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

    async def extract_user_n_reason(
        self,
    ) -> tuple[types.User | str | Exception, str | None]:
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
                if entity == enums.MessageEntityType.TEXT_MENTION:
                    return entity.user, reason

        if user.isdigit():
            user = int(user)
        elif user.startswith("@"):
            user = user.strip("@")

        try:
            return await self._client.get_users(user_ids=user), reason
        except Exception:
            return user, reason

    async def get_response(self, filters: "filters.Filter" = None, timeout: int = 8, **kwargs):
        """Get a Future Incoming message in chat where message was sent."""
        response: Message | None = await self._client.Convo.get_resp(
            client=self._client,
            chat_id=self.chat.id,
            filters=filters,
            timeout=timeout,
            **kwargs,
        )
        return response

    async def log(self) -> Self:
        """Forward Self to Log Channel"""
        return Message(await self._client.log_message(self))

    async def reply(
        self,
        text,
        del_in: int = 0,
        block: bool = True,
        disable_preview: bool = False,
        reply_parameters: types.ReplyParameters = None,
        **kwargs,
    ) -> "Message":
        """reply text or send a file with text if text length exceeds 4096 chars"""
        coro = self._client.send_message(
            chat_id=self.chat.id,
            text=text,
            disable_preview=disable_preview,
            reply_parameters=reply_parameters or types.ReplyParameters(message_id=self.id),
            **kwargs,
        )
        if del_in:
            await async_deleter(coro=coro, del_in=del_in, block=block)

        else:
            return Message(await coro)
