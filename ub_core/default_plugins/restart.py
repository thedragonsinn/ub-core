import os
import shutil

from pyrogram.enums import ChatType

from ub_core import BOT, Message, bot


async def init_task() -> None:
    restart_msg = int(os.environ.get("RESTART_MSG", 0))
    restart_chat = int(os.environ.get("RESTART_CHAT", 0))
    try:
        if restart_msg and restart_chat:
            await bot.get_chat(restart_chat)
            await bot.edit_message_text(
                chat_id=restart_chat, message_id=restart_msg, text="Started"
            )
            os.environ.pop("RESTART_MSG")
            os.environ.pop("RESTART_CHAT")
    except Exception as e:
        bot.log.error(e)


@bot.add_cmd(cmd="restart")
async def restart(bot: BOT, message: Message, u_resp: Message | None = None) -> None:
    """
    CMD: RESTART
    INFO: Restart the Bot.
    FLAGS:
        -h: for hard restart.
        -cl: for clearing logs.
        -cp: for clearing temp plugins.
    Usage:
        .restart | .restart -h
    """
    reply: Message = u_resp or await message.reply("restarting....")

    if reply.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        os.environ["RESTART_MSG"] = str(reply.id)
        os.environ["RESTART_CHAT"] = str(reply.chat.id)

    if "-cl" in message.flags:
        os.remove("logs/app_logs.txt")

    if "-cp" in message.flags:
        shutil.rmtree("app/temp", ignore_errors=True)

    await bot.restart(hard="-h" in message.flags)
