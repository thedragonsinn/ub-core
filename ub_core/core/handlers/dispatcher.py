import asyncio
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Callable

from pyrogram import ContinuePropagation, StopPropagation
from pyrogram.types import CallbackQuery as CallbackQueryUpdate
from pyrogram.types import Message as MessageUpdate

from ub_core import BOT, Config

from ..types import CallbackQuery, Message

USER_IS_PROCESSING_MESSAGE: list[int] = []

MESSAGE_TEXT_CACHE: dict[str, str] = defaultdict(str)


def anti_reaction(message: Message):
    """Check if Message.text is same as before or if message is older than 6 hours and stop execution"""
    unique_id = f"{message.chat.id}-{message.id}"

    if MESSAGE_TEXT_CACHE[unique_id] == message.text:
        return True

    time_diff = datetime.now(UTC) - message.date
    if time_diff >= timedelta(hours=6):
        return True

    MESSAGE_TEXT_CACHE[unique_id] = message.text
    return False


async def client_check(client: BOT, message: Message):
    if Config.MODE == "dual":
        if client.is_user:
            USER_IS_PROCESSING_MESSAGE.append(message.id)
        else:
            await asyncio.sleep(0.5)
            if message.id in USER_IS_PROCESSING_MESSAGE:
                message.stop_propagation()


def make_custom_object(
    update: MessageUpdate | CallbackQueryUpdate,
) -> Message | CallbackQuery | None:
    if isinstance(update, MessageUpdate):
        return Message.parse(update)

    if isinstance(update, CallbackQueryUpdate):
        return CallbackQuery.parse(update)


async def cmd_dispatcher(
    client: BOT,
    update: MessageUpdate | CallbackQueryUpdate,
    func: Callable = None,
    check_for_reactions: bool = True,
    mode_sensitive: bool = True,
    is_command: bool = True,
    use_custom_object: bool = True,
) -> None:
    """Custom Command Dispatcher to Gracefully Handle Errors and Cancellation"""

    if mode_sensitive:
        await client_check(client, update)

    if check_for_reactions and anti_reaction(update):
        update.stop_propagation()

    if use_custom_object:
        update = make_custom_object(update)

    if not func:
        cmd_object = Config.CMD_DICT.get(update.cmd)

        if not cmd_object:
            return
        func = cmd_object.func

    task = asyncio.create_task(func(client, update), name=update.task_id)

    try:
        await task
        if is_command and update.is_from_owner:
            await update.delete()

    except asyncio.exceptions.CancelledError:
        await client.log_text(text=f"<b>#Cancelled</b>:\n<code>{update.text}</code>")

    except (StopPropagation, ContinuePropagation):
        raise

    except Exception as e:
        client.log.error(e, exc_info=True, extra={"tg_message": update})

    if not client.is_bot and update.id in USER_IS_PROCESSING_MESSAGE:
        await asyncio.sleep(1)
        USER_IS_PROCESSING_MESSAGE.remove(update.id)

    if is_command:
        update.stop_propagation()
