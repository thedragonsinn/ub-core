import asyncio
import os

from ub_core import Config, Message, bot, utils


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

    with open("usage_record.txt", "a+") as f:
        f.write(
            f"user: {utils.get_name(update.from_user)}"
            f"\ncmd: {update.cmd}"
            f"\ninput: {update.input}"
            f"\nlink: {getattr(update, 'link', '')}\n"
            f"{'-' * 25}\n"
        )


@bot.register_task(task_type="bg", name="usage-record", ignore_if_exists=True)
async def upload_usage_record():
    if Config.COMMAND_LOG_LEVEL == 0:
        return

    log_file = "usage_record.txt"

    while True:
        await asyncio.sleep(3600)
        if not os.path.isfile(log_file):
            continue
        await bot.send_document(
            chat_id=Config.LOG_CHAT, message_thread_id=Config.LOG_CHAT_THREAD_ID, document=log_file
        )
        os.remove(log_file)
