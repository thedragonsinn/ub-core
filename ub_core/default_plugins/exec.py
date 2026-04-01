import asyncio
import traceback
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO

from pyrogram.enums import ParseMode

# noinspection PyUnresolvedReferences
# ruff: noqa: F401
import ub_core

# noinspection PyUnresolvedReferences
# ruff: noqa: F401
from ub_core import BOT, Cmd, Config, CustomDB, Message, bot, core, default_plugins, ub_core_dir, utils

# noinspection PyUnresolvedReferences
# ruff: noqa: F401
from ub_core.utils import aio, shell


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


async def _exec(bot: BOT, message: Message, code: str):
    function_definitions = {}
    exec(
        "async def __exec(bot: BOT, message: Message):"
        + "\n    r, c, cid , u, uid, ru, ruid = generate_locals(message=message)"
        + "\n    "
        + "\n    ".join(code.splitlines()),
        globals(),
        function_definitions,
    )
    return await function_definitions["__exec"](bot, message)


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
    code: str = message.filtered_input.strip().replace("\u00a0", " ")

    if not code:
        await message.reply("exec Jo mama?")
        return

    reply: Message = await message.reply("executing")

    stdout = StringIO()

    with redirect_stdout(stdout), redirect_stderr(stdout):
        try:
            func_out = await asyncio.create_task(_exec(bot, message, code), name=reply.task_id)
        except asyncio.exceptions.CancelledError:
            await reply.edit("`Cancelled....`")
            return

        except Exception:
            func_out = traceback.format_exc()

    stdout_text = stdout.getvalue().strip()

    if func_out is None and not stdout_text and "-s" in message.flags:
        await reply.delete()
        return

    if func_out is None:
        func_out = ""

    final_output = f"{stdout_text}\n\n{func_out}".strip()
    formatted_input = "" if "-s" in message.flags else f"```python\n{code}```"
    formatted_output = f"```\n{final_output}```" if final_output else ""

    await reply.edit(
        "\n".join((formatted_input, formatted_output)),
        name="exec.txt",
        disable_preview=True,
        parse_mode=ParseMode.MARKDOWN,
    )


if Config.DEV_MODE:
    BOT.add_cmd(cmd="py", allow_sudo=False)(executor)
