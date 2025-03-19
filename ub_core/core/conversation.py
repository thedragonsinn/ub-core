import asyncio
from collections import defaultdict
from typing import TYPE_CHECKING, Self

from pyrogram import filters
from pyrogram.types import Message, ReplyParameters

if TYPE_CHECKING:
    from .client import DualClient


# Relies on ub_core/core/handlers/conversation
class Conversation:
    """A Custom Class to get responses from chats"""

    CONVO_DICT: dict[int, list["Conversation"]] = defaultdict(list)

    class DuplicateConvo(Exception):
        def __init__(self, chat: str | int):
            super().__init__(f"Conversation already started with {chat} ")

    def __init__(
        self,
        client: "DualClient",
        chat_id: int | str,
        check_for_duplicates: bool = True,
        filters: filters.Filter | None = None,
        from_user: int | list[int] = None,
        reply_to_message_id: int = None,
        reply_to_user_id: int = None,
        timeout: int = 10,
    ):
        self.chat_id: int | str = chat_id
        self.client: "DualClient" = client
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
            raise self.DuplicateConvo(self.chat_id)

        Conversation.CONVO_DICT[self.chat_id].append(self)

        await self._create_default_filters()

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

    async def _create_default_filters(self):
        async def extra_filter(_, __, message: Message):
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
                        replied
                        and replied.from_user
                        and replied.from_user.id == self.reply_to_user_id
                    )
                return True
            except AssertionError:
                return False

        ext_filter = filters.create(extra_filter)

        self.filters = self.filters & ext_filter if self.filters else ext_filter

    async def match_filters(self, client: "DualClient", message: "Message") -> bool:
        if client != self.client:
            return False

        return await self.filters(client, message)

    @classmethod
    async def get_resp(cls, client, *args, **kwargs) -> Message | None:
        """
        Bound Method to Gracefully handle Timeout.
        but only returns first Message.
        """
        try:
            async with cls(*args, client=client, **kwargs) as convo:
                response: Message | None = await convo.get_response()
                return response
        except TimeoutError:
            return

    """Methods"""

    async def get_response(self, timeout: int = 0) -> Message | None:
        """Returns Latest Message for Specified Filters."""
        try:
            response: asyncio.Future.result = await asyncio.wait_for(
                fut=self.response_future, timeout=timeout or self.timeout
            )
            return response
        except asyncio.TimeoutError:
            raise TimeoutError(f"Conversation Timeout [{self.timeout}s] with chat: {self.chat_id}")

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
            return message, response
        return message

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
            return message, response
        return message

    async def send_photo(
        self,
        photo,
        caption: str = "",
        timeout: int = 0,
        get_response: bool = False,
        reply_parameters: ReplyParameters = None,
        **kwargs,
    ) -> Message | tuple[Message, Message]:

        if reply_to_id := kwargs.get("reply_to_id"):
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
            return message, response
        return message
