import asyncio

from pyrogram.enums import ParseMode

from ub_core import BOT, Config, Message
from ub_core.utils import shell


async def run_cmd(bot: BOT, message: Message) -> None:
    cmd: str = message.input.strip()
    reply: Message = await message.reply("executing...")

    try:
        proc_stdout: str = await asyncio.create_task(shell.run_shell_cmd(cmd), name=reply.task_id)
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
        await asyncio.create_task(sub_process.send_output(message=reply), name=reply.task_id)
        await reply.edit(
            text=f"<pre language=shell>~$ {cmd}\n\n{sub_process.stdout}</pre>",
            name="shell.txt",
            disable_preview=True,
            parse_mode=ParseMode.HTML,
        )
    except asyncio.exceptions.CancelledError:
        sub_process.cancel()
        await reply.edit("`Cancelled....`")
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
    try:
        async with bot.Convo(
            client=bot,
            chat_id=message.chat.id,
            timeout=180,
            from_user=message.from_user.id,
            reply_to_user_id=bot.me.id,
            reply_to_message_id=None,
        ) as convo:
            reply_to_id = message.id
            while 1:
                input_cmd = await convo.send_message(
                    text="__Reply to this message to pass in the command.__",
                    reply_to_id=reply_to_id,
                )
                reply_to_id = input_cmd.id
                convo.reply_to_message_id = reply_to_id
                input_prompt = await convo.get_response()

                input_text = input_cmd.text

                if input_text in ("q", "exit", "cancel", "c"):
                    sub_process.cancel()
                    await input_prompt.edit("`Cancelled....`")
                    return

                await sub_process.write_input(input_text)

                stdout_message = await input_cmd.reply(
                    text=f"__Executing__: ```shell\n{input_text}```",
                    parse_mode=ParseMode.MARKDOWN,
                )

                await asyncio.create_task(
                    sub_process.send_output(stdout_message), name=stdout_message.task_id
                )

                await stdout_message.edit(
                    text=f"<pre language=shell>~$ {input_text}\n\n{sub_process.stdout}</pre>",
                    name="shell.txt",
                    disable_preview=True,
                    parse_mode=ParseMode.HTML,
                )
                sub_process.flush_stdout()

    except asyncio.exceptions.CancelledError:
        sub_process.cancel()
        await message.reply("`Cancelled....`")
    except TimeoutError:
        sub_process.cancel()
        await message.reply("`Timeout.....`")
    except BaseException:
        sub_process.cancel()
        raise


if Config.DEV_MODE:
    BOT.add_cmd(cmd="shell", allow_sudo=False)(live_shell)
    BOT.add_cmd(cmd="sh", allow_sudo=False)(run_cmd)
    BOT.add_cmd(cmd="ish", allow_sudo=False)(interactive_shell)
