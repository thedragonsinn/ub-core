import asyncio

from ub_core import BOT, Config, CustomDB, Message, bot

DB = CustomDB["COMMON_SETTINGS"]

RECENT_CHANGE = False

LOCK = asyncio.Lock()


async def check_change(message: Message):
    global RECENT_CHANGE
    if RECENT_CHANGE:
        message.stop_propagation()
    RECENT_CHANGE = True


@bot.add_cmd(cmd="mode", allow_sudo=False)
async def mode_change(bot: BOT, message: Message):
    """
    CMD: MODE
    INFO: Changes mode to bot or dual
    """
    async with LOCK:
        await check_change(message)

    input = message.input.lower()

    if input not in {"dual", "bot"}:
        await message.reply("Invalid Mode\nAvailable Modes: `dual` | `bot`")
        await change_check()
        return
    elif input == Config.MODE:
        await message.reply(f"Already on `{input}` mode.")
        await change_check()
        return

    Config.MODE = input
    await message.reply(f"Mode Changed to `{input}`")
    await DB.add_data({"_id": "client_mode", "value": input})
    await change_check()


async def change_check():
    await asyncio.sleep(1)
    global RECENT_CHANGE
    RECENT_CHANGE = False
