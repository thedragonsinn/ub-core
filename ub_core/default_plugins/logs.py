import aiofiles

from ub_core import BOT, Message


@BOT.add_cmd(cmd="logs")
async def read_logs(bot: BOT, message: Message):
    async with aiofiles.open("logs/app_logs.txt", "r") as aio_file:
        text = await aio_file.read()
    if len(text) < 4050:
        await message.reply(f"<pre language=java>{text}</pre>")
    else:
        await message.reply_document(document="logs/app_logs.txt")
