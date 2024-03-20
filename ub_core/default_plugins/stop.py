from ub_core import BOT, Message, bot


@bot.add_cmd(cmd="stop_clients")
async def stop_client(bot: BOT, message: Message) -> None:
    """Stop Clients Before updating vars on koyeb to prevent string getting expired"""
    await message.reply("`Stopping Client(s)...`")
    await bot.stop_clients()
