from pyrogram.types import Message as MessageUpdate

from ub_core import BOT, bot

from ..handlers import create, valid_chat_filter
from ...core.conversation import Conversation

CONVO_FILTER = valid_chat_filter & create(
    lambda _, __, message: (message.chat.id in Conversation.CONVO_DICT.keys())
    and (not message.reactions)
)


@bot.on_message(
    filters=CONVO_FILTER,
    group=0,
    is_command=False,
    filters_edited=True,
    register_on_bot_too=True,
)
async def convo_handler(client: BOT, message: MessageUpdate):
    """Check for convo filter and update convo future accordingly"""
    conv_objects: list[Conversation] = Conversation.CONVO_DICT[message.chat.id]

    for conv_object in conv_objects:
        if conv_object._client != client:
            continue
        if conv_object.filters and not (await conv_object.filters(client, message)):
            continue

        conv_object.responses.append(message)
        conv_object.response_future.set_result(message)

    message.continue_propagation()
