import aiofiles

from ub_core import BOT, Message
from ub_core.utils import run_shell_cmd


@BOT.add_cmd(cmd="logs")
async def read_logs(bot: BOT, message: Message):
    """
    CMD: Logs
    INFO: Check bot logs
    FLAGS:
        -tail: get last few lines from file
    USAGE:
        .logs
        .logs -tail 10
    """

    if "-tail" in message.flags:
        text = await run_shell_cmd(cmd=f"tail -n {int(message.filtered_input)} logs/app_logs.txt")
        await message.reply(f"<pre language=java>{text}</pre>")
        return

    async with aiofiles.open("logs/app_logs.txt") as aio_file:
        text = await aio_file.read()

    if len(text) < 4096:
        await message.reply(f"<pre language=java>{text}</pre>")
    else:
        await message.reply_document(document="logs/app_logs.txt")
