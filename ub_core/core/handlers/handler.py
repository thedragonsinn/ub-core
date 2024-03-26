import asyncio
from typing import Callable

from pyrogram import StopPropagation
from pyrogram.handlers import EditedMessageHandler, MessageHandler
from pyrogram.types import Message as Msg

from ub_core import BOT, Config, Convo, Message, bot
from ub_core.core.handlers import filters


async def cmd_dispatcher(bot: BOT, message: Message, func: Callable = None) -> None:
    """Custom Command Dispatcher to Gracefully Handle Errors and Cancellation"""
    if filters.anti_reaction(message):
        message.stop_propagation()

    message = Message.parse(message)

    if not func:
        cmd_object = Config.CMD_DICT.get(message.cmd)

        if not cmd_object:
            return
        func = cmd_object.func

    task = asyncio.create_task(func(bot, message), name=message.task_id)

    try:
        await task
        if message.is_from_owner:
            await message.delete()
    except asyncio.exceptions.CancelledError:
        await bot.log_text(text=f"<b>#Cancelled</b>:\n<code>{message.text}</code>")
    except StopPropagation:
        raise
    except Exception as e:
        bot.log.error(e, exc_info=True, extra={"tg_message": message})
    message.stop_propagation()


# Don't Load Handler is Value is not True
# Useful for Legacy non-db type bots or
# Bots who would like to use custom filters
# for those, Manually add handler on the above function
if Config.LOAD_HANDLERS:
    bot.add_handler(
        MessageHandler(callback=cmd_dispatcher, filters=filters.cmd_filter), group=1
    )
    bot.add_handler(
        EditedMessageHandler(callback=cmd_dispatcher, filters=filters.cmd_filter),
        group=1,
    )


@bot.on_message(filters.convo_filter, group=0)
@bot.on_edited_message(filters.convo_filter, group=0)
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
