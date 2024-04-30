import asyncio
from typing import Callable

from pyrogram import StopPropagation
from pyrogram.errors import UserIsBlocked
from pyrogram.handlers import (
    CallbackQueryHandler,
    EditedMessageHandler,
    InlineQueryHandler,
    MessageHandler,
)
from pyrogram.types import CallbackQuery as CQ
from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent,
)
from pyrogram.types import Message as Msg

from ub_core import BOT, CallbackQuery, Config, Convo, Message, bot
from ub_core.core.handlers import filters

USER_IS_PROCESSING_MESSAGE: list[int] = []


async def cmd_dispatcher(
    client: BOT,
    message: Message,
    func: Callable = None,
    check_for_reactions: bool = True,
) -> None:
    """Custom Command Dispatcher to Gracefully Handle Errors and Cancellation"""

    if Config.MODE == "dual":
        if client.is_user:
            USER_IS_PROCESSING_MESSAGE.append(message.id)
        else:
            await asyncio.sleep(0.5)
            if message.id in USER_IS_PROCESSING_MESSAGE:
                message.stop_propagation()

    if check_for_reactions and filters.anti_reaction(message):
        message.stop_propagation()

    message = Message.parse(message)

    if not func:
        cmd_object = Config.CMD_DICT.get(message.cmd)

        if not cmd_object:
            return
        func = cmd_object.func

    task = asyncio.create_task(func(client, message), name=message.task_id)

    try:
        await task
        if message.is_from_owner:
            await message.delete()

    except asyncio.exceptions.CancelledError:
        await client.log_text(text=f"<b>#Cancelled</b>:\n<code>{message.text}</code>")

    except StopPropagation:
        raise

    except Exception as e:
        client.log.error(e, exc_info=True, extra={"tg_message": message})

    if not client.is_bot and message.id in USER_IS_PROCESSING_MESSAGE:
        await asyncio.sleep(1)
        USER_IS_PROCESSING_MESSAGE.remove(message.id)

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
    if bot.has_bot:
        bot.bot.add_handler(
            MessageHandler(callback=cmd_dispatcher, filters=filters.cmd_filter), group=1
        )
        bot.bot.add_handler(
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


if bot.has_bot:
    bot.bot.add_handler(
        MessageHandler(callback=convo_handler, filters=filters.convo_filter), group=0
    )
    bot.bot.add_handler(
        EditedMessageHandler(callback=convo_handler, filters=filters.convo_filter),
        group=0,
    )


async def inline_handler(bot: BOT, inline_query: InlineQuery):
    query_list: list = inline_query.query.split(maxsplit=1)
    cmd = query_list[0]
    text = ""
    if len(query_list) >= 2:
        text = query_list[1]
    Config.INLINE_QUERY_CACHE[inline_query.id] = {"cmd": cmd, "text": text}
    reply_markup = InlineKeyboardMarkup(
        [[InlineKeyboardButton(text=f"run {cmd}", callback_data=inline_query.id)]]
    )
    await inline_query.answer(
        results=[
            InlineQueryResultArticle(
                title=f"run {cmd}",
                input_message_content=InputTextMessageContent(text or "No Input."),
                reply_markup=reply_markup,
            )
        ],
        cache_time=10,
    )


if bot.bot and bot.bot.is_bot:
    bot.bot.add_handler(
        InlineQueryHandler(callback=inline_handler, filters=filters.inline_filter),
        group=1,
    )


async def callback_handler(client: BOT, callback_query: CQ):
    callback_query = CallbackQuery.parse(callback_query)

    try:
        await client.send_message(
            chat_id=callback_query.from_user.id,
            text=f"Use `.c -i {callback_query.task_id}` to cancel Inline code execution.",
        )
    except UserIsBlocked:
        reply_markup = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        text=f"Restart Me", url=f"http://t.me/{client.me.username}"
                    )
                ]
            ]
        )
        await callback_query.edit(
            text=f"You have Blocked @{client.me.username}.", reply_markup=reply_markup
        )
        return

    cmd_object = Config.CMD_DICT[callback_query.cmd]
    coro = cmd_object.func(client, callback_query)
    task = asyncio.create_task(coro, name=callback_query.task_id)

    try:
        await task
    except asyncio.exceptions.CancelledError:
        await callback_query.edit("`Cancelled...`")
    except StopPropagation:
        raise
    except Exception as e:
        client.log.error(e, exc_info=True)


if bot.bot and bot.bot.is_bot:
    bot.bot.add_handler(
        CallbackQueryHandler(
            callback=callback_handler, filters=filters.callback_filter
        ),
        group=1,
    )
