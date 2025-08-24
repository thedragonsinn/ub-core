from ub_core import BOT, Config, Message


@BOT.add_cmd(cmd="repo")
async def sauce(bot: BOT, message: Message) -> None:
    """
    CMD: REPO
    INFO: Show repository urls.
    """

    bot_repo = f"<a href='{Config.UPSTREAM_REPO}'>HERE</a>"
    core_repo = f"<a href='{Config.UPDATE_REPO}'>HERE</a>"
    await message.reply(
        text=f"{Config.BOT_NAME}: {bot_repo}\nUb-Core: {core_repo}",
        disable_preview=True,
    )
