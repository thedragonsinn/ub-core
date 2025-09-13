import asyncio
from collections import defaultdict
from typing import TYPE_CHECKING, Self

from pyrogram import filters
from pyrogram.types import ReplyParameters

from .types import Message

if TYPE_CHECKING:
    from .client import BOT


# Relies on ub_core/core/handlers/conversation
class Conversation:
    """A Custom Class to get responses from chats"""

    CONVO_DICT: dict[int, list["Conversation"]] = defaultdict(list)

    class DuplicateConvoError(Exception):
        def __init__(self, chat: str | int):
            super().__init__(f"Conversation already started with {chat} ")

    def __init__(
        self,
        client: "BOT",
        chat_id: int | str,
        check_for_duplicates: bool = True,
        filters: filters.Filter | None = None,
        from_user: int | list[int] = None,
        reply_to_message_id: int = None,
        reply_to_user_id: int = None,
        timeout: int = 10,
    ):
        self.chat_id: int | str = chat_id
        self.client: BOT = client
        self.check_for_duplicates: bool = check_for_duplicates

        self.filters: filters.Filter = filters
        self.from_user: int = from_user
        self.reply_to_message_id: int = reply_to_message_id
        self.reply_to_user_id = reply_to_user_id

        self.response_future: asyncio.Future | None = None
        self.responses: list[Message] = []
        self.timeout: int = timeout
        self.set_future()

    async def __aenter__(self) -> Self:
        """
        Convert Username to ID if chat_id is username.
        Check Convo Dict for duplicate Convo with same ID.
        Initialize Context Manager and return the Object.
        """
        if isinstance(self.chat_id, str):
            self.chat_id = (await self.client.get_chat(self.chat_id)).id

        if self.check_for_duplicates and self.chat_id in Conversation.CONVO_DICT.keys():
            raise self.DuplicateConvoError(self.chat_id)

        Conversation.CONVO_DICT[self.chat_id].append(self)

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit Context Manager and remove Chat ID from Dict."""
        if self in Conversation.CONVO_DICT[self.chat_id]:
            Conversation.CONVO_DICT[self.chat_id].remove(self)

        if not self.response_future.done():
            self.response_future.cancel()

        if not Conversation.CONVO_DICT[self.chat_id]:
            Conversation.CONVO_DICT.pop(self.chat_id)

    def set_future(self, *_, **__):
        future = asyncio.Future()
        future.add_done_callback(self.set_future)
        self.response_future = future

    @staticmethod
    async def extra_filter(self: "Self", client: "BOT", message: Message):
        try:
            if self.from_user:
                assert message.from_user
                if isinstance(self.from_user, list):
                    assert message.from_user.id in self.from_user
                else:
                    assert message.from_user.id == self.from_user

            if self.reply_to_message_id:
                assert message.reply_to_message_id == self.reply_to_message_id

            if self.reply_to_user_id:
                replied = message.reply_to_message
                assert (
                    replied and replied.from_user and replied.from_user.id == self.reply_to_user_id
                )
            return True
        except AssertionError:
            return False

    async def match_filters(self, client: "BOT", message: "Message") -> bool:
        if client != self.client:
            return False

        conv_filters_result = await self.filters(client, message) if self.filters else True
        extra_filters_result = await self.extra_filter(self, client, message)

        return conv_filters_result and extra_filters_result

    @classmethod
    async def get_resp(
        cls, client, *args, quote: bool = False, lower: bool = False, **kwargs
    ) -> Message | tuple[str, None | Message] | None:
        """
        Bound Method to Gracefully handle Timeout.
        but only returns first Message.
        """
        try:
            async with cls(*args, client=client, **kwargs) as convo:
                if quote:
                    response: tuple[str, Message] = await convo.get_quote_or_text(lower=lower)
                else:
                    response: Message | None = await convo.get_response()
                return response
        except TimeoutError:
            return ("", None) if quote else None

    """Methods"""

    async def get_response(self, timeout: int = 0) -> Message | None:
        """Returns Latest Message for Specified Filters."""
        try:
            response: Message = await asyncio.wait_for(
                fut=self.response_future, timeout=timeout or self.timeout
            )
            return response
        except TimeoutError as err:
            raise TimeoutError(
                f"Conversation Timeout [{self.timeout}s] with chat: {self.chat_id}"
            ) from err

    async def get_quote_or_text(self, timeout: int = 0, lower: bool = False) -> tuple[str, Message]:
        response: Message = await self.get_response(timeout=timeout)
        if response.quote is not None and response.quote.text:
            value = response.quote.text
        else:
            value = response.content
        value = value.lower() if lower else value
        return value, response

    async def send_message(
        self, text: str, timeout: int = 0, get_response: bool = False, **kwargs
    ) -> Message | tuple[Message, Message]:
        """
        Bound Method to Send Texts in Convo Chat.
        Returns Sent Message and Response if get_response is True.
        """
        message = await self.client.send_message(chat_id=self.chat_id, text=text, **kwargs)
        if get_response:
            response = await self.get_response(timeout=timeout)
            return Message.parse(message), Message.parse(response)
        return Message.parse(message)

    async def send_document(
        self,
        document,
        caption: str = "",
        timeout: int = 0,
        get_response: bool = False,
        disable_content_type_detection: bool = True,
        **kwargs,
    ) -> Message | tuple[Message, Message]:
        """
        Bound Method to Send Documents in Convo Chat.
        Returns Sent Message and Response if get_response is True.
        """
        message = await self.client.send_document(
            chat_id=self.chat_id,
            document=document,
            caption=caption,
            disable_content_type_detection=disable_content_type_detection,
            **kwargs,
        )
        if get_response:
            response = await self.get_response(timeout=timeout)
            return Message.parse(message), Message.parse(response)
        return Message.parse(message)

    async def send_photo(
        self,
        photo,
        caption: str = "",
        timeout: int = 0,
        get_response: bool = False,
        reply_parameters: ReplyParameters = None,
        **kwargs,
    ) -> Message | tuple[Message, Message]:
        if reply_to_id := kwargs.pop("reply_to_id", None):
            reply_parameters = ReplyParameters(message_id=reply_to_id)

        message = await self.client.send_photo(
            chat_id=self.chat_id,
            photo=photo,
            caption=caption,
            reply_parameters=reply_parameters,
            **kwargs,
        )

        if get_response:
            response = await self.get_response(timeout=timeout)
            return Message.parse(message), Message.parse(response)
        return Message.parse(message)

    async def send_voice(
        self,
        voice,
        caption: str = "",
        timeout: int = 0,
        get_response: bool = False,
        reply_parameters: ReplyParameters = None,
        **kwargs,
    ):
        if reply_to_id := kwargs.pop("reply_to_id", None):
            reply_parameters = ReplyParameters(message_id=reply_to_id)

        message = await self.client.send_voice(
            chat_id=self.chat_id,
            voice=voice,
            caption=caption,
            reply_parameters=reply_parameters,
            **kwargs,
        )

        if get_response:
            response = await self.get_response(timeout=timeout)
            return Message.parse(message), Message.parse(response)
        return Message.parse(message)
