from ub_core import BOT, Config, Message, ub_core_dir


@BOT.add_cmd(cmd="ci")
async def cmd_info(bot: BOT, message: Message):
    """
    CMD: CI (CMD INFO)
    INFO: Get GitHub File URL of a Command.
    USAGE: .ci ci
    """
    cmd = message.filtered_input.strip()
    if cmd not in Config.CMD_DICT:
        await message.reply("Give a valid cmd.", del_in=5)
        return

    command = Config.CMD_DICT[cmd]

    if command.is_from_core:
        relative_root = ub_core_dir.parent
        repo = Config.UPDATE_REPO
        branch = "main"
    else:
        relative_root = Config.WORKING_DIR.parent.resolve()
        repo = Config.REPO.remotes.origin.url
        branch = Config.REPO.active_branch

    relative_path = command.path.relative_to(relative_root)
    parts = relative_path.parts
    url_parts = [str(item).strip("/") for item in (repo, "blob", branch, *parts)]
    remote_url = "/".join(url_parts)

    resp_str = (
        "<blockquote>"
        f"<b>Command</b>: <code>{cmd}</code>"
        f"\n<b>Path</b>: <code>{relative_path}</code>"
        f"\n\n<b>Link</b>: <a href='{remote_url}'>Github</a>"
        "</blockquote>"
    )
    await message.reply(resp_str, disable_preview=True)


@BOT.add_cmd(cmd="s")
async def search(bot: BOT, message: Message):
    """
    CMD: Search
    INFO: Searches the given string in cmds.
    """
    search_str = message.input

    if not search_str:
        await message.reply("Give some input to search in commands.")
        return

    cmds = [cmd for cmd in Config.CMD_DICT.keys() if search_str in cmd]
    await message.reply(f"<pre language=json>{cmds}</pre>")
