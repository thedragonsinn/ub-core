import os
import shutil

from ub_core import BOT, Message


@BOT.add_cmd(cmd="restart")
async def restart(bot: BOT, message: Message) -> None:
    """
    CMD: RESTART
    INFO: Restart the Bot.
    FLAGS:
        -cl: for clearing logs.
        -cp: for clearing temp plugins.
    Usage:
        .restart | .restart -cl
    """
    await message.reply("Raising `SIGINT` to restart BOT...")

    if "-cl" in message.flags and os.path.isfile("logs/app_logs.txt"):
        os.remove("logs/app_logs.txt")

    if "-cp" in message.flags:
        shutil.rmtree("app/temp", ignore_errors=True)

    bot.raise_sigint()
