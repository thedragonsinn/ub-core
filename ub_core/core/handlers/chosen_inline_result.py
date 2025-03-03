from pyrogram.errors import UserIsBlocked
from pyrogram.handlers import ChosenInlineResultHandler
from pyrogram.types import (
    ChosenInlineResult,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from ..handlers import cmd_dispatcher, create
from ..types import InlineResult
from ... import BOT, bot
from ...config import Config


async def chosen_result_filter(_, __, result: ChosenInlineResult) -> bool:
    return result.result_id in Config.INLINE_RESULT_CACHE


RESULT_FILTER = create(chosen_result_filter)


async def chosen_result_handler(client: BOT, result: ChosenInlineResult):
    Config.INLINE_RESULT_CACHE.remove(result.result_id)

    result = InlineResult.parse(result)

    await result.edit_reply_markup()

    try:
        await client.send_message(
            chat_id=result.from_user.id,
            text=f"Use `.c -i {result.task_id}` to cancel Inline code execution.",
        )
    except UserIsBlocked:
        button = InlineKeyboardButton(
            text=f"Restart Me", url=f"http://t.me/{client.me.username}"
        )
        reply_markup = InlineKeyboardMarkup([[button]])

        await result.edit(
            text=f"You have Blocked @{client.me.username}.", reply_markup=reply_markup
        )
        return

    await cmd_dispatcher(
        client=client,
        update=result,
        is_command=False,
        check_for_reactions=False,
        mode_sensitive=False,
    )

    result.stop_propagation()


if bot.has_bot or bot.is_bot:
    bot.bot.add_handler(
        ChosenInlineResultHandler(
            callback=chosen_result_handler, filters=RESULT_FILTER
        ),
        group=1,
    )
