from pyrogram.errors import UserIsBlocked
from pyrogram.handlers import CallbackQueryHandler
from pyrogram.types import CallbackQuery as CallbackQueryUpdate
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from ub_core import BOT, Config, bot

from ..handlers import cmd_dispatcher, create
from ..types import CallbackQuery


def callback_check(_, __, callback_query: CallbackQueryUpdate):
    if isinstance(callback_query.data, bytes):
        data = callback_query.data.decode("utf-8")
    else:
        data = callback_query.data
    return data in Config.INLINE_QUERY_CACHE.keys()


CALLBACK_FILTER = create(callback_check)


async def callback_handler(client: BOT, callback_query: CallbackQueryUpdate):
    callback_query: CallbackQuery = CallbackQuery(callback_query)

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
        update=callback_query,
        is_command=False,
        check_for_reactions=False,
        mode_sensitive=False,
        use_custom_object=False,
    )
    await callback_query.stop_propagation()


if bot.has_bot or bot.is_bot:
    bot.bot.add_handler(
        CallbackQueryHandler(callback=callback_handler, filters=CALLBACK_FILTER),
        group=1,
    )
