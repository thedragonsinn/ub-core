import asyncio

from pyrogram import filters
from pyrogram.enums import ParseMode

from ub_core import BOT, Config, Message
from ub_core.utils import shell


async def run_cmd(bot: BOT, message: Message) -> None:
    cmd: str = message.input.strip()
    reply: Message = await message.reply("executing...")

    try:
        proc_stdout: str = await asyncio.create_task(
            shell.run_shell_cmd(cmd), name=reply.task_id
        )
    except asyncio.exceptions.CancelledError:
        await reply.edit("`Cancelled...`")
        return

    output: str = f"<pre language=shell>~$ {cmd}\n\n{proc_stdout}</pre>"
    await reply.edit(
        text=output,
        name="sh.txt",
        disable_preview=True,
        parse_mode=ParseMode.HTML,
    )


# Shell with Live Output
async def live_shell(bot: BOT, message: Message):
    cmd: str = message.input.strip()
    reply: Message = await message.reply("`getting live output....`")
    sub_process: shell.AsyncShell = await shell.AsyncShell.run_cmd(cmd)
    try:
        await asyncio.create_task(
            sub_process.send_output(message=reply), name=reply.task_id
        )
        await reply.edit(
            text=f"<pre language=shell>~$ {cmd}\n\n{sub_process.stdout}</pre>",
            name="shell.txt",
            disable_preview=True,
            parse_mode=ParseMode.HTML,
        )
    except asyncio.exceptions.CancelledError:
        sub_process.cancel()
        await reply.edit(f"`Cancelled....`")
    except BaseException:
        sub_process.cancel()
        raise


# Interactive Shell with Live Output
async def interactive_shell(bot: BOT, message: Message):
    """
    CMD: Interactive Shell
    INFO: Spawns an interactive shell that you can continuously pass multiple commands into.
    USAGE:
        .ish
        then keep replying to the bot's messages with shell commands.
    """
    sub_process: shell.InteractiveShell = await shell.InteractiveShell.spawn_shell()
    reply_to_id = message.id
    try:
        async with bot.Convo(
            client=bot,
            chat_id=message.chat.id,
            filters=generate_filter(message),
            timeout=180,
        ) as convo:
            while 1:

                input_prompt, input_cmd = await convo.send_message(
                    text="__Reply to this message to pass in the command.__",
                    reply_to_id=reply_to_id,
                    get_response=True,
                )
                input_text = input_cmd.text

                if input_text in ("q", "exit", "cancel", "c"):
                    sub_process.cancel()
                    await input_prompt.edit("`Cancelled....`")
                    return

                await sub_process.write_input(input_text)
                stdout_message = await input_cmd.reply(
                    f"__Executing__: ```shell\n{input_text}```"
                )
                await asyncio.create_task(
                    sub_process.send_output(stdout_message),
                    name=f"{stdout_message.chat.id}-{stdout_message.id}",
                )

                await stdout_message.edit(
                    text=f"<pre language=shell>~$ {input_text}\n\n{sub_process.stdout}</pre>",
                    name="shell.txt",
                    disable_preview=True,
                    parse_mode=ParseMode.HTML,
                )
                sub_process.flush_stdout()
                reply_to_id = input_cmd.id

    except asyncio.exceptions.CancelledError:
        sub_process.cancel()
        await message.reply("`Cancelled....`")
    except TimeoutError:
        sub_process.cancel()
        await message.reply("`Timeout.....`")
    except BaseException:
        sub_process.cancel()
        raise


def generate_filter(message: Message):
    async def _filter(_, __, msg: Message):
        if (
            not msg.text
            or not msg.from_user
            or msg.from_user.id != message.from_user.id
            or not msg.reply_to_message
            or not msg.reply_to_message.from_user
            or msg.reply_to_message.from_user.id != message._client.me.id
        ):
            return False
        return True

    return filters.create(_filter)


if Config.DEV_MODE:
    BOT.add_cmd(cmd="shell", allow_sudo=False)(live_shell)
    BOT.add_cmd(cmd="sh", allow_sudo=False)(run_cmd)
    BOT.add_cmd(cmd="ish", allow_sudo=False)(interactive_shell)
