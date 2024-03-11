import asyncio

from ub_core import BOT, Config, Message, __version__, bot
from ub_core.default_plugins.restart import restart
from ub_core.utils import aio, run_shell_cmd

REPO = Config.REPO


async def get_commits() -> str | None:
    try:
        async with asyncio.timeout(10):
            await asyncio.to_thread(REPO.git.fetch)
    except TimeoutError:
        return
    commits: str = ""
    limit: int = 0
    for commit in REPO.iter_commits("HEAD..origin/main"):
        commits += (
            f"<b>#{commit.count()}</b> "
            f"<a href='{Config.UPSTREAM_REPO}/commit/{commit}'>{commit.message}</a> "
            f"By <i>{commit.author}</i>"
        )
        limit += 1
        if limit >= 15:
            break
    return commits


async def pull_commits() -> None | bool:
    REPO.git.reset("--hard")
    try:
        async with asyncio.timeout(10):
            await asyncio.to_thread(
                REPO.git.pull, Config.UPSTREAM_REPO, "--rebase=true"
            )
            return True
    except TimeoutError:
        return


async def update_core():
    tag_info = await aio.get_json(
        "https://api.github.com/repos/thedragonsinn/ub-core/tags"
    )
    latest_version = tag_info[0]["name"]
    if latest_version == "v" + __version__:
        return
    await run_shell_cmd(f"pip install -q --no-cache-dir git+{Config.UPDATE_REPO}")
    return latest_version


@bot.add_cmd(cmd="update")
async def updater(bot: BOT, message: Message) -> None | Message:
    """
    CMD: UPDATE
    INFO: Pull / Check for updates.
    FLAGS:
        -pull to pull updates
        -c to update core
    USAGE:
        .update | .update -pull
    """
    reply: Message = await message.reply("Checking for Updates....")

    if "-c" in message.flags:
        updated_version = await update_core()

        if updated_version:
            await reply.edit(
                f"Core Updated to version: {updated_version}\nRestarting..."
            )
            await restart(bot, message, resp)
            return
        else:
            await reply.edit(f"Core Already on latest version: {__version__}")
            return

    commits: str = await get_commits()

    if commits is None:
        await reply.edit("Timeout... Try again.")
        return

    if not commits:
        await reply.edit(text="Already Up To Date.", del_in=5)
        return

    if "-pull" not in message.flags:
        await reply.edit(
            text=f"<b>Update Available:</b>\n{commits}", disable_web_page_preview=True
        )
        return

    if not (await pull_commits()):  # NOQA
        await reply.edit("Timeout...Try again.")
        return

    await asyncio.gather(
        bot.log_text(
            text=f"#Updater\nPulled:\n{commits}", disable_web_page_preview=True
        ),
        reply.edit("<b>Update Found</b>\n<code>Pulling....</code>"),
        run_shell_cmd(f"pip install -q --no-cache-dir git+{Config.UPDATE_REPO}"),
    )

    await restart(bot, message, reply)
