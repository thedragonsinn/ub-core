from pyrogram.errors import UserIsBlocked
from pyrogram.handlers import CallbackQueryHandler
from pyrogram.types import CallbackQuery as CQ
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from ub_core import BOT, CallbackQuery, Config, bot
from ub_core.core.handlers import cmd_dispatcher, create


def callback_check(_, __, callback_query):
    if isinstance(callback_query.data, bytes):
        data = callback_query.data.decode("utf-8")
    else:
        data = callback_query.data
    return data in Config.INLINE_QUERY_CACHE.keys()


callback_filter = create(callback_check)


async def callback_handler(client: BOT, callback_query: CQ):
    callback_query = CallbackQuery.parse(callback_query)

    try:
        await client.send_message(
            chat_id=callback_query.from_user.id,
            text=f"Use `.c -i {callback_query.task_id}` to cancel Inline code execution.",
        )
    except UserIsBlocked:
        button = InlineKeyboardButton(
            text=f"Restart Me", url=f"http://t.me/{client.me.username}"
        )
        reply_markup = InlineKeyboardMarkup([[button]])
        await callback_query.edit(
            text=f"You have Blocked @{client.me.username}.", reply_markup=reply_markup
        )
        return

    await cmd_dispatcher(
        client=client,
        message=callback_query,
        is_command=False,
        check_for_reactions=False,
        mode_sensitive=False,
        use_custom_object=False,
    )
    await callback_query.stop_propagation()


if bot.bot and bot.bot.is_bot:
    bot.bot.add_handler(
        CallbackQueryHandler(callback=callback_handler, filters=callback_filter),
        group=1,
    )
