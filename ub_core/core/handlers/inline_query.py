from pyrogram.handlers import InlineQueryHandler
from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent,
)

from ub_core import BOT, Config, bot
from ub_core.core.handlers import create
from ub_core.core.handlers.command import check_sudo_access


def inline_check(_, __, inline_query: InlineQuery):

    if not inline_query.query or not inline_query.from_user:
        return False

    user_id = inline_query.from_user.id
    supers = [Config.OWNER_ID, *Config.SUPERUSERS]

    if user_id not in Config.SUDO_USERS + supers:
        return False

    super = user_id in supers

    query_list: list = inline_query.query.split(maxsplit=1)

    cmd = query_list[0]
    cmd_obj = Config.CMD_DICT.get(cmd)

    if not cmd_obj:
        return False

    if not super:
        return check_sudo_access(cmd_obj)

    return True


INLINE_FILTER = create(inline_check)


async def inline_handler(bot: BOT, inline_query: InlineQuery):
    query_list: list = inline_query.query.split(maxsplit=1)
    cmd = query_list[0]
    text = ""

    if len(query_list) >= 2:
        text = query_list[1]

    Config.INLINE_QUERY_CACHE[inline_query.id] = {"cmd": cmd, "text": text}

    button = InlineKeyboardButton(text=f"run {cmd}", callback_data=inline_query.id)
    reply_markup = InlineKeyboardMarkup([[button]])
    result = InlineQueryResultArticle(
        title=f"run {cmd}",
        input_message_content=InputTextMessageContent(text or "No Input."),
        reply_markup=reply_markup,
    )

    await inline_query.answer(results=[result], cache_time=10)


if bot.bot and bot.bot.is_bot:
    bot.bot.add_handler(
        InlineQueryHandler(callback=inline_handler, filters=INLINE_FILTER), group=1
    )
