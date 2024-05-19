import asyncio

from ub_core import BOT, Message, bot


@bot.add_cmd(cmd="c")
async def cancel_task(bot: BOT, message: Message) -> Message | None:
    """
    CMD: CANCEL
    INFO: Cancel a running command by replying to a message.
    USAGE: .c | .c -i <inline query id>
    """
    if "-i" in message.flags:
        task_id: str = message.text_list[-1]
    else:
        task_id: str | None = message.replied_task_id

        if not task_id:
            await message.reply(
                text="Reply To a Command or Bot's Response Message.", del_in=8
            )
            return

    all_tasks: set[asyncio.all_tasks] = asyncio.all_tasks()
    tasks: list[asyncio.Task] | None = [x for x in all_tasks if x.get_name() == task_id]

    if not tasks:
        await message.reply(text="Task not in Currently Running Tasks.", del_in=8)
        return

    response: str = ""
    for task in tasks:
        status: bool = task.cancel()
        response += (
            f"Task: <code>{task.get_name()}</code>" f"\nCancelled: <code>{status}</code>\n"
        )

    await message.reply(response, del_in=5)
