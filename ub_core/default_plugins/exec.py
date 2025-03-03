import asyncio
import sys
import traceback
from io import StringIO

from pyrogram.enums import ParseMode

# isort: off
# noinspection PyUnresolvedReferences
import ub_core

# noinspection PyUnresolvedReferences
from ub_core import (
    BOT,
    DATABASE,
    DATABASE_CLIENT,
    Cmd,
    Config,
    CustomDB,
    Message,
    bot,
    core,
    default_plugins,
    utils,
)

# noinspection PyUnresolvedReferences
from ub_core.utils import aio, shell

# isort: on


def generate_locals(message: Message) -> tuple:
    cid = uid = ru = ruid = None

    if c := getattr(message, "chat", None):
        cid = message.chat.id

    if u := getattr(message, "from_user", None):
        uid = message.from_user.id

    if r := getattr(message, "replied", None):
        ru = r.from_user

    if ru:
        ruid = message.replied.from_user.id

    return r, c, cid, u, uid, ru, ruid


async def executor(bot: BOT, message: Message) -> None:
    """
    CMD: PY
    INFO: Run Python Code.
    FLAGS: -s to only show output.

    SHORT_ATTRS:
        r: Replied message Object
        c: Chat Object
        cid: chat_id
        u: User Object
        uid: user_id
        ru: Replied User Object
        ruid: Replied user_id

    USAGE:
        .py [-s] return 1
    """
    code: str = message.filtered_input.strip()

    if not code:
        await message.reply("exec Jo mama?")
        return

    reply: Message = await message.reply("executing")

    sys.stdout = codeOut = StringIO()
    sys.stderr = codeErr = StringIO()

    try:
        # Create and initialise the function
        exec(
            "async def _exec(bot: BOT, message: Message):"
            + "\n    r, c, cid , u, uid, ru, ruid = generate_locals(message=message)"
            + "\n    "
            + "\n    ".join(code.splitlines()),
        )
        func_out = await asyncio.create_task(
            locals()["_exec"](bot, message), name=reply.task_id
        )
    except asyncio.exceptions.CancelledError:
        await reply.edit("`Cancelled....`")
        return

    except Exception:
        func_out = str(traceback.format_exc())

    sys.stdout = sys.__stdout__
    sys.stderr = sys.__stderr__

    output = codeErr.getvalue().strip() or codeOut.getvalue().strip()

    if func_out is not None:
        output = f"{output}\n\n{func_out}".strip()

    elif not output and "-s" in message.flags:
        await reply.delete()
        return

    if "-s" in message.flags:
        output = f"|>> ```\n{output}```"
    else:
        output = f"```python\n{code}```\n\n```\n{output}```"

    await reply.edit(
        output,
        name="exec.txt",
        disable_preview=True,
        parse_mode=ParseMode.MARKDOWN,
    )


if Config.DEV_MODE:
    BOT.add_cmd(cmd="py", allow_sudo=False)(executor)
