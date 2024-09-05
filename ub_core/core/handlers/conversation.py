from pyrogram.types import Message as Msg

from ub_core import BOT, Convo, bot
from ub_core.core.conversation import Conversation
from ub_core.core.handlers import create

# Conversation Filter to check for incoming messages.

CONVO_FILTER = create(
    lambda _, __, message: (message.chat.id in Conversation.CONVO_DICT.keys())
    and (not message.reactions)
)


@bot.on_message(CONVO_FILTER, group=0)
@bot.on_edited_message(CONVO_FILTER, group=0)
async def convo_handler(bot: BOT, message: Msg):
    """Check for convo filter and update convo future accordingly"""
    conv_objects: list[Convo] = Convo.CONVO_DICT[message.chat.id]

    for conv_object in conv_objects:
        if conv_object._client != bot:
            continue
        if conv_object.filters and not (await conv_object.filters(bot, message)):
            continue

        conv_object.responses.append(message)
        conv_object.response_future.set_result(message)

    message.continue_propagation()
