import asyncio
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Callable

from pyrogram import ContinuePropagation, StopPropagation
from pyrogram.types import Message

from ub_core import BOT, Config, Message

MESSAGE_TEXT_CACHE = defaultdict(str)


def anti_reaction(message: Message):
    """Check if Message.text is same as before or if message is older than 6 hours and stop execution"""
    unique_id = f"{message.chat.id}-{message.id}"

    if MESSAGE_TEXT_CACHE[unique_id] == message.text:
        return True

    time_diff = datetime.utcnow() - message.date
    if time_diff >= timedelta(hours=6):
        return True

    MESSAGE_TEXT_CACHE[unique_id] = message.text
    return False


async def cmd_dispatcher(
    client: BOT,
    message: Message,
    func: Callable = None,
    check_for_reactions: bool = True,
    mode_sensitive: bool = False,
    is_command: bool = True,
) -> None:
    """Custom Command Dispatcher to Gracefully Handle Errors and Cancellation"""
    if check_for_reactions and anti_reaction(message):
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
        if is_command and message.is_from_owner:
            await message.delete()

    except asyncio.exceptions.CancelledError:
        await client.log_text(text=f"<b>#Cancelled</b>:\n<code>{message.text}</code>")

    except (StopPropagation, ContinuePropagation):
        raise

    except Exception as e:
        client.log.error(e, exc_info=True, extra={"tg_message": message})

    if is_command:
        message.stop_propagation()
