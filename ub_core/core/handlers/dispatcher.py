import asyncio
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Callable

from pyrogram import ContinuePropagation, StopPropagation
from pyrogram.types import Message as MessageUpdate

from ..types import Message
from ... import BOT
from ...config import Config

MESSAGE_TEXT_CACHE = defaultdict(str)


def anti_reaction(message: MessageUpdate):
    """Check if Message.text is same as before or if message is older than 6 hours and stop execution"""
    unique_id = f"{message.chat.id}-{message.id}"

    if MESSAGE_TEXT_CACHE[unique_id] == message.text:
        return True

    time_diff =  datetime.now(UTC) - message.date
    if time_diff >= timedelta(hours=6):
        return True

    MESSAGE_TEXT_CACHE[unique_id] = message.text
    return False


async def cmd_dispatcher(
    client: BOT,
    update: MessageUpdate,
    func: Callable = None,
    check_for_reactions: bool = True,
    mode_sensitive: bool = True,
    is_command: bool = True,
    use_custom_object: bool = True,
) -> None:
    """Custom Command Dispatcher to Gracefully Handle Errors and Cancellation"""
    if check_for_reactions and anti_reaction(update):
        update.stop_propagation()

    if use_custom_object:
        update = Message.parse(update)

    if not func:
        cmd_object = Config.CMD_DICT.get(update.cmd)

        if not cmd_object:
            return
        func = cmd_object.func

    try:
        task = asyncio.create_task(func(client, update), name=update.task_id)
        await task
        if is_command and update.is_from_owner:
            await update.delete()

    except asyncio.exceptions.CancelledError:
        await client.log_text(text=f"<b>#Cancelled</b>:\n<code>{update.text}</code>")

    except (StopPropagation, ContinuePropagation):
        raise

    except Exception as e:
        client.log.error(e, exc_info=True, extra={"tg_message": update})

    if is_command:
        update.stop_propagation()
