from ub_core import BOT, Config, Message, bot


@bot.add_cmd(cmd="repo")
async def sauce(bot: BOT, message: Message) -> None:
    bot = f"<a href='{Config.UPSTREAM_REPO}'>{Config.BOT_NAME}</a>"
    core = f"<a href='{Config.UPDATE_REPO}'>UB-Core</a>"
    await bot.send_message(
        chat_id=message.chat.id,
        text=f"{bot} | {core}",
        reply_to_message_id=message.reply_id or message.id,
        disable_web_page_preview=True,
    )
