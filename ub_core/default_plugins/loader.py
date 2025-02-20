import importlib
import os
import sys
import traceback

from ub_core import BOT, Config, Message


async def loader(bot: BOT, message: Message) -> Message | None:
    """
    CMD: LOAD
    INFO: Load a Bot Plugin.
    FLAGS: -r to reload a cmd.
    USAGE:
        .load [reply to plugin]
        .load -r ping
    """
    reply: Message = await message.reply("Loading....")

    try:
        assert "-r" in message.flags or message.replied.document.file_name.endswith(
            ".py"
        )
    except (AssertionError, AttributeError):
        await reply.edit("Reply to a Plugin.")
        return

    if "-r" in message.flags:
        plugin = message.filtered_input
        cmd_module = Config.CMD_DICT.get(plugin)

        if not cmd_module:
            await reply.edit(text="Invalid cmd.")
            return

        module = str(cmd_module.func.__module__)  # NOQA
    else:
        file_name: str = os.path.splitext(message.replied.document.file_name)[0]
        module = f"app.temp.{file_name}"
        await message.replied.download("app/temp/")

    reload = sys.modules.pop(module, None)
    status: str = "Reloaded" if reload else "Loaded"
    try:
        importlib.import_module(module)
    except Exception:
        await reply.edit(str(traceback.format_exc()))
        return
    await reply.edit(f"{status} {module}")


if Config.DEV_MODE:
    BOT.add_cmd(cmd="load", allow_sudo=False)(loader)
