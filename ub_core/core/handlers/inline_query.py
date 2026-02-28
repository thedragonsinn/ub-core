import asyncio
from uuid import uuid4

from pyrogram.handlers import InlineQueryHandler
from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent,
)

from ..handlers import create
from ..handlers.command import check_sudo_access
from ... import bot
from ...config import Config


def inline_check(_, __, inline_query: InlineQuery):
    if not inline_query.query or not inline_query.from_user:
        return False

    user_id = inline_query.from_user.id

    super_user = user_id == Config.OWNER_ID or user_id in Config.SUPERUSERS
    if not super_user and user_id not in Config.SUDO_USERS:
        return False

    query_list: list = inline_query.query.split(maxsplit=1)

    cmd = query_list[0]
    cmd_obj = Config.CMD_DICT.get(cmd)

    if not cmd_obj:
        return False

    if not super_user:
        return check_sudo_access(cmd_obj)

    return True


INLINE_FILTER = create(inline_check)


async def inline_handler(_, inline_query: InlineQuery):
    query_list: list = inline_query.query.split(maxsplit=1)
    cmd = query_list[0]
    text = query_list[1] if len(query_list) >= 2 else ""

    button = InlineKeyboardButton(text=f"run {cmd}", callback_data=inline_query.id)
    reply_markup = InlineKeyboardMarkup([[button]])
    result = InlineQueryResultArticle(
        id=str(uuid4()),
        title=f"run {cmd}",
        input_message_content=InputTextMessageContent(text or "No Input."),
        reply_markup=reply_markup,
    )

    Config.TASK_MANAGER.create_temp_task(
        asyncio.sleep(60),
        name="inline_handler_cache",
        extra_callback=lambda: (
            Config.INLINE_QUERY_CACHE.pop(inline_query.id, 0),
            Config.INLINE_RESULT_CACHE.discard(result.id),
        ),
    )

    Config.INLINE_QUERY_CACHE[inline_query.id] = {
        "cmd": cmd,
        "text": inline_query.query,
    }
    Config.INLINE_RESULT_CACHE.add(result.id)

    await inline_query.answer(results=[result], cache_time=0)


if bot.has_bot or bot.is_bot:
    bot.bot.add_handler(InlineQueryHandler(callback=inline_handler, filters=INLINE_FILTER), group=1)
