from ub_core import BOT, Config, Message, bot


@bot.add_cmd(cmd="repo")
async def sauce(bot: BOT, message: Message) -> None:
    bot_repo = f"<a href='{Config.UPSTREAM_REPO}'>here</a>"
    core_repo = f"<a href='{Config.UPDATE_REPO}'>here</a>"
    await bot.send_message(
        chat_id=message.chat.id,
        text=f"{Config.BOT_NAME}: {bot_repo}\nUb-Core: {core_repo}",
        reply_to_message_id=message.reply_id or message.id,
        disable_web_page_preview=True,
    )
