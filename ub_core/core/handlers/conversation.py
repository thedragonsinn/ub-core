from pyrogram.types import Message as MessageUpdate

from ub_core import BOT, bot

from ..handlers import UnifiedHandler, create, valid_chat_filter
from ...core.conversation import Conversation

CONVO_FILTER = valid_chat_filter & create(
    lambda _, __, message: (message.chat.id in Conversation.CONVO_DICT.keys())
    and (not message.reactions)
)


@bot.on_message(CONVO_FILTER, group=0, is_command=False, filters_edited=True)
async def convo_handler(bot: BOT, message: MessageUpdate):
    """Check for convo filter and update convo future accordingly"""
    conv_objects: list[Conversation] = Conversation.CONVO_DICT[message.chat.id]

    for conv_object in conv_objects:
        if conv_object._client != bot:
            continue
        if conv_object.filters and not (await conv_object.filters(bot, message)):
            continue

        conv_object.responses.append(message)
        conv_object.response_future.set_result(message)

    message.continue_propagation()


if bot.has_bot:
    bot.bot.add_handler(
        UnifiedHandler(callback=convo_handler, filters=CONVO_FILTER), group=0
    )
