import os

from ub_core import BOT, Config, Message


@BOT.add_cmd(cmd="ci")
async def cmd_info(bot: BOT, message: Message):
    """
    CMD: CI (CMD INFO)
    INFO: Get Github File URL of a Command.
    USAGE: .ci ci
    """
    cmd = message.filtered_input
    cmd_obj = Config.CMD_DICT.get(cmd)

    if cmd_obj is None:
        await message.reply("Give a valid cmd.", del_in=5)
        return

    if cmd_obj.is_from_core:
        plugin_path = cmd_obj.cmd_path.split("site-packages/")[1]
        repo = Config.UPDATE_REPO
        branch = "dual_mode"
    else:
        plugin_path = os.path.relpath(cmd_obj.cmd_path, os.curdir)
        repo = Config.REPO.remotes.origin.url
        branch = Config.REPO.active_branch

    to_join = [str(item).strip("/") for item in (repo, "blob", branch, plugin_path)]

    remote_url = os.path.join(*to_join)

    resp_str = (
        "<blockquote>"
        f"<b>Command</b>: <code>{cmd}</code>"
        f"\n<b>Path</b>: <code>{plugin_path}</code>"
        f"\n\n<b>Link</b>: <a href='{remote_url}'>Github</a>"
        "</blockquote>"
    )
    await message.reply(resp_str, disable_preview=True)


@BOT.add_cmd(cmd="s")
async def search(bot: BOT, message: Message):
    search_str = message.input

    if not search_str:
        await message.reply("Give some input to search in commands.")
        return

    cmds = [cmd for cmd in Config.CMD_DICT.keys() if search_str in cmd]
    await message.reply(f"<pre language=json>{cmds}</pre>")
