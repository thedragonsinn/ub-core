from pathlib import Path

from ub_core import Config, Message, bot, utils

LOG_FILE = Path("logs/usage_record.txt").resolve()

LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
LOG_FILE.unlink(missing_ok=True)


def record_usage(update: Message):
    # Compare Log Level against User access
    match Config.COMMAND_LOG_LEVEL:
        case 0:
            return
        case 1:
            if not update.is_from_owner:
                return
        case 2:
            if update.from_user.id not in Config.SUDO_USERS:
                return
        case 3:
            if update.from_user.id not in Config.SUPERUSERS:
                return
        case _:
            pass

    with LOG_FILE.open("a+") as f:
        f.write(
            f"user: {utils.get_name(update.from_user)}"
            f"\ncmd: {update.cmd}"
            f"\ninput: {update.input}"
            f"\nlink: {getattr(update, 'link', '')}\n"
            f"{'-' * 25}\n"
        )


@bot.register_worker(interval=3600, name="usage-record")
async def upload_usage_record():
    if Config.COMMAND_LOG_LEVEL == 0:
        return

    if not LOG_FILE.is_file() or LOG_FILE.stat().st_size == 0:
        return

    await bot.send_document(
        chat_id=Config.LOG_CHAT, message_thread_id=Config.LOG_CHAT_THREAD_ID, document=str(LOG_FILE)
    )

    LOG_FILE.write_text("")
