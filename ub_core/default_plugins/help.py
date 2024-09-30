from collections import defaultdict

from ub_core import BOT, Config, Message, bot


@bot.add_cmd(cmd="help")
async def cmd_list(bot: BOT, message: Message) -> None:
    """
    CMD: HELP
    INFO: Check info/about available cmds.
    USAGE:
        .help help | .help
    """
    cmd = message.input.strip()

    if not cmd:
        await message.reply(text=get_cmds(), del_in=30)
        return

    if cmd not in Config.CMD_DICT.keys():
        await message.reply(
            text=f"Invalid <b>{cmd}</b>, check {message.trigger}help", del_in=5
        )
        return

    doc_string = Config.CMD_DICT[cmd].doc
    help_str = "\n".join([x.replace("    ", "", 1) for x in doc_string.splitlines()])
    await message.reply(text=f"<pre language=java>{help_str}</pre>", del_in=30)


def get_cmds() -> str:
    cmd_n_dir_map: dict[str, list[str]] = defaultdict(list)

    for cmd in Config.CMD_DICT.values():
        cmd_n_dir_map[cmd.dir_name].append(cmd.cmd)

    sorted_keys = sorted(cmd_n_dir_map.keys())

    help_str = ""

    for key in sorted_keys:
        help_str += f"\n\n\n<b>{key.capitalize()}:</b>\n"
        help_str += f"<pre language=json>{cmd_n_dir_map[key]}</pre>"

    return help_str
